/*
 * encoder.c
 *
 *  Created on: Oct 23, 2026
 *      Author: Dell
 */

#include "main.h"
#include "tim.h"
#include "encoder.h"

int32_t encoder_value_left = 0;
int32_t encoder_value_right = 0;

int32_t delta_left = 0;
int32_t delta_right = 0;

int32_t encoder_left_poc = 0;
int32_t encoder_right_poc = 0;


void encoder_init(void)
{
    HAL_TIM_Encoder_Start(&htim2, TIM_CHANNEL_ALL);
    HAL_TIM_Encoder_Start(&htim5, TIM_CHANNEL_ALL);
}

int32_t encoder_speed_right(float dt) {
	encoder_value_right = __HAL_TIM_GET_COUNTER(&htim5);
	delta_right = encoder_value_right - encoder_right_poc;
	encoder_right_poc = encoder_value_right;
	return delta_right / dt;
}
int32_t encoder_speed_left(float dt) {
	encoder_value_left = __HAL_TIM_GET_COUNTER(&htim2);
	delta_left = encoder_value_left - encoder_left_poc;
	encoder_left_poc = encoder_value_left;
	return delta_left / dt;
}

