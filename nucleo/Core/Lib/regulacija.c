/*
 * regulacija.c
 *
 * Created on: Nov 3, 2026
 * Author: Lea
 */

#include "main.h"
#include "odometrija.h"
#include "regulacija.h"


float lin_v = 0;
float ang_w = 0;

float err_v = 0;
float err_w = 0;

float ref_lin_v = 0;
float ref_ang_w = 0;

float output_v = 0;
float output_w = 0;

PID_t PID_linearni = {
    .Kp = 1,
    .Ki = 1,
    .Kd = 1
};

PID_t PID_ugao = {
    .Kp = 1.5,
    .Ki = 1.5,
    .Kd = 1.5
};


void position_control_loop() {
	/*
	 * Ovde kasnije racunamo referentnu
	 * linearnu brzinu na osnovu pozicije.
	 */
}

void velocity_control_loop(float dt) {
	lin_v = get_linear_velocity();
	ang_w = get_angular_velocity();

	err_v = ref_lin_v - lin_v;
	err_w = ref_ang_w - ang_w;

	output_v = PID_regulator(&PID_linearni, &err_v, dt);
	output_w = PID_regulator(&PID_ugao, &err_w, dt);
}

float PID_regulator(PID_t *pid, float *error, float dt) {

	pid-> P = pid -> Kp * *error;
	pid-> D = pid -> Kd * D_regulator(pid, error, dt);
	pid -> I = pid ->Ki * anti_windup(pid, error, dt);

	pid->output = pid-> P + pid-> I + pid-> D;

	if (pid->output > 100) {
		pid->output = 100;
	} else if (pid->output < -100) {
		pid->output = -100;
	}

	return pid->output;
}

float D_regulator(PID_t *pid, float *error, float dt) {
	pid-> D = (*error - pid-> error_prev) / dt;
	pid-> error_prev = *error;
	return pid-> D;
}

float anti_windup(PID_t *pid, float *error, float dt)
{
    pid->integral_new = pid->integral + (*error) * dt;

    pid->I_new = pid->Ki * pid->integral_new;

    if ((pid->I_new > 100 && *error > 0) ||
        (pid->I_new < -100 && *error < 0))
    {
        return pid->integral;
    }

    pid->integral = pid->integral_new;

    return pid->integral;
}

void reset_PID(PID_t *pid, float *error){
	pid -> integral = 0;
	pid -> error_prev = 0;
	pid -> integral_new = 0;
	pid -> output = 0;
	pid->P = 0;
	pid->I = 0;
	pid->D = 0;
	pid -> I_new = 0;
	*error = 0;
}

