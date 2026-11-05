/*
 * mehanizam.c
 *
 *  Created on: Nov 4, 2026
 *      Author: Lea
 */
#include "main.h"

void front_mechanism() {
	//lift
	ax_move(4, 30, 500);//malo podigne
	HAL_Delay(1500);
	//levi
	ax_move(1, 30, 500); //sa u2d2 videti poziciju
	HAL_Delay(150);
	//desni
	ax_move(3, 30, 500);
	HAL_Delay(150);
	//lift
	ax_move(4, 30, 500);//puno podigne
	HAL_Delay(1500);




}
void back_mechanism() {

}

