/*
 * comm.c
 *
 * Protokol sa ESP-om na USART1. Vidi comm.h za opis i povezivanje.
 * Isti fajl je u nucleo/ i pogon-blackpill/: sve što zavisi od robota ide kroz
 * comm_port.h (svaki projekat ima svoj comm_port.c), ovde se ne dodaje ništa robot-specifično.
 *
 * Prijem i slanje idu preko prekida u kružne bafere, pa glavna petlja nikad ne čeka na UART.
 * Ako glavna petlja nakratko blokira (HAL_Delay), bajtovi se čuvaju u baferu (512 B)
 * i obrade se u sledećem comm_poll().
 *
 * NAPOMENA: USART1_IRQHandler je definisan ovde. Ako se u CubeMX-u uključi
 * "USART1 global interrupt", CubeMX će napraviti još jedan u stm32f4xx_it.c
 * i build javlja dupliranu funkciju: tada ga obrisati ovde ili tamo.
 */
#include <string.h>
#include "stm32f4xx_hal.h"
#include "comm.h"
#include "comm_port.h"
#include "link.h"
#include "protocol.h"

#define RX_SIZE 512             /* stepen dvojke */
#define TX_SIZE 512

static volatile uint8_t rx_buf[RX_SIZE];
static volatile uint16_t rx_head, rx_tail;
static volatile uint8_t tx_buf[TX_SIZE];
static volatile uint16_t tx_head, tx_tail;

static link_parser_t parser;
static volatile uint32_t last_rx_ms;
static volatile uint8_t esp_seen;    /* ESP se javio bar jednom ispravnom porukom */
static volatile uint8_t link_lost;   /* ESP je bio tu, pa utihnuo */

static uint8_t last_seq;             /* za prepoznavanje ponovljenih komandi */
static uint8_t last_reply_type, last_reply_reason;
static uint8_t motion_seq;           /* aktivna komanda kretanja, 0 = nema */
static uint8_t debug_mask;
static uint32_t last_status_ms;

/* ---------------- UART: prekid i kružni baferi ---------------- */

void USART1_IRQHandler(void) {
	uint32_t sr = USART1->SR;
	if (sr & (USART_SR_RXNE | USART_SR_ORE | USART_SR_FE | USART_SR_NE)) {
		uint8_t b = (uint8_t) USART1->DR;   /* čitanje DR briše i oznake grešaka */
		if (sr & USART_SR_RXNE) {
			uint16_t next = (rx_head + 1) & (RX_SIZE - 1);
			if (next != rx_tail) {
				rx_buf[rx_head] = b;
				rx_head = next;
			}
		}
	}
	if ((USART1->CR1 & USART_CR1_TXEIE) && (sr & USART_SR_TXE)) {
		if (tx_tail != tx_head) {
			USART1->DR = tx_buf[tx_tail];
			tx_tail = (tx_tail + 1) & (TX_SIZE - 1);
		} else {
			USART1->CR1 &= ~USART_CR1_TXEIE;
		}
	}
}

static void tx_write(const uint8_t *data, size_t n) {
	uint16_t free_space = (tx_tail - tx_head - 1) & (TX_SIZE - 1);
	if (n > free_space)
		return;                              /* bafer pun: okvir se odbacuje ceo */
	for (size_t i = 0; i < n; i++) {
		tx_buf[tx_head] = data[i];
		tx_head = (tx_head + 1) & (TX_SIZE - 1);
	}
	USART1->CR1 |= USART_CR1_TXEIE;
}

static void send(uint8_t type, uint8_t seq, const void *payload, size_t len) {
	uint8_t frame[LINK_MAX_FRAME];
	size_t n = link_build_frame(type, seq, payload, len, frame);
	if (n)
		tx_write(frame, n);
}

/* ---------------- odgovori ---------------- */

static void reply(uint8_t seq, uint8_t reason) {
	last_reply_type = reason ? MSG_FAIL : MSG_ACK;
	last_reply_reason = reason;
	if (reason) {
		msg_fail_t f = { reason };
		send(MSG_FAIL, seq, &f, sizeof f);
	} else {
		send(MSG_ACK, seq, 0, 0);
	}
}

void comm_motion_finished(uint8_t reason) {
	if (!motion_seq)
		return;
	if (reason) {
		msg_fail_t f = { reason };
		send(MSG_FAIL, motion_seq, &f, sizeof f);
	} else {
		send(MSG_DONE, motion_seq, 0, 0);
	}
	motion_seq = 0;
}

void comm_actuator_finished(uint8_t seq, uint8_t reason) {
	if (reason) {
		msg_fail_t f = { reason };
		send(MSG_FAIL, seq, &f, sizeof f);
	} else {
		send(MSG_DONE, seq, 0, 0);
	}
}

void comm_log(const char *text) {
	if (esp_seen)
		send(MSG_LOG, 0, text, strnlen(text, LINK_MAX_PAYLOAD));
}

/* ---------------- podrazumevani hook-ovi (zameniti svojim u comm_port.c) ----------------
 * comm_hook_stop namerno nema podrazumevanu verziju: ako ga projekat ne definiše,
 * build javlja grešku umesto da robot tiho ne staje kad veza pukne. */

__weak uint8_t comm_hook_goto(int16_t x_mm, int16_t y_mm, int16_t theta_cdeg, uint8_t flags, uint16_t max_speed) {
	return REASON_INVALID;   /* projekat još nema svoju verziju */
}
__weak uint8_t comm_hook_rotate(int16_t theta_cdeg) {
	return REASON_INVALID;
}
__weak uint8_t comm_hook_move(int16_t dist_mm, uint16_t max_speed) {
	return REASON_INVALID;
}
__weak uint8_t comm_hook_actuator(uint8_t seq, uint8_t id, int16_t value) {
	return REASON_INVALID;
}
__weak uint8_t comm_hook_bootloader(void) {
	return REASON_INVALID;
}

