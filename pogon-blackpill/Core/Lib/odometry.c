/*
 * odometry.c
 *
 *  Created on: Dec 23, 2025
 *      Author: lazar
 */

#include "main.h"

double L_wheel;
double L_wheel_recip;
double d_odom_left;
double d_odom_right;

double mid_angle;
int16_t v_l_diff = 0;
int16_t v_r_diff = 0;

volatile int16_t enc_l_sum;		// [inc]
volatile int16_t enc_r_sum;		// [inc]

volatile double v_right, v_left;
volatile double v_base, w_base;
volatile double x_base = 0.0, y_base = 0.0, phi_base = 0.0;

void
odometry_init ()
{
	L_wheel = 0.2993;																	// [m], rastojanje izmedju odometrijskih tockova
	L_wheel_recip = 1 / L_wheel;										// [1/m]
	d_odom_left = 0.07509;															// [m]
	d_odom_right = 0.07528;															// [m]
	enc_r_sum = 0;
	enc_l_sum = 0;
}

void
update_odom ()
{
	v_r_diff = cnt_difference (&htim5, &enc_r_sum);			// [inc/ms]
	v_l_diff = cnt_difference (&htim3, &enc_l_sum);
	// TODO: mora da se koriste i d
	v_right = -enc_velocity (v_r_diff, 0.001, 8192) * d_odom_right;			// rad/s, a treba da budu m/s
	v_left = enc_velocity (v_l_diff, 0.001, 8192) * d_odom_left;

	v_base = (v_right + v_left) * 0.5;									// [m/s]
	w_base = (v_right - v_left) * L_wheel_recip;				// [rad/s]
	mid_angle = (phi_base + w_base * 0.005);						// [rad + 0.5*rad/s * 0.001s = rad]

	x_base += v_base * cos (mid_angle) * 0.001;									// [mm/ms * 1ms = mm]
	y_base += v_base * sin (mid_angle) * 0.001;
	phi_base += w_base * 0.001;													// [0.001s * rad/s = rad]

	wrap2Pi (&phi_base);
}

double
get_x ()
{
	return x_base;
}

double
get_y ()
{
	return y_base;
}

double
get_phi ()
{
	return phi_base;
}

double
get_v ()
{
	return v_base;
}

double
get_w ()
{
	return w_base;
}
