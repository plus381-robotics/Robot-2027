/*
 * odometrija.c
 *
 *  Created on: Oct 27, 2026
 *      Author: Dell
 */
#include "main.h"
#include "tim.h"
#include "encoder.h"
#include "odometrija.h"

float D = 0.3; //razmak izmedju tockova
float d_left = 0.07; //precnik levog
float d_right = 0.07; //precnik desnog

volatile float v_left;
volatile float v_right;

volatile float linear_velocity = 1;
volatile float angular_velocity = 1;

volatile float x = 0;
volatile float y = 0;
volatile float phi = 0;

void update_odometrija(float w_left, float w_right, float dt) {
	v_left = w_left * (d_left / 2);
	v_right = w_right * (d_right / 2);

	linear_velocity = (v_left + v_right) / 2;
	angular_velocity = (v_right - v_left) / D;

	x += linear_velocity * cos(phi + (angular_velocity * dt) / 2);
	y += linear_velocity * sin(phi + (angular_velocity * dt) / 2);
	phi += angular_velocity * dt;

}

float get_pos_rob() {
	return x, y, phi;
}
