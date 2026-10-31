/*
 * pwm.c
 *
 *  Created on: Oct 31, 2026
 *      Author: Dell
 */
#include "main.h"
#include "tim.h"
#include "pwm.h"

void pwm_init()
{
    HAL_TIM_PWM_Start(&htim3, TIM_CHANNEL_1);
    HAL_TIM_PWM_Start(&htim3, TIM_CHANNEL_2);
}
