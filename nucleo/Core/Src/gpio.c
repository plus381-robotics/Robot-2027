/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file    gpio.c
  * @brief   This file provides code for the configuration
  *          of all used GPIO pins.
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2026 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */
/* USER CODE END Header */

/* Includes ------------------------------------------------------------------*/
#include "gpio.h"

/* USER CODE BEGIN 0 */

/* USER CODE END 0 */

/*----------------------------------------------------------------------------*/
/* Configure GPIO                                                             */
/*----------------------------------------------------------------------------*/
/* USER CODE BEGIN 1 */

/* USER CODE END 1 */

/** Configure pins
*/
void MX_GPIO_Init(void)
{

  GPIO_InitTypeDef GPIO_InitStruct = {0};

  /* GPIO Ports Clock Enable */
  __HAL_RCC_GPIOC_CLK_ENABLE();
  __HAL_RCC_GPIOA_CLK_ENABLE();
  __HAL_RCC_GPIOB_CLK_ENABLE();

  /*Configure GPIO pin Output Level */
  HAL_GPIO_WritePin(GPIOC, Val3_Pin|Val2_Pin|Val4_Pin, GPIO_PIN_RESET);

  /*Configure GPIO pin Output Level */
  HAL_GPIO_WritePin(GPIOB, Val5_Pin|Val1_Pin|Vac3_Pin|Vac2_Pin
                          |Vac1_Pin|Val6_Pin, GPIO_PIN_RESET);

  /*Configure GPIO pin Output Level */
  HAL_GPIO_WritePin(GPIOA, DIR_M_R_Pin|DIR_M_L_Pin, GPIO_PIN_RESET);

  /*Configure GPIO pin Output Level */
  HAL_GPIO_WritePin(SLP_R_GPIO_Port, SLP_R_Pin, GPIO_PIN_SET);

  /*Configure GPIO pin Output Level */
  HAL_GPIO_WritePin(SLP_L_GPIO_Port, SLP_L_Pin, GPIO_PIN_SET);

  /*Configure GPIO pins : IN_IR_2_Pin IN_IR_6_Pin IN_IR_7_Pin IN_IR_4_Pin
                           IN_IR_5_Pin OUT_MSW_1_Pin OUT_MSW_2_Pin */
  GPIO_InitStruct.Pin = IN_IR_2_Pin|IN_IR_6_Pin|IN_IR_7_Pin|IN_IR_4_Pin
                          |IN_IR_5_Pin|OUT_MSW_1_Pin|OUT_MSW_2_Pin;
  GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  HAL_GPIO_Init(GPIOC, &GPIO_InitStruct);

  /*Configure GPIO pins : Val3_Pin Val2_Pin Val4_Pin */
  GPIO_InitStruct.Pin = Val3_Pin|Val2_Pin|Val4_Pin;
  GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(GPIOC, &GPIO_InitStruct);

  /*Configure GPIO pins : IN_IR_8_Pin IN_IR_1_Pin */
  GPIO_InitStruct.Pin = IN_IR_8_Pin|IN_IR_1_Pin;
  GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

  /*Configure GPIO pins : Val5_Pin Val1_Pin Vac3_Pin Vac2_Pin
                           Vac1_Pin Val6_Pin SLP_L_Pin */
  GPIO_InitStruct.Pin = Val5_Pin|Val1_Pin|Vac3_Pin|Vac2_Pin
                          |Vac1_Pin|Val6_Pin|SLP_L_Pin;
  GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(GPIOB, &GPIO_InitStruct);

  /*Configure GPIO pins : DIR_M_R_Pin DIR_M_L_Pin SLP_R_Pin */
  GPIO_InitStruct.Pin = DIR_M_R_Pin|DIR_M_L_Pin|SLP_R_Pin;
  GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

  /*Configure GPIO pin : Chinch_Pin */
  GPIO_InitStruct.Pin = Chinch_Pin;
  GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
  GPIO_InitStruct.Pull = GPIO_PULLDOWN;
  HAL_GPIO_Init(Chinch_GPIO_Port, &GPIO_InitStruct);

  /*Configure GPIO pin : IN_IR_3_Pin */
  GPIO_InitStruct.Pin = IN_IR_3_Pin;
  GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  HAL_GPIO_Init(IN_IR_3_GPIO_Port, &GPIO_InitStruct);

}

/* USER CODE BEGIN 2 */

/* USER CODE END 2 */
