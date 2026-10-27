/*
 * timer.c
 *
 *  Created on: Oct 14, 2026
 *      Author: Dell
 */
#include "main.h"
#include "tim.h"
#include "chinch.h"

uint32_t time_ms;
float time_s;
float match_time;
uint8_t match_started = 0;
float chinch_time = 0.2;
const float dt = 0.001;

void timer10_isr() {
	time_ms++;
	time_s = time_ms / 1000.0;

	if (match_started == 1) {
		match_time += 0.001;
	}
	encoder_speed_left(dt);
	encoder_speed_right(dt);

	chinch_read();
	chinch_debounce_counter(chinch_time, dt);
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
		*start_time = 0xFFFF;
		return 1;
	}
	return 0;
}
int32_t get_left_encoder() {
	return encoder_speed_left(dt);
}
int32_t get_right_encoder() {
	return encoder_speed_right(dt);
}

