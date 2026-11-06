/*
 * comm.c
 *
 *  Created on: Dec 9, 2025
 *      Author: lazar
 */
#define TXBUFFERSIZE 40
#define RXBUFFERSIZE 40

#include "main.h"
#include <string.h>

static uint16_t fletcher16(uint8_t *data, size_t len);
static uint8_t create_rxba();

volatile uint8_t tx_buffer[TXBUFFERSIZE], rx_buffer[RXBUFFERSIZE];
volatile uint8_t rxba[32];
volatile uint32_t rc = 0;
volatile int16_t x10k, y10k, phi2B;
volatile int16_t v_left_2B, v_right_2B;
volatile float v_left_comm, v_right_comm;
volatile uint16_t v_left_pwm, v_right_pwm;
volatile double phi_conversion;
volatile static uint16_t sync = 0;
volatile static uint8_t idx = 0;
volatile float x, y, phi;
uint16_t prev_checksum = 0;
volatile goal_type rx_goal;
double x_dbg = -1.0, y_dbg = 0.0, phi_dbg = 1.5708;
int8_t type_dbg = 1;
//static double PHI_TOL_ = 0.0314, D_TOL_ = 0.02;
/*
 * ROS2 -> STM32:
 * 40B:
 * 	 8 * uint8 255
 * 	 int8 type
 * 	 double x
 * 	 double y
 * 	 double phi
 * 	 int8 	obstacle	:6
 * 	 		direction 	:2
 * 	 uint8 	v_max_100				[0.00, 2.55]
 * 	 uint8 	w_max_10				[0.0, 25.5]
 * 	 uint8 	dis_tol_perc_16: 4	[0.0, 1.0 : 0.0625]
 * 	 		ang_tol_perc_16: 4	[0.0, 1.0 : 0.0625]
 * 	 int8	start_coeff_v_4: 2	[0.0, 1.0 : 0.25]
 * 	 		start_coeff_w_4: 2	[0.0, 1.0 : 0.25]
 * 	 		stop_coeff_v_4:  2	[0.0, 1.0 : 0.25]
 * 	 		stop_coeff_w_4:  2	[0.0, 1.0 : 0.25]
 * 	 uint16 checksum
 *
 * STM32 -> ROS2:
 * 40B:
 *	 int8	status kratnje
 *	 int32	x_10k
 *	 int32	y_10k
 *	 int32	phi_10k
 *	 int32	v_10k
 *	 int32	w_10k

 */

void process_rx_buffer() {
	if (!create_rxba())
		return;

	rx_goal.obstacle = (rxba[25]) & 0b011;
	int8_t type = rxba[0];

	uint16_t received_checksum = rxba[30] | (rxba[31] << 8);

	// kill
	if (type == 0 || type == 10)
		rx_goal.type = type;
	// kretnja vec ide
	if (rx_goal.status > 0)
		return;

	// ako ponovo dobije istu kretnju
	if (prev_checksum == received_checksum)
		return;

	double x, y, phi;
	memcpy(&x, &rxba[1], sizeof(double));
	memcpy(&y, &rxba[9], sizeof(double));
	memcpy(&phi, &rxba[17], sizeof(double));
//
//	double dx = x - get_x();
//	double dy = y - get_y();
//	double dist2 = sqrt(dx * dx + dy * dy);
//
//	double dphi = phi - get_phi();
//	while (dphi > M_PI)
//		dphi -= 2 * M_PI;
//	while (dphi < -M_PI)
//		dphi += 2 * M_PI;
//
//	// Skip goal if already reached
//	if ((type == 1 && dist2 < D_TOL_)
//			|| (type == -1 && fabs(dphi) < PHI_TOL_)) {
////		reset_goal(&rx_goal);
////		prev_checksum = received_checksum;
//		return;
//	}

	rx_goal.type = type;
	rx_goal.x = x;
	rx_goal.y = y;
	rx_goal.phi = phi;
	uint8_t dir_bits = (rxba[25] >> 6) & 0b11;

	if (dir_bits == 0b01)
		rx_goal.direction = 1;
	else if (dir_bits == 0b10)
		rx_goal.direction = -1;
	else
		rx_goal.direction = 0;
	uint8_t v_max_100 = rxba[26];
	rx_goal.v_max = v_max_100 * 0.01;
	uint8_t w_max_10 = rxba[27];
	rx_goal.w_max = w_max_10 * 0.1;
	// TODO: ovde sam zapravo na pogresnu stranu racunao ovo, tako da za sad zanemari, pa ako treba ispravljaj
//	uint8_t tol_byte = rxba[28];
//	rx_goal.distance_tolerance_percentage = (((tol_byte >> 4) & 0b1111) + 1)
//			* 0.0625;
//	rx_goal.angle_tolerance_percentage = (((tol_byte) & 0b1111) + 1) * 0.0625;
//	uint8_t coeff_byte = rxba[29];
//	rx_goal.start_coeff_v = (((coeff_byte >> 6) & 0b11) + 1) * 0.25;
//	rx_goal.start_coeff_w = (((coeff_byte >> 4) & 0b11) + 1) * 0.25;
//	rx_goal.stop_coeff_v = (((coeff_byte >> 2) & 0b11) + 1) * 0.25;
//	rx_goal.stop_coeff_w = (((coeff_byte) & 0b11) + 1) * 0.25;
	rx_goal.distance_tolerance_percentage = 1.0;
	rx_goal.angle_tolerance_percentage = 1.0;
	rx_goal.start_coeff_v = 1.0;
	rx_goal.start_coeff_w = 1.0;
	rx_goal.stop_coeff_v = 1.0;
	rx_goal.stop_coeff_w = 1.0;
	prev_checksum = received_checksum;
	rx_goal.status = 0;
	return;
}

