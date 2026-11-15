/*
 * mehanizam.c
 *
 *  Created on: Nov 4, 2026
 *      Author: Lea
 */
#include "main.h"

void front_pocetna() {
	ax_move(1, 504, 500); //zakrene
	HAL_Delay(500);
	ax_move(3, 503, 500); //zakrene
	HAL_Delay(500);
	ax_move(2, 827, 500); //zakrene
	HAL_Delay(500);

}
void front_mechanism() {

	HAL_Delay(1500);
	ax_move(2, 503, 500); //zakrene
	HAL_Delay(1500);

	ax_move(3, 205, 500); //desni otvori
	HAL_Delay(1500);

	//pustaju i srednja i leva

	ax_move(3, 503, 500); //desni zatvori
	HAL_Delay(1500);

	//kapija

	ax_move(2, 827, 500); //zakrene da bi postavio kapiju
	HAL_Delay(1500);

	ax_move(1, 826, 500); //podize sa levim
	HAL_Delay(5000);

}
void back_pocetna() {
	ax_move(5, 504, 500);
	HAL_Delay(500);

	ax_move(7, 503, 500);
	HAL_Delay(500);

	ax_move(6, 827, 500);
	HAL_Delay(500);

}
void back_mechanism() {
	HAL_Delay(1500);

	ax_move(6, 503, 500); // zakrene
	HAL_Delay(1500);

	ax_move(7, 205, 500); // desni otvori
	HAL_Delay(1500);

	// pustaju i srednja i leva
	ax_move(7, 503, 500); // desni zatvori
	HAL_Delay(1500);

	// kapija
	ax_move(6, 827, 500); // zakrene da bi postavio kapiju
	HAL_Delay(1500);

	ax_move(5, 826, 500); // podize sa levim
	HAL_Delay(5000);

}

