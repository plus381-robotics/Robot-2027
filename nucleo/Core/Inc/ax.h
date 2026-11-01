/*
 * ax.h
 *
 * Created on: Nov 1, 2026
 * Author: Lea
 */

#ifndef INC_AX_H_
#define INC_AX_H_


void torque_enable (uint8_t id);

void ax_move (uint8_t id, uint16_t angle, uint16_t speed, UART_HandleTypeDef huart);

#endif
