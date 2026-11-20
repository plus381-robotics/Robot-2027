/*
 * regulacija.c
 *
 * Created on: Nov 3, 2026
 * Author: Lea
 */

#include "main.h"

#define TOLERANCIJA_MM 1 //videti
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

PID_t PID_v = { .Kp = 1, .Ki = 1, .Kd = 0 };
PID_t PID_w = { .Kp = 1.5, .Ki = 1.5, .Kd = 0.0 };

PID_t PID_distanca = { .Kp = 1, .Ki = 0, .Kd = 0 };
PID_t PID_ang = { .Kp = 1, .Ki = 0, .Kd = 0 };

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
		reset_PIDs();
}

void rotacija(float dt) {
	err_ang = ogranicenje_phi(ref_ang) - get_phi_pos_rob(); //videti da li automatski ide u +-pi
	err_ang = ogranicenje_phi(err_ang);
	ref_ang_w = PID_regulator(&PID_ang, &err_ang, dt);
	ref_lin_v = 0;
	if (fabsf(err_ang) < TOLERANCIJA_RAD) {
		movement_completed = 1;
		tip_kretnje = STOP;
	}
}

void velocity_control_loop(float dt) {
	lin_v = get_linear_velocity();
	ang_w = get_angular_velocity();

	err_v = ref_lin_v - lin_v;
	err_w = ref_ang_w - ang_w;

	output_v = PID_regulator(&PID_v, &err_v, dt);
	output_w = PID_regulator(&PID_w, &err_w, dt);
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
float get_distance(float ref_x, float ref_y){
	float dx = get_x_pos_rob() - ref_x;
	float dy = get_y_pos_rob() - ref_y;
	return sqrtf(dx * dx + dy * dy);
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
void reset_PIDs() {
	reset_PID(&PID_v, &err_v);
	reset_PID(&PID_w, &err_w);
	reset_PID(&PID_distanca, &err_distance);
	reset_PID(&PID_ang, &err_ang);
}
