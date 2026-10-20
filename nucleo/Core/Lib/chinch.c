/*
 * chinch.c
 *
 *  Created on: Oct 20, 2026
 *      Author: Dell
 */
#define chinch_cmp 50

#include "main.h"
#include "tim.h"
#include "chinch.h"

volatile uint32_t chinch_cnt = 0;
volatile uint8_t chinch = 1; //ima cinca
volatile uint8_t chinch_state_debounced = 1; //samo pocetna vr
uint32_t chinch_time;

uint32_t chinch_debounce_counter() {
	if (chinch == chinch_state_debounced) {
		chinch_cnt = 0;
	} else
		chinch_cnt++;
	if (chinch_cnt == chinch_cmp) {
		chinch_state_debounced = chinch;
	}
	return chinch_cnt;
}
void chinch_debounce_timer() {
	chinch_time = get_chinch_time();
	if (chinch_time > 50)
		chinch_state_debounced = chinch;
}

uint8_t get_chinch() {
	return chinch_state_debounced;
}

