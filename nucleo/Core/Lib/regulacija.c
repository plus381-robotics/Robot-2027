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
float ang_w = 0;

float err_v = 0;
float err_v_prev = 0;
float err_w = 0;
float err_w_prev = 0;

float ref_lin_v = 0;
float ref_ang_w = 0;


float integral_v = 0;
float integral_new = 0;


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

float integral_calculation(PID_t *pid, float *error, float dt) {
	return pid -> integral + *error * dt;
}

float anti_windup(PID_t *pid, float *error, float dt)
{
	pid -> integral_new = integral_calculation(pid, error, dt);

	pid -> output_new = pid-> P + pid->Ki * pid->integral_new + pid-> D;

    if ((pid->output_new > 100 && *error > 0) ||
        (pid->output_new < -100 && *error < 0))
    {
        return pid->integral;
    }

    pid->integral = pid->integral_new;

    return pid->integral;
}

