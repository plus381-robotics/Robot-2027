/*
 * ax.c
 *
 * Created on: Nov 1, 2026
 * Author: Lea
 */

#include "main.h"
#include "usart.h"


void
torque_enable (uint8_t id)
{
	uint16_t checksum_local = id + 4 + 3 + 0x18 + 1;
	uint8_t checksum = (uint8_t) (~checksum_local);
	uint8_t ax_move[] =
		{ 0xff, 0xff, id, 0x04, 0x03, 0x18, 0x01, checksum };

	HAL_UART_Transmit (&huart6, ax_move, 8, 200);
	HAL_Delay (50);
}

void
ax_move (uint8_t id, uint16_t angle, uint16_t speed, UART_HandleTypeDef huart)
{
	uint8_t angle_low, angle_high, speed_low, speed_high;
	angle_low = angle & 0xff;
	angle_high = angle >> 8;
	speed_low = speed & 0xff;
	speed_high = speed >> 8;

	uint16_t checksum_local = id + 7 + 3 + 0x1e + angle_low + angle_high + speed_low + speed_high;
	uint8_t checksum = (uint8_t) (~checksum_local);
	uint8_t ax_move[] =
		{ 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, id, 0x07, 0x03, 0x1E, angle_low, angle_high, speed_low, speed_high, checksum};

	HAL_UART_Transmit (&huart, ax_move, 17, 100);
	HAL_Delay (1);
	HAL_UART_Transmit (&huart, ax_move, 17, 100);
	HAL_Delay (1);
//	HAL_UART_Transmit (&huart, ax_move, 17, 100);
//	HAL_Delay (1);
	HAL_UART_Transmit (&huart, ax_move, 17, 100);
	HAL_Delay (6);
}
