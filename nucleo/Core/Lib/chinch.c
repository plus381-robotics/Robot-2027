/*
 * chinch.c
 *
 *  Created on: Oct 20, 2026
 *      Author: Dell
 */
#include "main.h"
#include "tim.h"
#include "chinch.h"

volatile uint32_t chinch_cnt = 0;
volatile uint8_t chinch_state_debounced = 1; //samo pocetna vr
uint32_t chinch_cmp;
float dt = 0.001;
volatile uint8_t chinch;


uint32_t chinch_debounce_counter(float chinch_time) {
	chinch = HAL_GPIO_ReadPin(GPIOA, GPIO_PIN_5);
	chinch_cmp = chinch_time / dt;
	if (chinch == chinch_state_debounced) {
		chinch_cnt = 0;
	} else
		chinch_cnt++;
	if (chinch_cnt == chinch_cmp) {
		chinch_state_debounced = chinch;
	}
	return chinch_cnt;
}

uint8_t get_chinch() {
	return chinch_state_debounced;
}

