/*
 * encoder.h
 *
 *  Created on: Oct 23, 2026
 *      Author: Lea
 */

#ifndef INC_ENCODER_H_
#define INC_ENCODER_H_

void encoder_init();
float encoder_speed_left(float dt);
float encoder_speed_right(float dt);
float get_left_encoder();
float get_right_encoder();
void encoder_update(float dt);
float get_speed_left();
float get_speed_right();

#endif /* INC_ENCODER_H_ */
