/*
 * pwm.c
 *
 *  Created on: Oct 31, 2026
 *      Author: Dell
 */
#include "main.h"
#include "tim.h"
#include "pwm.h"

uint32_t arr;
uint32_t ccr1 = 0;
uint32_t ccr2 = 0;

void pwm_init()
{
    HAL_TIM_PWM_Start(&htim3, TIM_CHANNEL_1);
    HAL_TIM_PWM_Start(&htim3, TIM_CHANNEL_2);
}

void pwm_set(uint8_t motor_left, uint8_t motor_right)
{
    arr = __HAL_TIM_GET_AUTORELOAD(&htim3);

    ccr1 = (arr + 1) * motor_left / 100;      //formula za ccr je (arr+1) * duty cycle / 100
    ccr2 = (arr + 1) * motor_right / 100;

    __HAL_TIM_SET_COMPARE(&htim3, TIM_CHANNEL_1, ccr1);
    __HAL_TIM_SET_COMPARE(&htim3, TIM_CHANNEL_2, ccr2);
}
