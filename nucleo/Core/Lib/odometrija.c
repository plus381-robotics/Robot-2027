/*
 * odometrija.c
 *
 *  Created on: Oct 27, 2026
 *      Author: Lea
 */
#include "main.h"
#include "tim.h"
#include "encoder.h"

float D = 0.3; //razmak izmedju tockova
float d_left = 0.07; //precnik levog
float d_right = 0.07; //precnik desnog

volatile float v_left;
volatile float v_right;

volatile float linear_velocity = 1;
volatile float angular_velocity = 1;

volatile float x = 0; //trenutna pozicija x, y, phi
volatile float y = 0;
volatile float phi = 0;
volatile float phi1 = 0;

volatile float s_left = 0; //od pocetka jednog kretanja ukupan predjeni put (za sada samo za linearno kretanje)
volatile float s_right = 0;
volatile float w_left;
volatile float w_right;

void update_odometrija(float dt) {
	//moracu da imam flag kad krenem kretnje da radim da vidim da li se radnja zavrsila neka ako jeste s cu postavljati na 0
	w_left = encoder_speed_left(dt);
	w_right = encoder_speed_right(dt);
	v_left = w_left * (d_left / 2);
	v_right = w_right * (d_right / 2);

	linear_velocity = (v_left + v_right) / 2;
	angular_velocity = (v_right - v_left) / D;

	x += linear_velocity * cos(phi + (angular_velocity * dt) / 2) * dt;
	y += linear_velocity * sin(phi + (angular_velocity * dt) / 2) * dt;

	phi1 += angular_velocity * dt; //u bilo kom opsegu vraca
	phi = ogranicenje_phi(phi1);

	s_left += fabs(v_left * dt); //sabira predjeni put
	s_right += fabs(v_right * dt);
}

float ogranicenje_phi(float phi) {
	if (phi < -M_PI)
		phi = +2 * M_PI;

	else if (phi > M_PI)
		phi = -2 * M_PI;
	return phi;
}

float get_s_left() {
	return s_left;
}
float get_s_right() {
	return s_right;
}
float get_phi1() {
	return phi1;
}

//lakse gledanje sta se desava
float error_left(float ideal_distance) //idealna distanca je ovo sto je zadato realna je ono sto je presao, dok funkcija sluzi za racunanje greske zarad lakseg podesavanje parametra
{
	return ideal_distance - get_s_left(); //vraca u svakom momentu gresku
}
float error_right(float ideal_distance) //idealna distanca je ovo sto je zadato realna je ono sto je presao, dok funkcija sluzi za racunanje greske zarad lakseg podesavanje parametra
{
	return ideal_distance - get_s_right(); //vraca u svakom momentu gresku
}
float error_D(float ideal_angle) {
	return ideal_angle - get_phi1();
}

//da lakse racunam a ne mucim se
float new_d_left(float ideal_distance) {
	return d_left * (ideal_distance / get_s_left());
}

float new_d_right(float ideal_distance) {
	return d_right * (ideal_distance / get_s_right());
}
float new_D(float ideal_angle) {
	return D * (get_phi1() / ideal_angle);
}

// Dodato za protokol sa ESP-om (komanda SET_POSE): postavlja trenutnu poziciju robota.
// x, y u metrima, phi u radijanima. Poziva se iz glavne petlje, zato se prekid nakratko gasi.


//PETRE DA LI SI SIG DA OCES OVO OVDE? Ovo ti nema veze sa pozicijama
void set_pose(float x_m, float y_m, float phi_rad) {
	__disable_irq();
	x = x_m;
	y = y_m;
	phi = phi_rad;
	phi1 = phi_rad;
	__enable_irq();
}

//potrebne promenljive koje ce mi dalje trebati da baratam sa njima u kodu
float get_x_pos_rob() {
	return x;
}
float get_y_pos_rob() {
	return y;
}
float get_phi_pos_rob() {
	return phi;
}

float get_linear_velocity() {
	return linear_velocity;
}
float get_angular_velocity() {
	return angular_velocity;
}

