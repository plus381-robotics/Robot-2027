/*
 * comm.c
 *
 * Protokol sa ESP-om na USART1. Vidi comm.h za opis i povezivanje.
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
#include "main.h"
#include "usart.h"
#include "comm.h"
#include "link.h"
#include "protocol.h"
#include "timer.h"
#include "odometrija.h"
#include "pwm.h"
#include "chinch.h"

#define NOW() get_time_ms()
#define CINC_READY_MS 500       /* posle pokretanja: debounce činča (200 ms) je sigurno završen */

extern uint8_t match_started;   /* timer.c */
extern float match_time;        /* timer.c, u sekundama */

static uint8_t cinc_in;         /* činč je viđen u robotu posle pokretanja (meč kreće tek na izvlačenje) */

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
static uint8_t last_motion_seq;      /* v3: seq poslednje ZAVRŠENE komande kretanja (0 = nijedna) */
static uint8_t last_motion_result;   /* v3: njen ishod, 0 = DONE, inače REASON_* */
static uint32_t last_status_ms;
static volatile uint8_t ir_raw;          /* v5: šta vidi svaki IR senzor (comm_ir_set) */
static volatile uint8_t ir_mask = 0xFF;  /* v5: koji smeju da zaustave robota (IR_MASK) */
static uint8_t reset_cause;          /* v4: razlog poslednjeg pokretanja (RESETCAUSE_*), za PONG */
static volatile uint8_t reset_request; /* v4: komanda RESET: restart posle RESET_DELAY_MS (da ACK ode) */
static uint32_t reset_t0;
#define RESET_DELAY_MS 30

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

