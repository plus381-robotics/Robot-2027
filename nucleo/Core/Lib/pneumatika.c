/*
 * pneumatika.c
 *
 *  Created on: Nov 21, 2026
 *      Author: Lea
 */

#ifndef LIB_PNEUMATIKA_C_
#define LIB_PNEUMATIKA_C_

#include "main.h"

void pneumatika_init() {
	HAL_GPIO_WritePin(Val1_GPIO_Port, Val1_Pin, GPIO_PIN_RESET);
	HAL_GPIO_WritePin(Val2_GPIO_Port, Val2_Pin, GPIO_PIN_RESET);
	HAL_GPIO_WritePin(Val3_GPIO_Port, Val3_Pin, GPIO_PIN_RESET);
	HAL_GPIO_WritePin(Val4_GPIO_Port, Val4_Pin, GPIO_PIN_RESET);
	HAL_GPIO_WritePin(Val5_GPIO_Port, Val5_Pin, GPIO_PIN_RESET);
	HAL_GPIO_WritePin(Val6_GPIO_Port, Val6_Pin, GPIO_PIN_RESET);

	HAL_GPIO_WritePin(Vac1_GPIO_Port, Vac1_Pin, GPIO_PIN_RESET);
	HAL_GPIO_WritePin(Vac2_GPIO_Port, Vac2_Pin, GPIO_PIN_RESET);
	HAL_GPIO_WritePin(Vac3_GPIO_Port, Vac3_Pin, GPIO_PIN_RESET);
}

#endif /* LIB_PNEUMATIKA_C_ */
