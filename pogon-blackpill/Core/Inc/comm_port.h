/*
 * comm_port.h
 *
 * Veza između zajedničkog protokola (comm.c, isti u nucleo/ i pogon-blackpill/)
 * i konkretnog robota. Svaki projekat ima svoj comm_port.c koji definiše ove funkcije
 * i comm_hook_* iz comm.h (comm_hook_stop je obavezan).
 */
#ifndef INC_COMM_PORT_H_
#define INC_COMM_PORT_H_

#include <stdint.h>
#include "protocol.h"

/* Milisekunde od starta. Poziva se i iz 1 kHz prekida (comm_tick_1ms). */
uint32_t comm_port_time_ms(void);

/* Popuni x, y, theta, v, w (mrad/s), match_ms i bitove MATCH_* u state (jedinice iz protocol.yaml:
 * mm, cdeg -18000..18000, mm/s, ms). comm.c posle sam dodaje STATE_MOVING. */
void comm_port_fill_status(msg_status_t *s);

/* SET_POSE (mm, mm, cdeg). Vraća 0 ili REASON_* ako se odbija. */
uint8_t comm_port_set_pose(int16_t x_mm, int16_t y_mm, int16_t theta_cdeg);

/* MATCH_START: kreni da brojiš 100 s. */
void comm_port_match_start(void);

/* RESUME (v4): poza kao SET_POSE i meč koji traje već elapsed_ms (obnova posle restarta).
 * Vraća 0 ili REASON_*. */
uint8_t comm_port_resume(int16_t x_mm, int16_t y_mm, int16_t theta_cdeg, uint32_t elapsed_ms);

/* IR senzori -> regulacija (bitovi 1 napred, 2 nazad). Zove ga kod koji čita IR; u prilazu elementu
 * (GOTOFLAGS_NEAR, v5) se ne prosleđuje. */
void comm_port_set_obstacle(uint8_t bits);

#endif /* INC_COMM_PORT_H_ */
