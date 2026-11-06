/*
 * signal.c
 *
 *  Created on: Dec 23, 2025
 *      Author: lazar
 */

#include "main.h"

void wrap180(volatile double *signal) {
	if (*signal > 180.0)
		*signal -= 360.0;
	if (*signal < -180.0)
		*signal += 360.0;
}

void wrap2Pi(volatile double *signal) {
	if (*signal > M_PI)
		*signal -= 2 * M_PI;
	if (*signal < -M_PI)
		*signal += 2 * M_PI;
}

double clamp(double signal, double min, double max) {
	if (signal > max)
		return max;
	if (signal < min)
		return min;
	return signal;
}

double correct_param(double param, double error, double eta, double min, double max)
{
    return clamp(param + eta * error, min, max);
}

unsigned char stacked(double time_limit, double v, double v_min, double freq, unsigned *cnt)
{
    if (fabs(v) < v_min * 0.5)
        (*cnt)++;
    else
        *cnt = 0;
    if (*cnt / freq >= time_limit)
        return 1;
    return 0;
}

double velocity_synthesis(double distance, double velocity, double acceleration, double J_MAX, double stopping_distance,
                          double v_max, double v_min, double dt, double v0, unsigned slowdown_status,
                          double v_slowed_max, double v_min_acc)
{
    if (dt <= 0.0)
        return 0.0;
    double abs_distance = fabs(distance);
    double abs_velocity = fabs(velocity);
    double abs_acceleration = fabs(acceleration);
    double abs_v0 = fabs(v0);
    double a_step = J_MAX * dt;
    double abs_v_ref = 0.0;
    double v_des = 0.0;

    switch (slowdown_status)
    {
    case 0:
        v_des = v_max;
        break;
    case 1:
        v_des = 0.0;
        return 0;
        break;
    case 2:
        v_des = v_slowed_max;
        break;
    }

    if (abs_distance < stopping_distance*1.01)
    {
        double x = abs_distance / stopping_distance;
        abs_v_ref = v_des * (35.0f * pow(x, 4) - 84.0f * pow(x, 5) + 70.0f * pow(x, 6) - 20.0f * pow(x, 7));
        abs_v_ref = clamp(abs_v_ref, v_min, v_max);
    }
    else
    {
        abs_v_ref = synthesis_v(abs_velocity, abs_acceleration, a_step, v_des, dt, abs_v0);
        abs_v_ref = clamp(abs_v_ref, v_min_acc, v_max);
    }
    return clamp(get_sign(distance) * abs_v_ref, -v_max, v_max);
}

double synthesis_v(double velocity, double acceleration, double a_step, double v_des, double dt, double v0)
{
    int8_t acc_sign = get_sign(v_des - v0);
    double v_ret;

    if (velocity * acc_sign > v_des * acc_sign)
        v_ret = v_des;
    else if (velocity * acc_sign < (v_des + v0) * 0.5 * acc_sign)
        v_ret = velocity + acc_sign * (acceleration + a_step) * dt;
    else if (a_step < acceleration * 1.1)
        v_ret = velocity + acc_sign * (acceleration - a_step) * dt;
    else
        v_ret = v_des;
    if (v_ret < v_des * 1.1 && v_ret > v_des * 0.9)
        v_ret = v_des;
    return v_ret;
}

double wrap(double signal, double min, double max)
{
    double temp = signal;
    wrap_ptr(&temp, min, max);
    return temp;
}

void wrap_ptr(double *signal, double min, double max)
{
    double diff = max - min;
    while (*signal > max)
        *signal -= diff;
    while (*signal < min)
        *signal += diff;
}

short get_sign(double num)
{
    if (num > 0)
        return 1;
    if (num < 0)
        return -1;
    return 0;
}

double scale_vel_ref(volatile double *ref_1, volatile double *ref_2, double limit)
{
    double factor;
    double abs_max_var = abs_max(*ref_1, *ref_2);
    if (abs_max_var > limit)
    {
        factor = limit / abs_max_var;
        *ref_1 *= factor;
        *ref_2 *= factor;
        return factor;
    }
    return 1.0;
}

double abs_max(double a, double b)
{
    if (fabs(a) > fabs(b))
        return fabs(a);
    return fabs(b);
}

double abs_min(double a, double b)
{
    if (fabs(a) < fabs(b))
        return fabs(a);
    return fabs(b);
}

unsigned long unsigned_min(unsigned long a, unsigned long b)
{
    if (a < b)
        return a;
    return b;
}

void vel_ramp_up_ptr(double *signal, double reference, double acc)
{
    if (fabs(reference) - fabs(*signal) > acc)
        *signal += get_sign(reference) * acc;
    else
        *signal = reference;
}

double vel_ramp_up(double signal, double reference, double acc)
{
    double edited_ref = signal;
    if (fabs(reference) - fabs(signal) > acc)
        edited_ref += get_sign(reference) * acc;
    else
        edited_ref = reference;
    return edited_ref;
}

double vel_s_curve_up_webots(double *vel, double prev_vel, double vel_ref, double jerk)
{
    double acc_approx = *vel - prev_vel;
    double acc_calc = vel_ref - *vel;
    double out = *vel;

    if (fabs(vel_ref) > fabs(*vel))
    {
        if (fabs(acc_calc) - fabs(acc_approx) > jerk)
            out = *vel + acc_approx + get_sign(vel_ref) * jerk;
        else
            out = vel_ref;
    }
    return out;
}

double vel_s_curve_up(double vel, double accel, double vel_ref, double jerk)
{
    double accel_des = vel_ref - vel;
    double edited_ref = vel_ref;

    if (fabs(vel_ref) > fabs(vel)) // ako ubrzava
    {
        if (fabs(accel_des) - fabs(accel) > jerk)
        {
            edited_ref = vel + accel + get_sign(vel_ref) * jerk;
        }
    }
    return edited_ref;
}

double min3(double a, double b, double c)
{
    double min = a;
    if (b < min)
        min = b;
    if (c < min)
        min = c;
    return min;
}

double snap_angle(double angle, double step)
{
    return roundf((angle + 2 * step) / step) * step - 2 * step;
}

double snap_ortho_deg(double phi)
{
    return roundf((phi + 180) / 90.0f) * 90.0f - 180;
}