/* v4: razlog pokretanja iz RCC->CSR (čita se pre nego što ga watchdog_init obriše; ako je već obrisan, 0). */
static uint8_t read_reset_cause(void) {
	uint32_t csr = RCC->CSR;
	uint8_t c = 0;
	if (csr & RCC_CSR_PINRSTF) c |= RESETCAUSE_PIN;
	if (csr & (RCC_CSR_PORRSTF | RCC_CSR_BORRSTF)) c |= RESETCAUSE_POWER;
	if (csr & RCC_CSR_SFTRSTF) c |= RESETCAUSE_SOFT;
	if (csr & RCC_CSR_IWDGRSTF) c |= RESETCAUSE_IWDG;
	if (csr & RCC_CSR_WWDGRSTF) c |= RESETCAUSE_WWDG;
	if (csr & RCC_CSR_LPWRRSTF) c |= RESETCAUSE_LOW_POWER;
	/* posle NRST-a je i PINRSTF; softverski restart postavlja i PINRSTF (NRST se interno spusti) */
	if (c & (RESETCAUSE_SOFT | RESETCAUSE_IWDG | RESETCAUSE_WWDG | RESETCAUSE_POWER))
		c &= ~RESETCAUSE_PIN;
	return c;
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
	last_motion_seq = motion_seq;         /* ide i u STATUS: ESP zna ishod i kad se DONE/FAIL izgubi */
	last_motion_result = reason;
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

/* ---------------- podrazumevani hook-ovi (zameniti svojim) ---------------- */

__weak uint8_t comm_hook_goto(int16_t x_mm, int16_t y_mm, int16_t theta_cdeg, uint8_t flags, uint16_t max_speed) {
	return REASON_INVALID;   /* pozicijska petlja još ne postoji */
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
__weak void comm_hook_stop(void) {
	pwm_set(0, 0);
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
	last_rx_ms = get_time_ms();               /* heartbeat: samo okviri koji su prošli CRC */
	if (link_lost)
		last_seq = 0;                         /* ESP se vratio (možda restartovan): seq kreće ispočetka */
	esp_seen = 1;
	link_lost = 0;

	if (f->type == MSG_PING) {
		msg_pong_t p = { PROTO_VERSION, reset_cause };
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
			set_pose(m.x / 1000.0f, m.y / 1000.0f, m.theta * (float) M_PI / 18000.0f);
			reply(f->seq, 0);
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
	case MSG_IR_MASK:                         /* v5: koji IR senzori smeju da zaustave robota */
		if (!PAYLOAD_IS(msg_ir_mask_t)) break;
		ir_mask = f->payload[0];
		reply(f->seq, 0);
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
		match_started = 1;
		reply(f->seq, 0);
		return;
	case MSG_RESUME:                          /* v4: obnova posle restarta: poza + meč od elapsed_ms */
		if (!PAYLOAD_IS(msg_resume_t)) break;
		{
			msg_resume_t m;
			memcpy(&m, f->payload, sizeof m);
			set_pose(m.x / 1000.0f, m.y / 1000.0f, m.theta * (float) M_PI / 18000.0f);
			match_time = m.elapsed_ms / 1000.0f;   /* timer.c nastavlja da broji od ovoga */
			match_started = 1;
			reply(f->seq, 0);
		}
		return;
	case MSG_RESET:                           /* v4: posle ACK softverski restart (comm_poll) */
		comm_hook_stop();
		reply(f->seq, 0);
		reset_request = 1;
		reset_t0 = NOW();
		return;
	default:
		break;
	}
	reply(f->seq, REASON_INVALID);            /* nepoznata komanda ili pogrešna dužina */
}

/* ---------------- IR senzori (v5) ----------------
 * Kod koji čita IR senzore (GPIO, 1 kHz) javlja šta svaki vidi preko comm_ir_set(bitovi IR_F1..IR_B4) i
 * zaustavlja robota kad comm_ir_obstacle() nije 0 (1 = napred, 2 = nazad). ESP bira koji senzori smeju da
 * zaustave robota (IR_MASK); ugašen senzor i dalje meri i ide u STATUS (ir_raw). Posle pokretanja: svi uključeni. */

void comm_ir_set(uint8_t raw) {
	ir_raw = raw;
}

uint8_t comm_ir_mask(void) {
	return ir_mask;
}

uint8_t comm_ir_obstacle(void) {
	uint8_t on = ir_raw & ir_mask;
	return ((on & (IR_F1 | IR_F2 | IR_F3 | IR_F4)) ? 1 : 0) | ((on & (IR_B1 | IR_B2 | IR_B3 | IR_B4)) ? 2 : 0);
}

/* ---------------- STATUS ---------------- */

static int16_t clamp16(float v) {
	if (v > 32767.0f) return 32767;
	if (v < -32768.0f) return -32768;
	return (int16_t) v;
}

static void send_status(void) {
	msg_status_t s;
	s.x = clamp16(get_x_pos_rob() * 1000.0f);
	s.y = clamp16(get_y_pos_rob() * 1000.0f);
	s.theta = clamp16(get_phi_pos_rob() * 18000.0f / (float) M_PI);
	s.v = clamp16(get_linear_velocity() * 1000.0f);
	s.state = (motion_seq ? STATE_MOVING : 0) | (match_started ? STATE_MATCH_RUNNING : 0);
	s.match_ms = (uint32_t) (match_time * 1000.0f);
	s.last_seq = last_motion_seq;
	s.last_result = last_motion_result;
	s.uptime_ms = get_time_ms();
	s.ir_raw = ir_raw;
	s.ir_mask = ir_mask;
	s.w = clamp16(get_angular_velocity() * 1000.0f);   /* rad/s -> mrad/s */
	send(MSG_STATUS, 0, &s, sizeof s);
}

/* ---------------- javne funkcije ---------------- */

void comm_init(void) {
	/* USART1 je već podešen u CubeMX-u (MX_USART1_UART_Init); ovde se samo uključuju prekidi */
	HAL_NVIC_SetPriority(USART1_IRQn, 1, 0);  /* niže od TIM10 (0), regulacija ima prednost */
	HAL_NVIC_EnableIRQ(USART1_IRQn);
	USART1->CR1 |= USART_CR1_RXNEIE;
	reset_cause = read_reset_cause();         /* pre watchdog_init(), koji briše oznake */
}

void comm_poll(void) {
	link_frame_t f;
	while (rx_tail != rx_head) {
		uint8_t b = rx_buf[rx_tail];
		rx_tail = (rx_tail + 1) & (RX_SIZE - 1);
		if (link_parser_feed(&parser, b, &f))
			handle(&f);
	}
	if (reset_request && NOW() - reset_t0 >= RESET_DELAY_MS)
		NVIC_SystemReset();
	if (link_lost && motion_seq)
		comm_motion_finished(REASON_LINK);    /* pad veze: kretanje je prekinuto (v4: LINK, ne STOPPED) */
	/* Činč: meč kreće kad se izvuče činč koji je posle pokretanja bio u robotu (debounce u chinch.c).
	 * Ako je činč izvučen već pri pokretanju (restart u meču), meč NE kreće sam: ESP šalje RESUME. */
	if (NOW() > CINC_READY_MS && !match_started) {
		if (get_chinch())
			cinc_in = 1;
		else if (cinc_in)
			match_started = 1;
	}
	if (esp_seen && !link_lost && get_time_ms() - last_status_ms >= COMM_STATUS_PERIOD_MS) {
		last_status_ms = get_time_ms();
		send_status();
	}
}

void comm_tick_1ms(void) {
	if (esp_seen && !link_lost && get_time_ms() - last_rx_ms > COMM_HEARTBEAT_MS) {
		link_lost = 1;
		comm_hook_stop();
	}
}

uint8_t comm_esp_connected(void) {
	return esp_seen && !link_lost;
}

uint8_t comm_stop_reason(void) {
	return link_lost ? REASON_LINK : REASON_STOPPED;
}

uint8_t comm_motion_allowed(void) {
	return !link_lost;   /* bez ESP-a (samostalni režim) uvek 1 */
}
