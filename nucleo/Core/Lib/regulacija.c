/*
 * regulacija.c
 *
 *  Created on: Nov 3, 2026
 *      Author: Lea
 */

#include "main.h"
#include "odometrija.h"
#include "regulacija.h"

float lin_v;
float ang_v;

float err_v = 0;
float err_w = 0;

float ref_lin_v = 0;
float ref_ang_v = 0;

float Kp_v = 1;
float Ki_v = 1;

float integral_v = 0;
float output_v = 0;

float P_v = 0;
float I_v = 0;

float Kp_w = 1;
float Ki_w = 1;

float integral_w = 0;
float output_w = 0;

float P_w = 0;
float I_w = 0;

float integral_new = 0;
float output_new = 0;

void position_control_loop() {

	/*switch(tip ksretnje){
	 case 0: stoji;
	 case 1: rot;
	 case 2: xy;
	 }*/

	/*samo racuna ref a ulaz mi je zeljena pozicija i tip kretnje*/

}

void velocity_control_loop(float dt) {

	// LEA: kad ovde budes upisivala PWM, prvo proveri comm_motion_allowed() (comm.h).
	// Ako vrati 0 (ESP je utihnuo), pozovi pwm_set(0, 0) i preskoci regulaciju.
	// Bez toga comm.c ugasi motore samo jednom, a vec sledeci prolaz (1 ms) ih ponovo pokrene.

	lin_v = get_linear_velocity();
	ang_v = get_angular_velocity();

	err_v = ref_lin_v - lin_v;
	err_w = ref_ang_v - ang_v;

	output_v = PI_regulator_v(err_v, dt);
	output_w = PI_regulator_w(err_w, dt);

	//prosledjuje mi gresku u pid
	//iz pida dobijam upravljanje linearne i ugaone brzine u odnosu na err
	//na osnovu upravljanja lin + ug brzina = desni motor
	//lin - ug = levi

}

float PI_regulator_v(float error, float dt) {
	P_v = Kp_v * error;
	integral_v = anti_windup(error, dt, &integral_v, Kp_v, Ki_v);
	I_v = Ki_v * integral_v;
	output_v = P_v + I_v;

	if (output_v > 100)
		output_v = 100;
	else if (output_v < -100)
		output_v = -100;

	return output_v;

}

float PI_regulator_w(float error, float dt) {
	P_w = Kp_w * error;
	integral_w = anti_windup(error, dt, &integral_w, Kp_w, Ki_w);
	I_w = Ki_w * integral_w;
	output_w = P_w + I_w;

	if (output_w > 100)
		output_w = 100;
	else if (output_w < -100)
		output_w = -100;

	return output_w;

}
float integral_calculation(float error, float dt, float integral) {
	integral_new = integral + error * dt;

	return integral_new;
}

float anti_windup(float error, float dt, float *integral, float Kp, float Ki) {
	integral_new = integral_calculation(error, dt, *integral);

	output_new = Kp * error + Ki * integral_new;

	if (output_new > 100 && error > 0) {
		return *integral;
	}

	if (output_new < -100 && error < 0) {
		return *integral;
	}

	return integral_new;
}
