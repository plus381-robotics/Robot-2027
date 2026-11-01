/*
 * ax.c
 *
 * Created on: Nov 1, 2026
 * Author: Lea
 */

#include "main.h"
#include "ax.h"
#include "usart.h"

// UKLJUČIVANJE MOMENTA MOTORA (TORQUE ENABLE)
void torque_enable(uint8_t id, UART_HandleTypeDef *huart) {
	uint16_t checksum_local = id + 4 + 3 + 0x18 + 1;

	uint8_t checksum = (uint8_t) (~checksum_local);

	uint8_t packet[] = { 0xFF, 0xFF, id, 0x04, 0x03, 0x18, 0x01, checksum };

	HAL_UART_Transmit(huart, packet, sizeof(packet), 200);

	HAL_Delay(50);
}

void ax_move(uint8_t id, uint16_t angle, uint16_t speed,
		UART_HandleTypeDef *huart) {
	uint8_t angle_low;
	uint8_t angle_high;

	uint8_t speed_low;
	uint8_t speed_high;

	angle_low = angle & 0xFF;
	angle_high = (angle >> 8) & 0xFF;

	speed_low = speed & 0xFF;
	speed_high = (speed >> 8) & 0xFF;

	uint16_t checksum_local = id + 7 + 3 + 0x1E + angle_low + angle_high
			+ speed_low + speed_high;

	uint8_t checksum = (uint8_t) (~checksum_local);

	uint8_t packet[] = { 0xFF, 0xFF, id, 0x07, 0x03, 0x1E, angle_low,
			angle_high, speed_low, speed_high, checksum };

	HAL_UART_Transmit(huart, packet, sizeof(packet), 100);

	HAL_Delay(6);
}
void ax_write(uint8_t id, uint8_t addr, uint8_t *data, uint8_t n) {
	uint8_t p[16];
	uint8_t len = n + 3;               // instr + addr + data + checksum
	uint8_t sum = id + len + 0x03 + addr;
	p[0] = 0xFF;
	p[1] = 0xFF;
	p[2] = id;
	p[3] = len;
	p[4] = 0x03;
	p[5] = addr;
	for (int i = 0; i < n; i++) {
		p[6 + i] = data[i];
		sum += data[i];
	}
	p[6 + n] = ~sum;
	HAL_HalfDuplex_EnableTransmitter(&huart6);
	HAL_UART_Transmit(&huart6, p, 7 + n, 10);
	HAL_HalfDuplex_EnableReceiver(&huart6);
}
