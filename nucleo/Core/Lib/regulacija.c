/*
 * regulacija.c
 *
 *  Created on: Nov 3, 2026
 *      Author: Lea
 */

#include "main.h"
#include "odometrija.h"

float lin_v;
float ang_v;
float err_v = 0;
float err_w = 0;
float ref_lin_v = 0;
float ref_ang_v = 0;

float Kp = 1;
float Ki = 1;
float integral = 0;
float output = 0;
float P = 0;
float I = 0;
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
	//err_w = ref_ang_v - ang_v;
	output = PI_regulator(err_v, dt);
	//prosledjuje mi gresku u pid
	//iz pida dobijam upravljanje linearne i ugaone brzine u odnosu na err
	//na osnovu upravljanja lin + ug brzina = desni motor
	//lin - ug = levi
}
float PI_regulator(float error, float dt) {
	P = Kp * error;
	integral = anti_windup(error, dt);
	I = Ki * integral;
	output = P + I;

	if (output > 100) {
		output = 100;
	} else if (output < 0) {
		output = 0;
	}
	return output;
}

float anti_windup(float error, float dt) {
	integral_new = integral + error * dt;
	output_new = Kp * error + Ki * integral_new;
	if (output_new > 100 && error > 0) {
		return integral;
	}
	if (output_new < -100 && error < 0) {
		return integral;
	}
	return integral_new;
}
