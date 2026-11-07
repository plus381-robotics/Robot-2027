# Regulacija kretanja: prepis BlackPill control.c + signal.c (Lazar) u Python, korak po korak, 1 kHz.
# Namerno blizu originala (ista imena, isti redosled), da se izmene u C kodu lako prenesu ovde.
# Parametri dolaze iz profila ([control]); ništa nije "zakucano" osim onoga što je i u C-u.
#
# Ulaz: odometrija (x, y, phi, v, w) i cilj (Goal). Izlaz: v_ref, w_ref -> referenca brzina točkova
# (v_right, v_left, skalirano na MOTOR_V_MAX), što model robota (plant.py) prati.
# Brzinski PID (pid.c) se ne prepisuje: njegov efekat (kašnjenje, zasićenje) je u plant.py.
import math

DT = 0.001


def clamp(s, lo, hi):                  # signal.c: prvo max, pa min (redosled je bitan)
    if s > hi:
        return hi
    if s < lo:
        return lo
    return s


def wrap(s, lo, hi):
    d = hi - lo
    while s > hi:
        s -= d
    while s < lo:
        s += d
    return s


def sign(v):
    return 1 if v > 0 else (-1 if v < 0 else 0)


def synthesis_v(velocity, acceleration, a_step, v_des, dt, v0):
    acc_sign = sign(v_des - v0)
    if velocity * acc_sign > v_des * acc_sign:
        v = v_des
    elif velocity * acc_sign < (v_des + v0) * 0.5 * acc_sign:
        v = velocity + acc_sign * (acceleration + a_step) * dt
    elif a_step < acceleration * 1.1:
        v = velocity + acc_sign * (acceleration - a_step) * dt
    else:
        v = v_des
    if v_des * 0.9 < v < v_des * 1.1:
        v = v_des
    return v


def velocity_synthesis(distance, velocity, acceleration, j_max, stopping_distance, v_max, v_min, dt,
                       v0, slowdown_status, v_slowed_max, v_min_acc):
    a_dist, a_vel, a_acc = abs(distance), abs(velocity), abs(acceleration)
    a_step = j_max * dt
    if slowdown_status == 1:
        return 0.0
    v_des = v_slowed_max if slowdown_status == 2 else v_max
    if a_dist < stopping_distance * 1.01:
        x = a_dist / stopping_distance
        r = v_des * (35.0 * x ** 4 - 84.0 * x ** 5 + 70.0 * x ** 6 - 20.0 * x ** 7)
        r = clamp(r, v_min, v_max)
    else:
        r = synthesis_v(a_vel, a_acc, a_step, v_des, dt, abs(v0))
        r = clamp(r, v_min_acc, v_max)       # kao u C-u: V_MIN_ACC >= v_max -> odmah v_max
    return clamp(sign(distance) * r, -v_max, v_max)


class Goal:
    """goal_type iz main.h."""

    def __init__(self):
        self.type = 0
        self.x = self.y = self.phi = 0.0
        self.direction = 0
        self.v_max = self.w_max = 0.0
        self.distance_tolerance_percentage = self.angle_tolerance_percentage = 1.0
        self.start_coeff_v = self.start_coeff_w = self.stop_coeff_v = self.stop_coeff_w = 1.0
        self.status = 0
        self.obstacle = 0


