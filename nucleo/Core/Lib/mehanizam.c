/*
 * mehanizam.c
 *
 *  Created on: Nov 4, 2026
 *      Author: Lea
 */
#include "main.h"

void front_mechanism() {
	ax_move(4, 30, 500);//malo podigne
	HAL_Delay(1500);

	ax_move(2, 30, 500);//zakrene
	HAL_Delay(1500);

	ax_move(3, 30, 500);//ostavi desnu
	HAL_Delay(1500);

	//ostavi srednju

	ax_move(2, 30, 500); //rotira se
	HAL_Delay(1500);

	ax_move(4, 30, 500);//malo vise podigne
	HAL_Delay(1500);

	//ostavi levu



}
void back_mechanism() {

}

