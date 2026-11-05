/*
 * encoder.h
 *
 *  Created on: Oct 23, 2026
 *      Author: Dell
 */

#ifndef INC_ENCODER_H_
#define INC_ENCODER_H_

void encoder_init();
float encoder_speed_left(float dt);
float encoder_speed_right(float dt);
int32_t get_left_encoder();
int32_t get_right_encoder();

#endif /* INC_ENCODER_H_ */
