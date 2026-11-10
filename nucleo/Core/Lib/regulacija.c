/*
 * regulacija.c
 *
 * Created on: Nov 3, 2026
 * Author: Lea
 */

#include "main.h"
#include "odometrija.h"
#include "regulacija.h"

// GLOBALNE PROMENLJIVE

float lin_v = 0;

float err_v = 0;
float err_v_prev = 0;

float ref_lin_v = 0;

float Kp_v = 1;
float Ki_v = 1;
float Kd_v = 1;

float integral_v = 0;
float integral_new = 0;

float P_v = 0;
float I_v = 0;
float D_v = 0;

float output_v = 0;
float output_new = 0;

// POSITION CONTROL

void position_control_loop() {
	/*
	 * Ovde kasnije racunamo referentnu
	 * linearnu brzinu na osnovu pozicije.
	 */
}

void velocity_control_loop(float dt) {
	lin_v = get_linear_velocity();

	err_v = ref_lin_v - lin_v;

	output_v = PID_regulator_v(err_v, dt);
}

// PID REGULATOR

float PID_regulator_v(float error, float dt) {

	P_v = Kp_v * error;
	I_v = Ki_v * anti_windup(error, dt);
	D_v = Kd_v * D_regulator(error, dt);

	output_v = P_v + I_v + D_v;

	if (output_v > 100) {
		output_v = 100;
	} else if (output_v < -100) {
		output_v = -100;
	}

	return output_v;
}

float D_regulator(float error, float dt) {
	D_v = (error - err_v_prev) / dt;
	err_v_prev = error;
	return D_v;
}

float integral_calculation(float error, float dt) {
	return integral_v + error * dt;
}

float anti_windup(float error, float dt) {
	integral_new = integral_calculation(error, dt);

	output_new = Kp_v * error + Ki_v * integral_new;

	if (output_new > 100 && error > 0) {
		return integral_v;
	}

	if (output_new < -100 && error < 0) {
		return integral_v;
	}

	integral_v = integral_new;

	return integral_v;
}

