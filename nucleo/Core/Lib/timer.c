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
uint32_t chinch_time_pom = 0;
uint8_t match_started = 0;
uint32_t chinch_cnt_pom;
uint8_t flag_chinch_timer = 0;


void timer10_isr() {
	time_ms++;
	time_s = time_ms / 1000.0;


	if (match_started == 1) {
		match_time += 0.001;
	}
}
uint32_t get_chinch_time() {
	return chinch_time_pom;
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


