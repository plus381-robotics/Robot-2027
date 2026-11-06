/*
 * lib.h
 *
 *  Created on: Aug 13, 2024
 *      Author: lazar
 */

#ifndef LIB_LIB_H_
#define LIB_LIB_H_

#include <stdint.h>
#include <math.h>
#include <stdlib.h>
#include <stdio.h>

#include "tim.h"
#include "gpio.h"
#include "usart.h"

typedef struct st_pid {
	float p;
	float i;
	float d;
	float lmt;
	float ctrl;
	float ctrl_p;
	float ctrl_pp;
	float err_p;
	float err_sum;
	float err_dif;
	float sum_lmt;

} pid;

typedef struct goal_struct {
	int8_t type;
	double x;
	double y;
	double phi;
	int8_t obstacle;
	int8_t direction;
	double v_max;
	double w_max;
	double distance_tolerance_percentage;
	double angle_tolerance_percentage;
	double start_coeff_v;
	double start_coeff_w;
	double stop_coeff_v;
	double stop_coeff_w;
	int8_t status; // -1 = success; -2 = canceled; -3 = interrupted; -4 = timed out
	double distance_remaininig;
	double angle_remaining;
} goal_type;

// pid.h
float
calc_pid(volatile pid *pid_ptr, float err);
float
calc_pid_2(volatile pid *pid_ptr, float ref, float val);
void
init_pid(volatile pid *pid_ptr, float p, float i, float d, float limit,
		float sum_limit);
void
reset_pid(volatile pid *pid_ptr);

// time.h
void
time_ISR();
void
time_start();
void
time_stop();

// encoder.h
int16_t
cnt_difference(TIM_HandleTypeDef *htim, volatile int16_t *cur);
void
enc_start(TIM_HandleTypeDef *htim);
void
enc_init();
double
enc_velocity(int16_t diff, double deltaT, uint16_t impulse_per_2Pi);

// pwm.h
void
pwm_set_dc(TIM_HandleTypeDef *htim, uint32_t channel, int16_t duty_cycle);
void
pwm_init();
void pwm_kill();
void
pwm_left(float vel);
void
pwm_right(float vel);
void
set_motor_l_dir(int8_t dir);
void
set_motor_r_dir(int8_t dir);
// odometry.h
void
odometry_init();
void
update_odom();
double
get_x();
double
get_y();
double
get_phi();
double
get_v();
double
get_w();

//signal.h
void
wrap180(volatile double *signal);
void
wrap2Pi(volatile double *signal);
double clamp(double signal, double min, double max);
double correct_param(double param, double error, double eta, double min,
		double max);
unsigned char stacked(double time_limit, double v, double v_min, double freq,
		unsigned *cnt);
double velocity_synthesis(double distance, double velocity, double acceleration,
		double J_MAX, double stopping_distance, double v_max, double v_min,
		double dt, double v0, unsigned slowdown_status, double v_slowed_max,
		double v_min_acc);
double synthesis_v(double velocity, double acceleration, double a_step,
		double v_des, double dt, double v0);
double wrap(double signal, double min, double max);
void wrap_ptr(double *signal, double min, double max);
short get_sign(double num);
double scale_vel_ref(volatile double *ref_1, volatile double *ref_2,
		double limit);
double abs_max(double a, double b);
double abs_min(double a, double b);
unsigned long unsigned_min(unsigned long a, unsigned long b);
void vel_ramp_up_ptr(double *signal, double reference, double acc);
double vel_ramp_up(double signal, double reference, double acc);
double vel_s_curve_up_webots(double *vel, double prev_vel, double vel_ref,
		double jerk);
double vel_s_curve_up(double vel, double accel, double vel_ref, double jerk);
double min3(double a, double b, double c);
double snap_angle(double angle, double step);
double snap_ortho_deg(double phi);

//motorControl.h
double calculate_control(double ref, double y);

// comm.h
void
update_tx_buffer();
void
comm_init();
void process_rx_buffer();
goal_type* get_rx_goal();

// control.h
void control_loop();
void move_init();
double get_v_r();
double get_v_l();
void move_goal(goal_type *goal);
uint8_t get_set_goal_reset();
void reset_goal(goal_type *goal_ptr);

#endif /* LIB_LIB_H_ */