goal_type* get_rx_goal() {
	return &rx_goal;
}

void update_tx_buffer() {
	for (int i = 0; i < 8; i++)
		tx_buffer[i] = 0xFF;

// XXX: slanje cilja za kretnju, za testiranje
	// prvo metar
//	tx_buffer[8] = type_dbg;
//	memcpy(&tx_buffer[9], &x_dbg, sizeof(double));
//	memcpy(&tx_buffer[17], &y_dbg, sizeof(double));
//	memcpy(&tx_buffer[25], &phi_dbg, sizeof(double));
//	tx_buffer[33] = 1;      // direction
//	tx_buffer[34] = 150;    // v_max_100
//	tx_buffer[35] = 150;     // w_max_10
//	tx_buffer[36] = 0xff; 	// tol_perc_16
//	tx_buffer[37] = 0xff; 	// start/stop coeffs = 1

	if (rx_goal.type != 0)
		tx_buffer[8] = rx_goal.status;
	else
		tx_buffer[8] = 0;
	int32_t x = (int32_t) (get_x() * 10000.0);
	int32_t y = (int32_t) (get_y() * 10000.0);
	int32_t phi = (int32_t) (get_phi() * 10000.0);
	int32_t v = (int32_t) (get_v() * 10000.0);
	int32_t w = (int32_t) (get_w() * 10000.0);
	memcpy(&tx_buffer[9], &x, sizeof(int32_t));
	memcpy(&tx_buffer[13], &y, sizeof(int32_t));
	memcpy(&tx_buffer[17], &phi, sizeof(int32_t));
	memcpy(&tx_buffer[21], &v, sizeof(int32_t));
	memcpy(&tx_buffer[25], &w, sizeof(int32_t));
	memset(&tx_buffer[29], 0, 9);

	// checksum over payload bytes (8→37)
	uint16_t cksum = fletcher16(&tx_buffer[8], 30);
	tx_buffer[38] = cksum & 0xFF;
	tx_buffer[39] = cksum >> 8;

	huart1.gState = HAL_UART_STATE_READY;
	__HAL_UART_CLEAR_FLAG(&huart1, UART_FLAG_TC);
	HAL_UART_Transmit_DMA(&huart1, (uint8_t*) tx_buffer, TXBUFFERSIZE);

	if (rx_goal.status < 0)
		reset_goal(&rx_goal);
}

static uint16_t fletcher16(uint8_t *data, size_t len) {
	uint16_t sum1 = 0;
	uint16_t sum2 = 0;

	for (size_t i = 0; i < len; i++) {
		sum1 = (sum1 + data[i]) % 255;
		sum2 = (sum2 + sum1) % 255;
	}

	return (sum2 << 8) | sum1;
}
static uint8_t create_rxba() {
	int start_index = -1;

	for (int i = 0; i < RXBUFFERSIZE; i++) {
		int found = 1;

		for (int k = 0; k < 8; k++) {
			if (rx_buffer[(i + k) % RXBUFFERSIZE] != 0xFF) {
				found = 0;
				break;
			}
		}

		if (found) {
			start_index = (i + 8) % RXBUFFERSIZE;
			break;
		}
	}

	if (start_index < 0)
		return 0;

	// Copy 32 bytes with wrap
	for (int i = 0; i < 32; i++) {
		rxba[i] = rx_buffer[(start_index + i) % RXBUFFERSIZE];
	}

	return 1;
}

void comm_init() {
	rx_goal.status = 0;

	if (HAL_UART_Receive_DMA(&huart1, (uint8_t*) rx_buffer,
	RXBUFFERSIZE) != HAL_OK) {
		Error_Handler();
	}
//  if(HAL_UART_Transmit_DMA(&huart1, (uint8_t*)tx_buffer, TXBUFFERSIZE)!= HAL_OK)
//  {
//    Error_Handler();
//  }
}

void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart) {
//    HAL_UART_Receive_DMA(&huart1, (uint8_t *)rx_buffer, RXBUFFERSIZE);
	process_rx_buffer();
//	if (get_set_goal_reset())
//		reset_goal(&rx_goal);
}
