/*
 * regulacija.h
 *
 *  Created on: Nov 3, 2026
 *      Author: Lea
 */


#ifndef INC_REGULACIJA_H_
#define INC_REGULACIJA_H_

typedef struct
{
    float Kp;
    float Ki;
    float Kd;
    float max_output;

    float integral;
    float error_prev;
    float integral_new;

    float P;
    float I;
    float D;
    float I_new;

    float output;

} PID_t;

float get_distance(float ref_x, float ref_y);
float get_ugao_ka_cilju(float ref_x, float ref_y);

void stop(float dt);

void rotacija(float dt);
void move_to_xy(float dt);
uint8_t rotacija_to_xy(float dt);

void krivolinijsko(float dt);

void position_control_loop(float dt);
void velocity_control_loop(float dt);

float PID_regulator(PID_t *pid, float *error, float dt);
float D_regulator(PID_t *pid, float *error, float dt);
float anti_windup(PID_t *pid, float *error, float dt);

void reset_PID(PID_t *pid, float *error);
void reset_PIDs();

#endif

