#include "main.h"
#include "tim.h"
#include "chinch.h"

volatile uint32_t chinch_cnt = 0;
volatile uint8_t chinch = 1; // ima cinca
volatile uint8_t chinch_state_debounced = 1; // samo pocetna vr
uint32_t chinch_cmp;

void chinch_debounce_counter(float chinch_time, float dt) {
	chinch_cmp = chinch_time / dt;

	if (chinch == chinch_state_debounced) {
		chinch_cnt = 0;
	} else {
		chinch_cnt++;
	}

	if (chinch_cnt >= chinch_cmp) {
		chinch_state_debounced = chinch;
		chinch_cnt = 0;
	}
}

uint8_t get_chinch() {
	return chinch_state_debounced;
}
void chinch_read() {
	chinch = HAL_GPIO_ReadPin(Chinch_GPIO_GPIO_Port, Chinch_GPIO_Pin);
}
