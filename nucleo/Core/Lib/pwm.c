/*
 * pwm.c
 *
 *  Created on: Oct 31, 2026
 *      Author: Lea
 */

#include "main.h"
#include "tim.h"
#include "pwm.h"

uint32_t arr;
uint32_t ccr1 = 0;
uint32_t ccr2 = 0;
int8_t motor_left_sign = 0;
int8_t motor_right_sign = 0;

void pwm_init() {
	HAL_TIM_PWM_Start(&htim3, TIM_CHANNEL_1);
	HAL_TIM_PWM_Start(&htim3, TIM_CHANNEL_2);
}
void motori_set(float motor_left, float motor_right) {
	if (motor_left < 0) {
		motor_left = fabsf(motor_left);
		motor_left_sign = -1;
	} else
		motor_left_sign = 1;

	if (motor_right < 0) {
		motor_right = fabsf(motor_right);
		motor_right_sign = -1;
	} else
		motor_right_sign = 1;
	pwm_set(motor_left, motor_left_sign, motor_right, motor_right_sign);
}

void pwm_set(float motor_left, int8_t smer_l, float motor_right, int8_t smer_r) {
	//TODO smer motora
	// Ne pozivati direktno! koristiti motori_set() petre tebi pricam
	arr = __HAL_TIM_GET_AUTORELOAD(&htim3);

	ccr1 = (arr + 1) * motor_left / 100; //formula za ccr je (arr+1) * duty cycle / 100
	ccr2 = (arr + 1) * motor_right / 100;

	__HAL_TIM_SET_COMPARE(&htim3, TIM_CHANNEL_1, ccr1);
	__HAL_TIM_SET_COMPARE(&htim3, TIM_CHANNEL_2, ccr2);
}
