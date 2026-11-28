/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.h
  * @brief          : Header for main.c file.
  *                   This file contains the common defines of the application.
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

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef __MAIN_H
#define __MAIN_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "stm32f4xx_hal.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */
#include <stdint.h>
#include <math.h>
#include "watchdog.h"
#include "comm.h"
#include "tim.h"
#include "timer.h"
#include "chinch.h"
#include "encoder.h"
#include "odometrija.h"
#include "pwm.h"
#include "ax.h"
#include "regulacija.h"
#include "mehanizam.h"
#include "pneumatika.h"
#include "ir_senzori.h"
#include "taktike.h"

/* USER CODE END Includes */

/* Exported types ------------------------------------------------------------*/
/* USER CODE BEGIN ET */

/* USER CODE END ET */

/* Exported constants --------------------------------------------------------*/
/* USER CODE BEGIN EC */

/* USER CODE END EC */

/* Exported macro ------------------------------------------------------------*/
/* USER CODE BEGIN EM */

/* USER CODE END EM */

/* Exported functions prototypes ---------------------------------------------*/
void Error_Handler(void);

/* USER CODE BEGIN EFP */

/* USER CODE END EFP */

/* Private defines -----------------------------------------------------------*/
#define IN_IR_2_Pin GPIO_PIN_0
#define IN_IR_2_GPIO_Port GPIOC
#define Val3_Pin GPIO_PIN_1
#define Val3_GPIO_Port GPIOC
#define IN_IR_6_Pin GPIO_PIN_2
#define IN_IR_6_GPIO_Port GPIOC
#define Val2_Pin GPIO_PIN_3
#define Val2_GPIO_Port GPIOC
#define ENC_A_L_Pin GPIO_PIN_0
#define ENC_A_L_GPIO_Port GPIOA
#define ENC_B_L_Pin GPIO_PIN_1
#define ENC_B_L_GPIO_Port GPIOA
#define ENC_A_R_Pin GPIO_PIN_5
#define ENC_A_R_GPIO_Port GPIOA
#define IN_IR_8_Pin GPIO_PIN_7
#define IN_IR_8_GPIO_Port GPIOA
#define Val4_Pin GPIO_PIN_4
#define Val4_GPIO_Port GPIOC
#define IN_IR_7_Pin GPIO_PIN_5
#define IN_IR_7_GPIO_Port GPIOC
#define Val5_Pin GPIO_PIN_2
#define Val5_GPIO_Port GPIOB
#define Val1_Pin GPIO_PIN_12
#define Val1_GPIO_Port GPIOB
#define Vac3_Pin GPIO_PIN_13
#define Vac3_GPIO_Port GPIOB
#define Vac2_Pin GPIO_PIN_14
#define Vac2_GPIO_Port GPIOB
#define Vac1_Pin GPIO_PIN_15
#define Vac1_GPIO_Port GPIOB
#define PWM_R_Pin GPIO_PIN_7
#define PWM_R_GPIO_Port GPIOC
#define IN_IR_4_Pin GPIO_PIN_8
#define IN_IR_4_GPIO_Port GPIOC
#define IN_IR_5_Pin GPIO_PIN_9
#define IN_IR_5_GPIO_Port GPIOC
#define DIR_M_R_Pin GPIO_PIN_8
#define DIR_M_R_GPIO_Port GPIOA
#define DIR_M_L_Pin GPIO_PIN_9
#define DIR_M_L_GPIO_Port GPIOA
#define SLP_R_Pin GPIO_PIN_10
#define SLP_R_GPIO_Port GPIOA
#define UART_AX_3V3_Pin GPIO_PIN_11
#define UART_AX_3V3_GPIO_Port GPIOA
#define IN_IR_1_Pin GPIO_PIN_12
#define IN_IR_1_GPIO_Port GPIOA
#define OUT_MSW_1_Pin GPIO_PIN_10
#define OUT_MSW_1_GPIO_Port GPIOC
#define OUT_MSW_2_Pin GPIO_PIN_11
#define OUT_MSW_2_GPIO_Port GPIOC
#define Chinch_Pin GPIO_PIN_12
#define Chinch_GPIO_Port GPIOC
#define ENC_B_R_Pin GPIO_PIN_3
#define ENC_B_R_GPIO_Port GPIOB
#define Val6_Pin GPIO_PIN_4
#define Val6_GPIO_Port GPIOB
#define SLP_L_Pin GPIO_PIN_5
#define SLP_L_GPIO_Port GPIOB
#define PWM_L_Pin GPIO_PIN_6
#define PWM_L_GPIO_Port GPIOB
#define PWM_BLDC_Pin GPIO_PIN_8
#define PWM_BLDC_GPIO_Port GPIOB
#define IN_IR_3_Pin GPIO_PIN_9
#define IN_IR_3_GPIO_Port GPIOB

/* USER CODE BEGIN Private defines */

/* USER CODE END Private defines */

#ifdef __cplusplus
}
#endif

#endif /* __MAIN_H */
