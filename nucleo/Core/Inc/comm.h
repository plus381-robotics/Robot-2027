/*
 * comm.h
 *
 * Komunikacija sa ESP-om preko USART1 (PA9 TX, PA10 RX).
 *
 * BEZ ESP-a Nucleo radi potpuno isto kao ranije:
 *  - dok se ESP ne javi nijednom ispravnom porukom, comm ne dira ništa (samostalni režim),
 *  - heartbeat se proverava tek kad se ESP javio.
 * Kad je ESP povezan, pa utihne duže od COMM_HEARTBEAT_MS, poziva se comm_hook_stop()
 * i comm_motion_allowed() vraća 0 dok se ESP ponovo ne javi.
 * Heartbeat osvežavaju samo ispravni okviri (prošli CRC), a obrađuju se u comm_poll().
 * Zato glavna petlja ne sme da blokira duže od COMM_HEARTBEAT_MS dok je ESP povezan,
 * inače Nucleo pogrešno zaključi da je veza pukla.
 *
 * Činč (protokol v4): comm_poll() pokreće meč (match_started, timer.c broji match_time) kad se izvuče
 * činč koji je posle pokretanja bio u robotu (chinch.c, debounce 200 ms). To radi i bez ESP-a. Ako je
 * činč izvučen već pri pokretanju (restart Nucleo-a u meču), meč ne kreće sam: ESP šalje RESUME
 * (poza + meč od elapsed_ms). Ostalo iz v4: RESET (softverski restart posle ACK), uptime_ms i w u
 * STATUS-u, razlog restarta u PONG-u, pad veze prekida kretanje sa REASON_LINK.
 *
 * Povezivanje u projekat:
 *  - main.c, USER CODE 2:  comm_init();          (posle MX_USART1_UART_Init)
 *  - main.c, petlja:       comm_poll();
 *  - stm32f4xx_it.c, TIM10 prekid (posle timer10_isr()):  comm_tick_1ms();
 */
#ifndef INC_COMM_H_
#define INC_COMM_H_

#include <stdint.h>

#define COMM_HEARTBEAT_MS      500   /* ESP šalje PING svakih ~150 ms */
#define COMM_STATUS_PERIOD_MS  50    /* STATUS ka ESP-u, 20 Hz */

void comm_init(void);
void comm_poll(void);        /* glavna petlja: obrađuje primljene poruke, šalje STATUS */
void comm_tick_1ms(void);    /* 1 kHz prekid: provera heartbeat-a */

uint8_t comm_esp_connected(void);   /* 1 = ESP se javio i veza je živa */
uint8_t comm_motion_allowed(void);  /* 0 = veza sa ESP-om je pukla, motori treba da stoje */
uint8_t comm_stop_reason(void);    /* za comm_hook_stop: REASON_LINK posle pada veze, inače STOPPED */

/* Kad se završi kretanje koje je pokrenuo ESP (GOTO/ROTATE/MOVE):
 * reason 0 = uspešno (DONE), inače REASON_* iz protocol.h (FAIL). */
void comm_motion_finished(uint8_t reason);
/* Isto za aktuator koji je pokrenut komandom ACTUATOR sa datim seq. */
void comm_actuator_finished(uint8_t seq, uint8_t reason);

/* Tekstualna poruka koja se na ESP-u ispiše (LOG). */
void comm_log(const char *text);

/*
 * HOOK-ovi: veza protokola sa vašim kodom.
 * Ovde su "weak" podrazumevane verzije; kad napišete svoju funkciju sa istim imenom
 * (npr. u regulacija.c), ona automatski zamenjuje podrazumevanu.
 *
 * Povratna vrednost: 0 = komanda prihvaćena (kasnije pozvati comm_motion_finished),
 *                    REASON_* = odbijena odmah.
 * Podrazumevano kretanje i aktuatori vraćaju REASON_INVALID ("još nije implementirano").
 */
uint8_t comm_hook_goto(int16_t x_mm, int16_t y_mm, int16_t theta_cdeg, uint8_t flags, uint16_t max_speed);
uint8_t comm_hook_rotate(int16_t theta_cdeg);
uint8_t comm_hook_move(int16_t dist_mm, uint16_t max_speed);
uint8_t comm_hook_actuator(uint8_t seq, uint8_t id, int16_t value);
void comm_hook_stop(void);   /* podrazumevano: pwm_set(0, 0) */

#endif /* INC_COMM_H_ */
