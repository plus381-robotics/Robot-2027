/*
 * comm_port.c
 *
 * BlackPill deo protokola sa ESP-om: comm.c (zajednički sa nucleo/) zove ove funkcije.
 * Vidi comm_port.h i comm.h.
 *
 * Most protokol -> postojeća regulacija (control.c): cilj (goal) živi ovde, glavna petlja
 * zove comm_port_update(), pa move_goal(comm_port_goal()).
 *   GOTO   -> goal type 1 (REVERSE -> direction -1, max_speed -> v_max),
 *             posle dolaska rotacija na theta, osim ako je NO_THETA
 *   ROTATE -> goal type -1
 *   MOVE   -> tačka dist ispred (ili iza) robota, goal type 1
 *   STOP, pad heartbeat-a, kraj meča -> type 0
 * Status regulacije -> odgovor: -1 DONE, -4 i -3 FAIL BLOCKED, -5 FAIL TIMEOUT.
 * Nova komanda pre završetka: comm.c sam šalje FAIL PREEMPTED za staru.
 *
 * Hook-ovi samo upisuju zahtev (comm_hook_stop se zove i iz prekida pri padu heartbeat-a),
 * a goal menja isključivo comm_port_update() iz glavne petlje.
 */
#include "main.h"
#include "comm.h"
#include "comm_port.h"

#define MATCH_MS        100000
#define V_DEFAULT       1.0      /* m/s kad je max_speed = 0 */
#define W_GOTO          6.0      /* rad/s, kao lazarov xy_goal u main.c */
#define W_ROTATE        3.14     /* rad/s, kao lazarov rot_goal u main.c */
#define D_ARRIVED       0.02     /* m; bliže od ovoga se ne vozi (go_to_xy bi se okretao ka atan2(0, 0)) */
#define ROT_TIMEOUT_MS  5000     /* rotate() nema detekciju zaglavljivanja */
#define V_NEAR          0.2      /* m/s: najveća brzina u prilazu elementu (GOTOFLAGS_NEAR, v5) */

enum { IDLE, DRIVE, TURN };

static goal_type goal;                 /* type 0 = stoj */
static uint8_t phase = IDLE;
static uint32_t phase_t0;
static uint8_t has_final;              /* posle DRIVE okreni se na final_phi */
static double final_phi;

static volatile uint8_t stop_request, stop_reason;
static struct {
	int8_t type;                       /* 1 = vožnja na x,y, -1 = rotacija */
	double x, y, phi, v;
	int8_t dir;
	uint8_t final;
	uint8_t near;                      /* v5: prilaz elementu (IR ne zaustavlja, sporo) */
} req;
static uint8_t near;                   /* kretanje u toku je prilaz (GOTOFLAGS_NEAR) */
static volatile uint8_t ir_bits;       /* poslednje stanje IR-a (comm_port_set_obstacle) */
static volatile uint8_t req_pending;

static volatile uint8_t boot_request;
static uint32_t boot_t0;
#define BOOT_DELAY_MS   30       /* da ACK stigne da ode preko UART-a */
#define SYSMEM          0x1FFF0000UL

static volatile uint8_t match_running, match_over;
static uint32_t match_start_ms;

/* ---------------- comm_port.h ---------------- */

uint32_t comm_port_time_ms(void) {
	return HAL_GetTick();
}

static int16_t clamp16(double v) {
	if (v > 32767.0) return 32767;
	if (v < -32768.0) return -32768;
	return (int16_t) v;
}

void comm_port_fill_status(msg_status_t *s) {
	double phi = get_phi();            /* wrap2Pi() drži -pi..pi, ali za svaki slučaj */
	if (phi > M_PI)
		phi -= 2.0 * M_PI;
	s->x = clamp16(get_x() * 1000.0);
	s->y = clamp16(get_y() * 1000.0);
	s->theta = clamp16(phi * 18000.0 / M_PI);
	s->v = clamp16(get_v() * 1000.0);
	s->w = clamp16(get_w() * 1000.0);  /* rad/s -> mrad/s (v4) */
	if (match_over) {
		s->state |= STATE_MATCH_OVER;
		s->match_ms = MATCH_MS;
	} else if (match_running) {
		s->state |= STATE_MATCH_RUNNING;
		s->match_ms = HAL_GetTick() - match_start_ms;
	}
}

