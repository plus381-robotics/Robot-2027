/*
 * encoder.c
 *
 *  Created on: Nov 18, 2025
 *      Author: Lea
 */

#include "main.h"
#include "tim.h"


//volatile int16_t trenutna = 0;
//int16_t speed_of_encoder_right_passive() {
//	int16_t speed = (int16_t) TIM2->CNT - trenutna;
//	trenutna = (int16_t) TIM2->CNT;
//
//	return speed;
//}

int16_t cnt_difference(TIM_HandleTypeDef *htim, volatile int16_t *cur) {
	int16_t diff = (int16_t) (htim->Instance->CNT) - *cur;
	*cur = (int16_t) htim->Instance->CNT;
	return diff;
}

void enc_start(TIM_HandleTypeDef *htim) {
	HAL_TIM_Encoder_Start(htim, TIM_CHANNEL_ALL);
}

void enc_init() {
	enc_start(&htim2);
	enc_start(&htim3);
	enc_start(&htim4);
	enc_start(&htim5);
}

double enc_velocity(int16_t diff, double deltaT, uint16_t impulse_per_2Pi) {
	// TODO: proveri u ros-u u kojim jedinicama su brzine
	double vel, ang;
	ang = (double) diff / (double) impulse_per_2Pi * 2 * M_PI;	// predjeni ugao u radijanima
	vel = ang / deltaT;
	return vel;
}

