/*
 * pid.c
 *
 *  Created on: Mar 25, 2026
 *      Author: lazar
 */

#include "main.h"

float calc_pid(volatile pid *pid_ptr, float err) {
	pid_ptr->err_sum += err;
	pid_ptr->err_sum = clamp(pid_ptr->err_sum, -pid_ptr->sum_lmt, pid_ptr->sum_lmt);
	pid_ptr->ctrl = pid_ptr->p * err + pid_ptr->i * pid_ptr->err_sum
			+ pid_ptr->d * pid_ptr->err_dif;
	pid_ptr->ctrl = clamp(pid_ptr->ctrl, -pid_ptr->lmt, pid_ptr->lmt);
	pid_ptr->err_dif = err - pid_ptr->err_p;
	pid_ptr->err_p = err;
	return pid_ptr->ctrl;
}

float calc_pid_2(volatile pid *pid_ptr, float ref, float val) {
	return calc_pid(pid_ptr, ref - val);
}

void init_pid(volatile pid *pid_ptr, float p, float i, float d, float limit,
		float sum_limit) {
	pid_ptr->p = p;
	pid_ptr->i = i;
	pid_ptr->d = d;
	pid_ptr->lmt = limit;
	pid_ptr->sum_lmt = sum_limit;
	pid_ptr->ctrl = 0;
	pid_ptr->ctrl_p = 0;
	pid_ptr->ctrl_pp = 0;
	pid_ptr->err_p = 0;
	pid_ptr->err_sum = 0;
	pid_ptr->err_dif = 0;
}

void reset_pid(volatile pid *pid_ptr) {
	pid_ptr->ctrl = 0;
	pid_ptr->ctrl_p = 0;
	pid_ptr->ctrl_pp = 0;
	pid_ptr->err_p = 0;
	pid_ptr->err_sum = 0;
	pid_ptr->err_dif = 0;
}