uint8_t comm_port_set_pose(int16_t x_mm, int16_t y_mm, int16_t theta_cdeg) {
	if (phase != IDLE || req_pending)
		return REASON_INVALID;         /* cilj je zadat u starim koordinatama */
	set_pose(x_mm / 1000.0, y_mm / 1000.0, theta_cdeg * M_PI / 18000.0);
	return 0;
}

void comm_port_match_start(void) {
	if (!match_running) {
		match_start_ms = HAL_GetTick();
		match_running = 1;
	}
}

uint8_t comm_port_resume(int16_t x_mm, int16_t y_mm, int16_t theta_cdeg, uint32_t elapsed_ms) {
	uint8_t r = comm_port_set_pose(x_mm, y_mm, theta_cdeg);
	if (r)
		return r;
	match_start_ms = HAL_GetTick() - elapsed_ms;   /* sat meča nastavlja od elapsed_ms */
	match_running = 1;                             /* kraj (100 s) proverava comm_port_update() */
	return 0;
}

/* ---------------- hook-ovi iz comm.h ---------------- */

static double speed(uint16_t max_speed_mm_s) {
	return max_speed_mm_s ? max_speed_mm_s / 1000.0 : V_DEFAULT;
}

uint8_t comm_hook_goto(int16_t x_mm, int16_t y_mm, int16_t theta_cdeg, uint8_t flags, uint16_t max_speed) {
	if (match_over)
		return REASON_MATCH_OVER;
	req.type = 1;
	req.x = x_mm / 1000.0;
	req.y = y_mm / 1000.0;
	req.phi = theta_cdeg * M_PI / 18000.0;
	req.dir = (flags & GOTOFLAGS_REVERSE) ? -1 : 1;
	req.v = speed(max_speed);
	req.final = !(flags & GOTOFLAGS_NO_THETA);
	req.near = (flags & GOTOFLAGS_NEAR) ? 1 : 0;
	req_pending = 1;
	return 0;
}

uint8_t comm_hook_rotate(int16_t theta_cdeg) {
	if (match_over)
		return REASON_MATCH_OVER;
	req.type = -1;
	req.phi = theta_cdeg * M_PI / 18000.0;
	req.final = 0;
	req.near = 0;
	req_pending = 1;
	return 0;
}

uint8_t comm_hook_move(int16_t dist_mm, uint16_t max_speed, uint8_t flags) {
	if (match_over)
		return REASON_MATCH_OVER;
	if (dist_mm == 0)
		return REASON_INVALID;
	double d = dist_mm / 1000.0, phi = get_phi();
	req.type = 1;
	req.x = get_x() + d * cos(phi);    /* d < 0: tačka iza robota, vozi unazad */
	req.y = get_y() + d * sin(phi);
	req.dir = d > 0 ? 1 : -1;
	req.v = speed(max_speed);
	req.final = 0;
	req.near = (flags & GOTOFLAGS_NEAR) ? 1 : 0;
	req_pending = 1;
	return 0;
}

uint8_t comm_hook_bootloader(void) {
	boot_request = 1;
	boot_t0 = HAL_GetTick();
	comm_hook_stop();
	return 0;
}

/* Ulazak u bootloader preko reseta: oznaka u backup registru (preživljava reset), pa restart;
 * main() je vidi pre bilo kakve inicijalizacije i skače u bootloader iz čistog stanja (comm_port_boot_check). */
#define BOOT_MAGIC 0xB007B007UL

static void jump_to_bootloader(void) {
	pwm_kill();
	__HAL_RCC_PWR_CLK_ENABLE();
	PWR->CR |= PWR_CR_DBP;
	RTC->BKP0R = BOOT_MAGIC;
	NVIC_SystemReset();
}

