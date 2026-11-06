/*
 * motorControl.c
 *
 *  Created on: Dec 23, 2025
 *      Author: Lea
 */

#include "main.h"

double e, u;
double P = 1.0;

double calculate_control(double ref, double y) {
	e = ref - y;
	u = P * e;
	return u;
}

