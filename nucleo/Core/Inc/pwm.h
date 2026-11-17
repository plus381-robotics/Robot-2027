/*
 * pwm.h
 *
 *  Created on: Oct 31, 2026
 *      Author: Lea
 */

#ifndef INC_PWM_H_
#define INC_PWM_H_

void pwm_init();
void motori_set(float motor_left, float motor_right);
void pwm_set(float motor_left, int8_t smer_l, float motor_right, int8_t smer_r);

#endif /* INC_PWM_H_ */
