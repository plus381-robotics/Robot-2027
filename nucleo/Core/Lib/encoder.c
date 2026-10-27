/*
 * encoder.c
 *
 *  Created on: Oct 23, 2026
 *      Author: Dell
 */

#include "main.h"
#include "tim.h"
#include "encoder.h"

volatile int32_t encoder_value_left = 0;
volatile int32_t encoder_value_right = 0;

volatile float delta_left = 0;
volatile float delta_right = 0;

volatile int32_t encoder_left_poc = 0;
volatile int32_t encoder_right_poc = 0;

const static uint16_t incr_total = 8192;
static float inc2rad;

void encoder_init(void) {
	HAL_TIM_Encoder_Start(&htim2, TIM_CHANNEL_ALL);
	HAL_TIM_Encoder_Start(&htim5, TIM_CHANNEL_ALL);
	inc2rad = 2 * M_PI / incr_total;
}

float encoder_speed_right(float dt) {
	encoder_value_right = (int16_t)__HAL_TIM_GET_COUNTER(&htim5);
	delta_right = encoder_value_right - encoder_right_poc;
	encoder_right_poc = encoder_value_right;
	return delta_right * inc2rad / dt;
}

float encoder_speed_left(float dt) {
	encoder_value_left = (int16_t)__HAL_TIM_GET_COUNTER(&htim2);
	delta_left = encoder_value_left - encoder_left_poc;
	encoder_left_poc = encoder_value_left;
	return delta_left * inc2rad / dt;
}

int32_t get_left_encoder() {
	return encoder_value_left;
}

int32_t get_right_encoder() {
	return encoder_value_right;
}