/* ---------------- obrada komandi ---------------- */

#define PAYLOAD_IS(T) (f->len == sizeof(T))

static void start_motion(uint8_t seq, uint8_t reason) {
	if (!reason) {
		if (motion_seq)                       /* nova komanda prekida staru */
			comm_motion_finished(REASON_PREEMPTED);
		motion_seq = seq;
	}
	reply(seq, reason);
}

static void handle(const link_frame_t *f) {
	last_rx_ms = comm_port_time_ms();         /* heartbeat: samo okviri koji su prošli CRC */
	if (link_lost)
		last_seq = 0;                         /* ESP se vratio (možda restartovan): seq kreće ispočetka */
	esp_seen = 1;
	link_lost = 0;

	if (f->type == MSG_PING) {
		msg_pong_t p = { PROTO_VERSION };
		send(MSG_PONG, f->seq, &p, sizeof p);
		return;
	}
	if (f->seq == 0)
		return;
	if (f->seq == last_seq) {                 /* ponovljena komanda: samo ponovi odgovor */
		if (last_reply_type == MSG_FAIL) {
			msg_fail_t r = { last_reply_reason };
			send(MSG_FAIL, f->seq, &r, sizeof r);
		} else {
			send(MSG_ACK, f->seq, 0, 0);
		}
		return;
	}
	last_seq = f->seq;

	switch (f->type) {
	case MSG_SET_POSE:
		if (!PAYLOAD_IS(msg_set_pose_t)) break;
		{
			msg_set_pose_t m;
			memcpy(&m, f->payload, sizeof m);
			reply(f->seq, comm_port_set_pose(m.x, m.y, m.theta));
		}
		return;
	case MSG_GOTO:
		if (!PAYLOAD_IS(msg_goto_t)) break;
		{
			msg_goto_t m;
			memcpy(&m, f->payload, sizeof m);
			start_motion(f->seq, comm_hook_goto(m.x, m.y, m.theta, m.flags, m.max_speed));
		}
		return;
	case MSG_ROTATE:
		if (!PAYLOAD_IS(msg_rotate_t)) break;
		{
			msg_rotate_t m;
			memcpy(&m, f->payload, sizeof m);
			start_motion(f->seq, comm_hook_rotate(m.theta));
		}
		return;
	case MSG_MOVE:
		if (!PAYLOAD_IS(msg_move_t)) break;
		{
			msg_move_t m;
			memcpy(&m, f->payload, sizeof m);
			start_motion(f->seq, comm_hook_move(m.dist, m.max_speed));
		}
		return;
	case MSG_STOP:
		comm_hook_stop();
		comm_motion_finished(REASON_STOPPED);
		reply(f->seq, 0);
		return;
	case MSG_ACTUATOR:
		if (!PAYLOAD_IS(msg_actuator_t)) break;
		{
			msg_actuator_t m;
			memcpy(&m, f->payload, sizeof m);
			reply(f->seq, comm_hook_actuator(f->seq, m.id, m.value));
		}
		return;
	case MSG_MATCH_START:
		comm_port_match_start();
		reply(f->seq, 0);
		return;
	case MSG_ENTER_BOOTLOADER:
		reply(f->seq, comm_hook_bootloader());
		return;
	case MSG_DEBUG_STREAMS:
		if (!PAYLOAD_IS(msg_debug_streams_t)) break;
		debug_mask = f->payload[0];
		reply(f->seq, 0);
		return;
	default:
		break;
	}
	reply(f->seq, REASON_INVALID);            /* nepoznata komanda ili pogrešna dužina */
}

/* ---------------- STATUS ---------------- */

static void send_status(void) {
	msg_status_t s = { 0 };
	comm_port_fill_status(&s);
	if (motion_seq)
		s.state |= STATE_MOVING;
	send(MSG_STATUS, 0, &s, sizeof s);
}

/* ---------------- javne funkcije ---------------- */

void comm_init(void) {
	/* USART1 je već podešen u CubeMX-u (MX_USART1_UART_Init); ovde se samo uključuju prekidi */
	/* Prioritet 1. USART prekid traje par us; ako 1 kHz prekid robota traje duže od jednog
	 * bajta (~87 us na 115200), projekat mora da ga spusti ispod 1, inače se gube bajtovi. */
	HAL_NVIC_SetPriority(USART1_IRQn, 1, 0);
	HAL_NVIC_EnableIRQ(USART1_IRQn);
	USART1->CR1 |= USART_CR1_RXNEIE;
}

void comm_poll(void) {
	link_frame_t f;
	while (rx_tail != rx_head) {
		uint8_t b = rx_buf[rx_tail];
		rx_tail = (rx_tail + 1) & (RX_SIZE - 1);
		if (link_parser_feed(&parser, b, &f))
			handle(&f);
	}
	uint32_t now = comm_port_time_ms();
	if (esp_seen && !link_lost && now - last_status_ms >= COMM_STATUS_PERIOD_MS) {
		last_status_ms = now;
		send_status();
	}
}

void comm_tick_1ms(void) {
	if (esp_seen && !link_lost && comm_port_time_ms() - last_rx_ms > COMM_HEARTBEAT_MS) {
		link_lost = 1;
		comm_hook_stop();
	}
}

uint8_t comm_esp_connected(void) {
	return esp_seen && !link_lost;
}

uint8_t comm_motion_allowed(void) {
	return !link_lost;   /* bez ESP-a (samostalni režim) uvek 1 */
}