class Control:
    def __init__(self, c, motor_v_max, wheel_track):
        # parametri (move_init)
        self.V_MIN, self.V_MAX = c["V_MIN"], c["V_MAX"]
        self.V_MIN_ACC = 1.5 if "V_MIN_ACC" not in c else c["V_MIN_ACC"]
        self.V_MIN_STACKED = c["V_MIN_STACKED"]
        self.W_MIN, self.W_MAX = c["W_MIN"], c["W_MAX"]
        self.W_MIN_ACC = c.get("W_MIN_ACC", 12.57)
        self.V_SLOWED_MAX = c["V_SLOWED_MAX"]
        self.MOTOR_V_MAX = motor_v_max
        self.L = wheel_track
        self.P_w = c["P_W"]
        self.J_MAX, self.J_MAX_STOP = c["J_MAX"], c["J_MAX_STOP"]
        self.J_ROT_MAX, self.J_ROT_MAX_STOP = c["J_ROT_MAX"], c["J_ROT_MAX_STOP"]
        self.D_TOL, self.D_PROJ_TOL = c["D_TOL"], c["D_PROJ_TOL"]
        self.D_LONG_TOL, self.D_SHORT_TOL = c["D_LONG_TOL"], c["D_SHORT_TOL"]
        self.PHI_TOL = c["PHI_TOL"]
        self.STACKED_TIME = c["STACKED_TIME"]
        self.dt = DT
        # stanje
        self.movement_state = 0
        self.reg_type = 0
        self.reg_phase = 0
        self.direction = 1
        self.x_ref = self.y_ref = self.phi_ref = 0.0
        self.v_ref = self.w_ref = 0.0
        self.v_right = self.v_left = 0.0
        self.prev_v = self.prev_w = 0.0
        self.a = self.alpha = 0.0
        self.obstacle = 0
        self.obst_f = self.obst_b = 0
        self.obst_in_loop = 0
        self.stacked_cnt = 0
        self.distance = self.distance_proj = 0.0
        self.phi_error = 0.0
        self.base = (0.0, 0.0, 0.0, 0.0, 0.0)
        self._reset_tmp()
        self.starting_coeff_v = self.stopping_coeff_v = self.starting_coeff_w = self.stopping_coeff_w = 1.0
        self.d_tol_perc = self.phi_tol_perc = 1.0
        self.stopping_distance = self.starting_distance = 0.0
        self.stopping_angle = self.starting_angle = 0.0

    def _reset_tmp(self):
        self.v_max_temp, self.w_max_temp = self.V_MAX, self.W_MAX
        self.j_max_temp, self.j_rot_max_temp = self.J_MAX, self.J_ROT_MAX

    # ---------------- move_goal / reset ----------------

    def reset_movement(self):
        x, y, phi, _, _ = self.base
        self.obst_in_loop = 0
        self.movement_state = 0
        self.stacked_cnt = 0
        self.x_ref, self.y_ref, self.phi_ref = x, y, phi
        self.direction = 1
        self._reset_tmp()
        self.starting_coeff_v = self.stopping_coeff_v = self.starting_coeff_w = self.stopping_coeff_w = 1.0
        self.d_tol_perc = self.phi_tol_perc = 1.0
        self.reg_type = 0
        self.reg_phase = 0

    def reset_goal(self, g, odom):
        self.reset_movement()
        g.type = 0
        g.x, g.y, g.phi = odom[0], odom[1], odom[2]
        g.direction = 0
        g.v_max, g.w_max = self.V_MAX, self.V_MIN
        g.distance_tolerance_percentage = g.angle_tolerance_percentage = 1.0
        g.start_coeff_v = g.start_coeff_w = g.stop_coeff_v = g.stop_coeff_w = 1.0
        g.status = 0

    def move_goal(self, g, odom):
        self.obstacle = g.obstacle
        g.status = self.movement_state
        if g.type == 0:
            self.reset_movement()
        elif g.status == 0:
            g.status = 1
            self.base = odom
            self.v_max_temp = clamp(g.v_max, self.V_MIN, self.V_MAX)
            self.w_max_temp = clamp(g.w_max, self.W_MIN, self.W_MAX)
            self.starting_coeff_v = clamp(g.start_coeff_v, 1.0, 10.0)
            self.stopping_coeff_v = clamp(g.stop_coeff_v, 1.0, 10.0)
            self.starting_coeff_w = clamp(g.start_coeff_w, 1.0, 10.0)
            self.stopping_coeff_w = clamp(g.stop_coeff_w, 1.0, 10.0)
            self.d_tol_perc = clamp(g.distance_tolerance_percentage, 1.0, 10.0)
            self.phi_tol_perc = clamp(g.angle_tolerance_percentage, 1.0, 10.0)
            self.direction = g.direction
            if g.type == -1:
                self.x_ref, self.y_ref = odom[0], odom[1]
                self.phi_ref = g.phi
                self.reg_type = -1
            elif g.type == 1:
                self.x_ref, self.y_ref = g.x, g.y
                self.phi_ref = 0.0
                self.reg_type = 1

    # ---------------- control_loop ----------------

    def loop(self, odom):
        """Jedan korak (1 ms). odom = (x, y, phi, v, w). Vraća (v_right, v_left) reference točkova."""
        self.base = odom
        _, _, _, v_base, w_base = odom
        self.obst_f = self.obstacle & 1
        self.obst_b = (self.obstacle >> 1) & 1
        if self.reg_type == -1:
            self._rotate()
        elif self.reg_type == 0:
            self.v_ref = self.w_ref = 0.0
            self.reset_movement()
        elif self.reg_type == 1:
            self._go_to_xy()
        if (self.obst_f and self.direction == 1) or (self.obst_b and self.direction == -1):
            self.v_ref = 0.0
        # velocity_loop: PID je u modelu; ovde samo referenca točkova i skaliranje (scale_vel_ref)
        vr = self.v_ref + self.w_ref * self.L * 0.5
        vl = self.v_ref - self.w_ref * self.L * 0.5
        m = max(abs(vr), abs(vl))
        if m > self.MOTOR_V_MAX:
            vr *= self.MOTOR_V_MAX / m
            vl *= self.MOTOR_V_MAX / m
        self.v_right, self.v_left = vr, vl
        self.a = (v_base - self.prev_v) / self.dt
        self.alpha = (w_base - self.prev_w) / self.dt
        self.prev_v, self.prev_w = v_base, w_base
        return vr, vl

    def _angles(self, err):
        self.starting_angle = 5 * self.w_max_temp ** 1.5 / 3 / math.sqrt(self.j_rot_max_temp) * self.starting_coeff_w
        self.stopping_angle = 5 * self.w_max_temp ** 1.5 / 3 / math.sqrt(self.J_ROT_MAX_STOP) * self.stopping_coeff_w
        slowing = clamp((abs(err) / (self.starting_angle + self.stopping_angle)) ** (2.0 / 3.0), 0.0, 1.0)
        w_min_acc = clamp(slowing, 0.6, 1.0) * self.W_MIN_ACC
        self.w_max_temp *= slowing
        self.stopping_angle = 5 * self.w_max_temp ** 1.5 / 3 / math.sqrt(self.J_ROT_MAX_STOP) * self.stopping_coeff_w
        return w_min_acc

    def _rotate(self):
        x, y, phi, v_base, w_base = self.base
        self.phi_error = wrap(self.phi_ref - phi, -math.pi, math.pi)
        if abs(self.phi_error) < self.PHI_TOL * self.phi_tol_perc and abs(w_base) < self.W_MIN * 2.0:
            self.movement_state = -1
        w_min_acc = self.W_MIN_ACC             # C: lokalna, smanjena samo u prvom pozivu
        if self.movement_state == 0:
            w_min_acc = self._angles(self.phi_error)
            self.movement_state = 1
        self.v_ref = 0.0
        self.w_ref = velocity_synthesis(self.phi_error, w_base, self.alpha, self.j_rot_max_temp,
                                        self.stopping_angle, self.w_max_temp, self.W_MIN, self.dt, 0.0, 0, 0.0,
                                        w_min_acc)

    def _go_to_xy(self):
        x, y, phi, v_base, w_base = self.base
        if self.movement_state == 0:
            self.movement_state = 1
        w_min_acc = self.W_MIN_ACC
        xe, ye = self.x_ref - x, self.y_ref - y
        self.phi_error = wrap(math.atan2(ye, xe) - phi + (self.direction - 1) * math.pi * 0.5, -math.pi, math.pi)
        rp = self.reg_phase
        if rp == 0:
            self.v_ref = self.w_ref = 0.0
            self._angles(self.phi_error)
            self.reg_phase = 1
        elif rp == 1:
            if abs(self.phi_error) < self.PHI_TOL * 3.0 and abs(w_base) < self.W_MIN * 2.0:
                self.reg_phase = 2
                self.w_max_temp = self.W_MAX
            self.v_ref = 0.0
            # C: W_MIN_ACC_temp_ je ovde uvek W_MIN_ACC (lokalna promenljiva iz faze 0 se ne pamti)
            self.w_ref = velocity_synthesis(self.phi_error, w_base, self.alpha, self.j_rot_max_temp,
                                            self.stopping_angle, self.w_max_temp, self.W_MIN, self.dt, 0.0, 0, 0.0,
                                            w_min_acc)
        elif rp == 2:
            self.v_ref = self.w_ref = 0.0
            self.distance = math.hypot(xe, ye)
            self.distance_proj = self.distance * math.cos(self.phi_error)
            self.starting_distance = 5 * self.v_max_temp ** 1.5 / 3 / math.sqrt(self.j_max_temp) * self.starting_coeff_v
            self.stopping_distance = 5 * self.v_max_temp ** 1.5 / 3 / math.sqrt(self.J_MAX_STOP) * self.stopping_coeff_v
            slowing = clamp((self.distance / (self.starting_distance + self.stopping_distance)) ** (2.0 / 3.0), 0.0, 1.0)
            self.v_max_temp *= slowing
            self.stopping_distance = 5 * self.v_max_temp ** 1.5 / 3 / math.sqrt(self.J_MAX_STOP) * self.stopping_coeff_v
            self.reg_phase = 3
        elif rp == 3:
            self.obst_in_loop = self.obst_f if self.direction == 1 else self.obst_b
            if self.distance_proj < self.D_PROJ_TOL * self.d_tol_perc and abs(v_base) < self.V_MIN * 2.0 \
                    and abs(w_base) < self.W_MIN * 2.0:
                self.movement_state = -1 if abs(self.distance) < self.D_TOL * self.d_tol_perc else -5
                return
            if self.obst_in_loop and abs(v_base) < self.V_MIN * 2.0 and abs(w_base) < self.W_MIN * 2.0:
                self.movement_state = -4
                return
            if abs(v_base) < self.V_MIN_STACKED * 0.5:
                self.stacked_cnt += 1
            else:
                self.stacked_cnt = 0
            if self.stacked_cnt * self.dt >= self.STACKED_TIME:
                self.movement_state = -3
                return
            self.distance = math.hypot(xe, ye)
            self.distance_proj = self.distance * math.cos(self.phi_error)
            self.v_ref = velocity_synthesis(self.distance_proj * self.direction, v_base, self.a, self.j_max_temp,
                                            self.stopping_distance, self.v_max_temp, self.V_MIN, self.dt, 0.0,
                                            self.obst_in_loop, self.V_SLOWED_MAX, self.V_MIN_ACC)
            self.w_ref = self.P_w * clamp((self.distance - self.D_SHORT_TOL) / (self.D_LONG_TOL - self.D_SHORT_TOL),
                                          0.0, 1.0) * self.phi_error
