/*
 * odometrija.h
 *
 *  Created on: Oct 27, 2026
 *      Author: Lea
 */

#ifndef INC_ODOMETRIJA_H_
#define INC_ODOMETRIJA_H_

void update_odometrija(float dt);

float error_left(float ideal_distance);
float error_right(float ideal_distance);
float error_D(float ideal_angle);

float new_d_left(float ideal_distance);
float new_d_right(float ideal_distance);
float new_D(float ideal_angle);

float get_s_left();
float get_s_right();
float get_phi1();

float get_x_pos_rob();
float get_y_pos_rob();
float get_phi_pos_rob();

float get_linear_velocity();
float get_angular_velocity();

void set_pose(float x_m, float y_m, float phi_rad); // dodato za ESP (SET_POSE)

#endif /* INC_ODOMETRIJA_H_ */
