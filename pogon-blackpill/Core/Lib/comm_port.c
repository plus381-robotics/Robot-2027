/*
 * comm_port.c
 *
 * BlackPill deo protokola sa ESP-om: comm.c (zajednički sa nucleo/) zove ove funkcije.
 * Vidi comm_port.h i comm.h.
 *
 * Cilj za regulaciju (goal) živi ovde. Glavna petlja zove comm_port_update(), pa
 * move_goal(comm_port_goal()). Hook-ovi mogu da se pozovu i iz prekida (comm_hook_stop
 * pri padu heartbeat-a), zato samo postavljaju zahtev, a goal menja comm_port_update().
 */
#include "main.h"
#include "comm.h"
#include "comm_port.h"

static goal_type goal;                 /* type 0 = stoj */
static volatile uint8_t stop_request;
static volatile uint8_t match_running;
static uint32_t match_start_ms;

/* ---------------- comm_port.h ---------------- */

uint32_t comm_port_time_ms(void) {
	return HAL_GetTick();
}

static int16_t clamp16(double v) {
	if (v > 32767.0) return 32767;
	if (v < -32768.0) return -32768;
	return (int16_t) v;
}

void comm_port_fill_status(msg_status_t *s) {
	double phi = get_phi();            /* 0..2pi, a protokol traži -180..180° */
	if (phi > M_PI)
		phi -= 2.0 * M_PI;
	s->x = clamp16(get_x() * 1000.0);
	s->y = clamp16(get_y() * 1000.0);
	s->theta = clamp16(phi * 18000.0 / M_PI);
	s->v = clamp16(get_v() * 1000.0);
	if (match_running) {
		s->state |= STATE_MATCH_RUNNING;
		s->match_ms = HAL_GetTick() - match_start_ms;
	}
}

uint8_t comm_port_set_pose(int16_t x_mm, int16_t y_mm, int16_t theta_cdeg) {
	set_pose(x_mm / 1000.0, y_mm / 1000.0, theta_cdeg * M_PI / 18000.0);
	return 0;
}

void comm_port_match_start(void) {
	if (!match_running) {
		match_start_ms = HAL_GetTick();
		match_running = 1;
	}
}

/* ---------------- hook-ovi iz comm.h ---------------- */

void comm_hook_stop(void) {
	stop_request = 1;
}

/* ---------------- glavna petlja ---------------- */

goal_type* comm_port_goal(void) {
	return &goal;
}

void comm_port_update(void) {
	if (stop_request) {
		stop_request = 0;
		reset_goal(&goal);
	}
}
