/*
 * regulacija.h
 *
 *  Created on: Nov 3, 2026
 *      Author: Lea
 */

#ifndef INC_REGULACIJA_H_
#define INC_REGULACIJA_H_

void position_control_loop();
void velocity_control_loop(float dt);
float PI_regulator_v(float error, float dt);
float PI_regulator_w(float error, float dt);
float anti_windup(float error, float dt, float *integral, float Kp, float Ki);
float integral_calculation(float error, float dt, float integral);

#endif /* INC_REGULACIJA_H_ */
