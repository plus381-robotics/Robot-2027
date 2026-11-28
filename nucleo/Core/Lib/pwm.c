/*
 * pwm.c
 *
 *  Created on: Oct 31, 2026
 *      Author: Lea
 */

#include "main.h"
#define LEVI_NAPRED    GPIO_PIN_SET   // DIR pin = 0 V -> drajver vrti levi motor napred
#define LEVI_NAZAD     GPIO_PIN_RESET     // DIR pin = 3.3 V -> drajver vrti levi motor nazad

#define DESNI_NAPRED   GPIO_PIN_RESET
#define DESNI_NAZAD    GPIO_PIN_SET

uint32_t arr;
uint32_t ccr1 = 0;
uint32_t ccr2 = 0;
int8_t motor_left_sign = 0;
int8_t motor_right_sign = 0;

void pwm_init() {
	HAL_TIM_PWM_Start(&htim4, TIM_CHANNEL_1); //levi
	HAL_TIM_PWM_Start(&htim3, TIM_CHANNEL_2); //desni
}
void motori_set(float motor_left, float motor_right) {
	if (motor_left < 0) { //treba da ize nazad u ovoj petlji
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
	// Ne pozivati direktno! koristiti motori_set() petre tebi pricam

	if (smer_l  == 1)
		HAL_GPIO_WritePin(DIR_M_L_GPIO_Port, DIR_M_L_Pin, LEVI_NAPRED);
	else
		HAL_GPIO_WritePin(DIR_M_L_GPIO_Port, DIR_M_L_Pin, LEVI_NAZAD);
	if (smer_r == 1)
		HAL_GPIO_WritePin(DIR_M_R_GPIO_Port, DIR_M_R_Pin, DESNI_NAPRED);
	else
		HAL_GPIO_WritePin(DIR_M_R_GPIO_Port, DIR_M_R_Pin, DESNI_NAZAD);

	arr = __HAL_TIM_GET_AUTORELOAD(&htim4);

	ccr1 = (arr + 1) * motor_left / 100; //formula za ccr je (arr+1) * duty cycle / 100
	ccr2 = (arr + 1) * motor_right / 100;

	__HAL_TIM_SET_COMPARE(&htim4, TIM_CHANNEL_1, ccr1);
	__HAL_TIM_SET_COMPARE(&htim3, TIM_CHANNEL_2, ccr2);
}
