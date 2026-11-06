/*
 * time.c
 *
 *  Created on: Nov 18, 2025
 *      Author: Lea
 */
#include "main.h"
#include "tim.h"

static uint32_t sys_time_ms = 0;
volatile int16_t tim2_diff = 0, tim3_diff = 0, tim4_diff = 0, tim5_diff = 0;
volatile int16_t tim2_cur = 0, tim3_cur = 0, tim4_cur = 0, tim5_cur = 0;
volatile double vel_dbg;
volatile double motorCtrl, out_vel;
static uint8_t uart_psc = 100, uart_psc_cnt = 1;
float vl = 0.0, vr = 0.0;

void time_ISR()	// poziva se u stm32f4xx_it.c, na 1ms
{
	// TODO: u uint16_t (mzd bez u), postaviti pwm, napidovati

	sys_time_ms++;
	update_odom();
	control_loop();
//	vl = vel_dbg;
//	vr = -vel_dbg;
//	pwm_left(vl);
//	pwm_right(vr);

	uart_psc_cnt++;
	if (uart_psc_cnt >= uart_psc) {
		uart_psc_cnt = 0;
		update_tx_buffer();
	}
}

void time_start() {
	HAL_TIM_Base_Start_IT(&htim10);
}

void time_stop() {
	HAL_TIM_Base_Stop_IT(&htim10);
}
