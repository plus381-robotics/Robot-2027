/*
 * timer.c
 *
 *  Created on: Oct 14, 2026
 *      Author: Lea
 */
#include "main.h"

uint32_t time_ms;
uint8_t match_started = 0;
uint32_t match_time = 0;

float chinch_time = 0.2;
const float dt = 0.001;

void timer10_isr() {
	time_ms++;
	chinch_read();
	chinch_debounce_counter(chinch_time, dt);
	if (match_started == 1) {
		match_time++;
	}
	encoder_update(dt);
	update_odometrija(dt);

	if (match_time >= 100000) {
		motori_set(0, 0);
	}

	/*else {
		if (time_ms % 10 == 0) {
			position_control_loop(dt);
		}
		velocity_control_loop(dt);
	}*/
}

void time_start() {
	HAL_TIM_Base_Start_IT(&htim10);
}

uint32_t get_time_ms() {
	return time_ms;
}

uint8_t timer_delay(uint32_t *start_time, uint32_t delay) {
	if (*start_time > time_ms) {
		*start_time = time_ms;
	}
	if (*start_time + delay <= time_ms) {
		*start_time = 0xFFFFFFFF;
		return 1;
	}
	return 0;
}

