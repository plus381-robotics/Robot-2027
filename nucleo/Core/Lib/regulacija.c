/*
 * regulacija.c
 *
 * Created on: Nov 3, 2026
 * Author: Lea
 */

#include "main.h"

#define TOLERANCIJA_MM 1 //mm videti
#define TOLERANCIJA_RAD 0.1 //rad videti
#define OGRANICENJE_UGLA_PRILIKOM_XY 15 //mm

#define STOP 0
#define ROTACIJA 1
#define MOVE_TO_XY 2
#define KRIVOLINIJSKO 3

volatile uint8_t tip_kretnje;
volatile uint8_t okrenuta = 1;

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

volatile float ref_ang;
float err_distance = 0;
float err_ang = 0;
volatile float movement_completed = 0;
volatile float ref_x = 0;
volatile float ref_y = 0;

PID_t PID_v = { .Kp = 1.0, .Ki = 1.0, .Kd = 0.0, .max_output = 100 };
PID_t PID_w = { .Kp = 1.5, .Ki = 1.5, .Kd = 0.0, .max_output = 100 };
PID_t PID_distanca = { .Kp = 1, .Ki = 0, .Kd = 0, .max_output = 500 };
PID_t PID_ang = { .Kp = 1, .Ki = 0, .Kd = 0, .max_output = 3 };

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
	err_ang = ogranicenje_phi(ref_ang) - get_phi_pos_rob();
	err_ang = ogranicenje_phi(err_ang);
	ref_ang_w = PID_regulator(&PID_ang, &err_ang, dt);
	ref_lin_v = 0;
	if (fabsf(err_ang) < TOLERANCIJA_RAD) {
		movement_completed = 1;
		tip_kretnje = STOP;
	}
}
uint8_t rotacija_to_xy(float dt) {
	err_ang = get_ugao_ka_cilju(ref_x, ref_y) - get_phi_pos_rob();
	err_ang = ogranicenje_phi(err_ang);
	if (fabsf(err_ang) < TOLERANCIJA_RAD) {
		return 1;
	}
	ref_ang_w = PID_regulator(&PID_ang, &err_ang, dt);
	ref_lin_v = 0;
	return 0;
}

void move_to_xy(float dt) {
	err_distance = get_distance(ref_x, ref_y);

	if (err_distance < TOLERANCIJA_MM) { //provera da li je stigao ako jeste izadje
		movement_completed = 1;
		tip_kretnje = STOP;
	}

	else {
		okrenuta = 1;
		if (err_distance > OGRANICENJE_UGLA_PRILIKOM_XY) { //ako je unutar r = OGRANICENJE_UGLA_PRILIKOM_XY da se ne okrece da ne bi podivljao ali treba videti da se smanjuje to na sto manje
			okrenuta = rotacija_to_xy(dt);
		}
		if (okrenuta == 1) {
			err_ang = get_ugao_ka_cilju(ref_x, ref_y) - get_phi_pos_rob();
			err_ang = ogranicenje_phi(err_ang);

			if (fabsf(err_ang) > M_PI / 2) { //preslo je koordinatu ako je vece od pi/2 ugao tj to znaci da je ugao 90 do 180 ili -180 do -90
				err_distance = -err_distance; // negativna je distanca jer je preko logiiiiiccc
				err_ang = ogranicenje_phi(err_ang + M_PI); //ugao merimo u odnosu na zadnji deo robota
			}

			if (fabsf(err_distance) < OGRANICENJE_UGLA_PRILIKOM_XY) {
				err_ang = 0;
			}

			ref_lin_v = PID_regulator(&PID_distanca, &err_distance, dt);
			ref_ang_w = PID_regulator(&PID_ang, &err_ang, dt);
		}
	}
}

void krivolinijsko(float dt) {
	stop(dt);
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
}
float get_distance(float ref_x, float ref_y) {
	float dx = get_x_pos_rob() - ref_x;
	float dy = get_y_pos_rob() - ref_y;
	return sqrtf(dx * dx + dy * dy);
}
float get_ugao_ka_cilju(float ref_x, float ref_y) {
	float dx = ref_x - get_x_pos_rob();
	float dy = ref_y - get_y_pos_rob();
	return atan2f(dy, dx);
}
float PID_regulator(PID_t *pid, float *error, float dt) {

	pid->P = pid->Kp * *error;
	pid->D = pid->Kd * D_regulator(pid, error, dt);
	pid->I = pid->Ki * anti_windup(pid, error, dt);

	pid->output = pid->P + pid->I + pid->D;

	if (pid->output > pid->max_output) {
		pid->output = pid->max_output;
	} else if (pid->output < -pid->max_output) {
		pid->output = -pid->max_output;
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

	if ((pid->I_new > pid->max_output && *error > 0) || (pid->I_new < -pid->max_output && *error < 0)) {
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
