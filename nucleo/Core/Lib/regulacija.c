/*
 * regulacija.c
 *
 * Created on: Nov 3, 2026
 * Author: Lea
 */

#include "main.h"

#define tolerancija 1 //videti
#define TOLERANCIJA_RAD 1 //videti
#define STOP 0
#define ROTACIJA 1
#define MOVE_TO_XY 2
#define KRIVOLINIJSKO 3

uint8_t tip_kretnje;

float lin_v = 0;
float ang_w = 0;

float err_v = 0;
float err_w = 0;

float ref_lin_v = 0;
float ref_ang_w = 0;

float output_v = 0;
float output_w = 0;

float left = 0;
float right = 0;

float ref_distance;
float ref_ang;
float err_distance = 0;
float err_ang = 0;
float movement_completed = 0;

PID_t PID_linearni = { .Kp = 1, .Ki = 1, .Kd = 0 };
PID_t PID_ugao = { .Kp = 1.5, .Ki = 1.5, .Kd = 0.0 };
PID_t PID_pozicija = { .Kp = 1, .Ki = 0, .Kd = 0 }; // mm  -> mm/s
PID_t PID_rotacija = { .Kp = 1, .Ki = 0, .Kd = 0 };   // rad -> rad/s

void position_control_loop(float dt) {
	switch (tip_kretnje) {
	case STOP:
		stop(dt);
		break;
	case ROTACIJA:
		rotacija(dt);
		break;
	case MOVE_TO_XY:
		move_to_xy(dt);
		break;
	case KRIVOLINIJSKO:
		krivolinijsko(dt);
		break;
	default:
		stop(dt);
		break;
	}
}

void stop(float dt) {
		ref_lin_v = 0;
		ref_ang_w = 0;
		reset_PID(&PID_pozicija, &err_distance);
		reset_PID(&PID_rotacija, &err_ang);
}

void velocity_control_loop(float dt) {
	lin_v = get_linear_velocity();
	ang_w = get_angular_velocity();

	err_v = ref_lin_v - lin_v;
	err_w = ref_ang_w - ang_w;

	output_v = PID_regulator(&PID_linearni, &err_v, dt);
	output_w = PID_regulator(&PID_ugao, &err_w, dt);
	left = output_v - output_w;
	right = output_v + output_w;
	if (left > 100)
		left = 100;
	if (left < -100)
		left = -100;
	if (right > 100)
		right = 100;
	if (right < -100)
		right = -100;
	motori_set(left, right);
}

float PID_regulator(PID_t *pid, float *error, float dt) {

	pid->P = pid->Kp * *error;
	pid->D = pid->Kd * D_regulator(pid, error, dt);
	pid->I = pid->Ki * anti_windup(pid, error, dt);

	pid->output = pid->P + pid->I + pid->D;

	if (pid->output > 100) {
		pid->output = 100;
	} else if (pid->output < -100) {
		pid->output = -100;
	}

	return pid->output;
}

float D_regulator(PID_t *pid, float *error, float dt) {
	pid->D = (*error - pid->error_prev) / dt;
	pid->error_prev = *error;
	return pid->D;
}

float anti_windup(PID_t *pid, float *error, float dt) {
	pid->integral_new = pid->integral + (*error) * dt;

	pid->I_new = pid->Ki * pid->integral_new;

	if ((pid->I_new > 100 && *error > 0) || (pid->I_new < -100 && *error < 0)) {
		return pid->integral;
	}

	pid->integral = pid->integral_new;

	return pid->integral;
}

void reset_PID(PID_t *pid, float *error) {
	pid->integral = 0;
	pid->error_prev = 0;
	pid->integral_new = 0;
	pid->output = 0;
	pid->P = 0;
	pid->I = 0;
	pid->D = 0;
	pid->I_new = 0;
	*error = 0;
}