void comm_port_boot_check(void) {
	__HAL_RCC_PWR_CLK_ENABLE();
	if (RTC->BKP0R != BOOT_MAGIC)
		return;
	PWR->CR |= PWR_CR_DBP;
	RTC->BKP0R = 0;
	__HAL_RCC_SYSCFG_CLK_ENABLE();
	SYSCFG->MEMRMP = SYSCFG_MEMRMP_MEM_MODE_0;   /* sistemska memorija na adresi 0 */
	__set_MSP(*(volatile uint32_t*) SYSMEM);
	((void (*)(void)) *(volatile uint32_t*) (SYSMEM + 4))();
}

void comm_hook_stop(void) {
	req_pending = 0;
	stop_reason = comm_stop_reason();  /* STOPPED, ili LINK kad je pukla veza (v4) */
	stop_request = 1;
}

/* ---------------- most ka regulaciji ---------------- */

static void finish(uint8_t reason) {
	comm_motion_finished(reason);      /* 0 = DONE; ako ESP-ova komanda nije aktivna, ne šalje ništa */
	reset_goal(&goal);
	phase = IDLE;
	near = 0;
}

/* IR (prepreka): bitovi 1 = napred, 2 = nazad, kao goal.obstacle u control.c. Ovo zove kod koji čita IR
 * senzore (još ne postoji na BlackPill-u); comm_port_update() ih prosleđuje regulaciji, osim u prilazu
 * elementu (GOTOFLAGS_NEAR, v5), kad IR ne zaustavlja robota. */
void comm_port_set_obstacle(uint8_t bits) {
	ir_bits = bits;
}

static void start_turn(double phi) {
	reset_goal(&goal);                 /* i reset_movement(): movement_state_ = 0, može nov cilj */
	goal.phi = phi;
	goal.w_max = W_ROTATE;
	goal.type = -1;
	phase = TURN;
	phase_t0 = HAL_GetTick();
}

static void start(void) {
	has_final = req.final;
	final_phi = req.phi;
	near = req.near;
	if (near && req.v > V_NEAR)
		req.v = V_NEAR;                /* prilaz: sporo, jer IR ne zaustavlja */
	if (req.type == -1) {
		start_turn(req.phi);
		return;
	}
	double dx = req.x - get_x(), dy = req.y - get_y();
	if (sqrt(dx * dx + dy * dy) < D_ARRIVED) {   /* već je tu */
		if (has_final)
			start_turn(final_phi);
		else
			finish(0);
		return;
	}
	reset_goal(&goal);
	goal.x = req.x;
	goal.y = req.y;
	goal.direction = req.dir;
	goal.v_max = req.v;
	goal.w_max = W_GOTO;
	goal.type = 1;
	phase = DRIVE;
	phase_t0 = HAL_GetTick();
}

goal_type* comm_port_goal(void) {
	return &goal;
}

void comm_port_update(void) {
	uint32_t now = HAL_GetTick();
	if (match_running && !match_over && now - match_start_ms >= MATCH_MS) {
		match_over = 1;
		req_pending = 0;
		stop_reason = REASON_MATCH_OVER;
		stop_request = 1;
	}
	if (stop_request) {
		stop_request = 0;
		finish(stop_reason);
	}
	if (boot_request && now - boot_t0 >= BOOT_DELAY_MS)
		jump_to_bootloader();
	if (req_pending) {
		req_pending = 0;
		start();
	}
	goal.obstacle = near ? 0 : ir_bits;  /* v5: u prilazu elementu IR ne zaustavlja robota */
	if (phase == IDLE)
		return;
	/* goal.status je movement_state_ iz poslednjeg move_goal() */
	switch (goal.status) {
	case -1:
		if (phase == DRIVE && has_final)
			start_turn(final_phi);
		else
			finish(0);
		break;
	case -3:                           /* zaglavljen (stacked) */
	case -4:                           /* prepreka */
		finish(REASON_BLOCKED);
		break;
	case -5:                           /* stao, ali nije stigao */
		finish(REASON_TIMEOUT);
		break;
	default:
		if (phase == TURN && now - phase_t0 > ROT_TIMEOUT_MS)
			finish(REASON_TIMEOUT);
		break;
	}
}
