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

    float integral;
    float error_prev;
    float integral_new;

    float P;
    float I;
    float D;

    float output;
    float output_new;

} PID_t;



void position_control_loop(void);
void velocity_control_loop(float dt);
float PID_regulator(PID_t *pid, float *error, float dt);
float integral_calculation(PID_t *pid, float *error, float dt);
float D_regulator(PID_t *pid, float *error, float dt);
float anti_windup(PID_t *pid, float *error, float dt);

#endif

