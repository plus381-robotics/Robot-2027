/*
 * timer.h
 *
 *  Created on: Oct 14, 2026
 *      Author: Dell
 */
#ifndef INC_TIMER_H_
#define INC_TIMER_H_

void timer10_isr();
void time_start();
uint32_t get_time_ms();
uint8_t timer_delay(uint32_t *start_time, uint32_t delay);

int32_t get_left_encoder();
int32_t get_right_encoder();
#endif /* INC_TIMER_H_ */
