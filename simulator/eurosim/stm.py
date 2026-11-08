# Simulirani STM32 (BlackPill): comm.c + comm_port.c + control.c, na nivou bajtova na UART-u.
#
# ESP kod (robot.py) ga vidi kao UART (write/read), isto kao pravi STM32: COBS + CRC16, isti
# protocol.py. Vreme je virtuelno (clock() u ms, isti sat kao ESP kod); pri svakom write/read
# simulacija se dovede do trenutnog vremena u koracima od 1 ms (kao 1 kHz petlja na STM32).
#
# Verno prati (vidi komentare sa imenima C funkcija):
#  - comm.c: duplikat samo po poslednjem seq (ponovi poslednji odgovor), PREEMPTED za staru komandu
#    kretanja, STOP odmah šalje FAIL STOPPED, pad veze posle 500 ms bez ispravnog okvira -> stop i
#    bez STATUS-a dok se ESP ne javi (tada seq kreće ispočetka), STATUS na 50 ms, nepoznato -> INVALID
#  - comm_port.c: GOTO = vožnja pa okret na theta (osim NO_THETA), MOVE = tačka ispred/iza,
#    ROTATE timeout 5 s, statusi regulacije -1 DONE / -3 -4 BLOCKED / -5 TIMEOUT, SET_POSE samo
#    kad robot stoji, meč 100 s pa MATCH_OVER
#  - aktuatori (novi robot: AX i pumpe): ACK pa DONE posle zadatog vremena, nikad FAIL
#  - protokol v4: RESET (restart 30 ms posle ACK), RESUME (poza + meč od elapsed_ms), uptime_ms i w u
#    STATUS-u, reset_cause u PONG-u, pad veze prekida kretanje sa LINK. Profil [link] protocol_version < 4:
#    PONG/STATUS su kraći (kao stari firmver), RESET/RESUME -> INVALID.
import math

from . import paths
from .control import Control, Goal
from .plant import Plant

import sys
for _p in (str(paths.ESP / "lib"),):
    if _p not in sys.path:
        sys.path.append(_p)
import protocol as P                     # noqa: E402  (ESP32/lib/protocol.py, generisan iz yaml-a)
from link import build_frame, FrameParser  # noqa: E402

MATCH_MS = 100000
IDLE, DRIVE, TURN = "IDLE", "DRIVE", "TURN"
REASON_NAME = {getattr(P.Reason, k): k for k in dir(P.Reason) if not k.startswith("_")}
QUIET = ("PING", "PONG", "STATUS")       # ne upisuju se u trag poruka (ima ih previše)


class SimSTM:
    def __init__(self, profile, clock):
        self.p, self.clock = profile, clock
        lk = profile.get("link", {})
        self.version = lk.get("protocol_version", P.VERSION)
        self.hb_ms = lk.get("heartbeat_ms", 500)
        self.status_ms = lk.get("status_period_ms", 50)
        c = profile["control"]
        self.c = c
        self.plant = Plant(profile)
        self.ctl = Control(c, profile["drive"]["wheel_v_max"], self.plant.track)
        act = profile.get("actuators", {})
        self.act_on = act.get("enabled", True)
        self.act_ms = act.get("default_ms", 300)
        self.act_ms_by_id = {}                  # id -> ms (popunjava esp.py iz imena)
        self.parser = FrameParser()
        self.out = bytearray()
        self.t = clock()                        # do kog ms je simulacija stigla
        self.on = True                          # False = "isključen kabl"
        self.drop_rx = 0                        # koliko sledećih okvira od ESP-a da izgubi (test)
        self.trace = []                         # (t, "rx"|"tx", ime, seq, polja) bez PING/PONG/STATUS
        # comm.c
        self.last_rx = 0
        self.esp_seen = False
        self.link_lost = False
        self.last_seq = 0
        self.last_reply = ("ACK", 0)
        self.motion_seq = 0
        self.last_motion = (0, 0)
        self.last_status = -10 ** 9
        self.boot_t = self.t                    # v4: uptime_ms = t - boot_t
        self.reset_cause = P.ResetCause.POWER
        self.reset_at = None                    # komanda RESET: kad se restartuje
        # comm_port.c
        self.goal = Goal()
        self.phase = IDLE
        self.phase_t0 = 0
        self.has_final = False
        self.final_phi = 0.0
        self.stop_request = 0
        self.req = None
        self.match_running = self.match_over = False
        self.match_start = 0
        # aktuatori
        self.acts = []                          # [(kraj_ms, seq, id, value)]
        self.act_state = {}                     # id -> poslednja vrednost
        self.ctl.reset_goal(self.goal, self.odom())

    # ---------------- UART (ono što robot.py koristi) ----------------

    def init(self, **k):
        pass

    def write(self, data):
        self.advance()
        if not self.on:
            return
        for t, seq, pl in self.parser.feed(bytes(data)):
            if self.drop_rx:
                self.drop_rx -= 1
                continue
            self._handle(t, seq, pl)

    def read(self, n=None):
        self.advance()
        if not self.on or not self.out:
            return None
        o, self.out = bytes(self.out), bytearray()
        return o

    # ---------------- vreme ----------------

    def advance(self, until=None):
        now = self.clock() if until is None else until
        while self.t < now:
            self.t += 1
            self._tick()

    def _tick(self):
        t = self.t
        if self.reset_at is not None and t >= self.reset_at:       # comm_poll: NVIC_SystemReset posle RESET
            self.hard_reset("restart (komanda RESET)", P.ResetCause.SOFT)
            return
        # comm_tick_1ms: pad veze
        if self.esp_seen and not self.link_lost and t - self.last_rx > self.hb_ms:
            self.link_lost = True
            self._hook_stop()
            self.log_event("veza", "pad veze (nema PING-a %d ms): STOP" % self.hb_ms)
        # aktuatori
        if self.acts:
            for a in [a for a in self.acts if t >= a[0]]:
                self.acts.remove(a)
                self.act_state[a[2]] = a[3]
                self._send("DONE", a[1])
        # comm_port_update + move_goal + control_loop (1 kHz)
        self._port_update()
        if self.plant.obstacles:
            self.goal.obstacle = self.plant.scan()
        else:
            self.goal.obstacle = self.plant.ir = 0
        self.ctl.move_goal(self.goal, self.odom())
        vr, vl = self.ctl.loop(self.odom())
        self.plant.step(vr, vl)
        # comm_poll: STATUS
        if self.esp_seen and not self.link_lost and t - self.last_status >= self.status_ms:
            self.last_status = t
            self._send_status()

    def odom(self):
        pl = self.plant
        return (pl.ox, pl.oy, pl.oth, pl.ov, pl.ow)

    # ---------------- comm.c ----------------

    _OLD = {"STATUS": ((3, 13), (4, 15)), "PONG": ((4, 1),)}   # starija verzija: kraća poruka

    def _send(self, name, seq=0, **f):
        t, pl = P.encode(name, **f)
        for v, n in self._OLD.get(name, ()):
            if self.version < v:
                pl = pl[:n]
                break
        self.out += build_frame(t, seq, pl)
        if name not in QUIET:
            self.trace.append((self.t, "tx", name, seq, f))

    def _reply(self, seq, reason):
        if reason:
            self.last_reply = ("FAIL", reason)
            self._send("FAIL", seq, reason=reason)
        else:
            self.last_reply = ("ACK", 0)
            self._send("ACK", seq)

    def motion_finished(self, reason):          # comm_motion_finished
        if not self.motion_seq:
            return
        self.last_motion = (self.motion_seq, reason)    # v3: ide i u STATUS
        if reason:
            self._send("FAIL", self.motion_seq, reason=reason)
        else:
            self._send("DONE", self.motion_seq)
        self.motion_seq = 0

    def _start_motion(self, seq, reason):
        if not reason:
            if self.motion_seq:
                self.motion_finished(P.Reason.PREEMPTED)
            self.motion_seq = seq
        self._reply(seq, reason)

    def _handle(self, t, seq, pl):
        self.last_rx = self.t
        if self.link_lost:
            self.last_seq = 0
        self.esp_seen = True
        self.link_lost = False
        try:
            name, d = P.decode(t, pl)
        except Exception:
            name, d = None, {}
        if name == "PING":
            self._send("PONG", seq, version=self.version, reset_cause=self.reset_cause)
            return
        if name not in QUIET:
            self.trace.append((self.t, "rx", name or "0x%02x" % t, seq, d))
        if seq == 0:
            return
        if seq == self.last_seq:
            kind, reason = self.last_reply
            if kind == "FAIL":
                self._send("FAIL", seq, reason=reason)
            else:
                self._send("ACK", seq)
            return
        self.last_seq = seq
        R = P.Reason
        if name == "SET_POSE":
            self._reply(seq, self._set_pose(d["x"], d["y"], d["theta"]))
        elif name == "GOTO":
            self._start_motion(seq, self._hook_goto(**d))
        elif name == "ROTATE":
            self._start_motion(seq, self._hook_rotate(d["theta"]))
        elif name == "MOVE":
            self._start_motion(seq, self._hook_move(d["dist"], d["max_speed"]))
        elif name == "STOP":
            self._hook_stop()
            self.motion_finished(R.STOPPED)
            self._reply(seq, 0)
        elif name == "ACTUATOR":
            self._reply(seq, self._hook_actuator(seq, d["id"], d["value"]))
        elif name == "MATCH_START":
            self.match_start_now()
            self._reply(seq, 0)
        elif name == "RESUME" and self.version >= 4:
            r = self._set_pose(d["x"], d["y"], d["theta"])
            if not r:
                self.match_start = self.t - d["elapsed_ms"]      # comm_port_resume: sat nastavlja
                self.match_running = True
                self.log_event("stm", "RESUME: poza i mec od %.1f s" % (d["elapsed_ms"] / 1000))
            self._reply(seq, r)
        elif name == "RESET" and self.version >= 4:
            self._hook_stop()
            self._reply(seq, 0)
            self.reset_at = self.t + 30
        else:                                   # nepoznato, pogrešna dužina, ENTER_BOOTLOADER (nema u sim.)
            self._reply(seq, R.INVALID)

    def _send_status(self):
        pl = self.plant
        phi = pl.oth
        state = 0
        match_ms = 0
        if self.match_over:
            state |= P.State.MATCH_OVER
            match_ms = MATCH_MS
        elif self.match_running:
            state |= P.State.MATCH_RUNNING
            match_ms = self.t - self.match_start
        if self.motion_seq:
            state |= P.State.MOVING
        cl = lambda v: max(-32768, min(32767, int(v)))   # noqa: E731  (clamp16, kao (int16_t) u C-u)
        self._send("STATUS", x=cl(pl.ox * 1000), y=cl(pl.oy * 1000), theta=cl(phi * 18000 / math.pi),
                   v=cl(pl.ov * 1000), state=state, match_ms=match_ms,
                   last_seq=self.last_motion[0], last_result=self.last_motion[1],
                   uptime_ms=(self.t - self.boot_t) & 0xFFFFFFFF, w=cl(pl.ow * 1000))

    # ---------------- comm_port.c ----------------

    def match_start_now(self):                  # comm_port_match_start (i činč na novom robotu)
        if not self.match_running:
            self.match_start = self.t
            self.match_running = True

    def pull_cord(self):
        """Izvučen činč: na novom robotu STM32 sam kreće da broji 100 s."""
        self.advance()
        self.match_start_now()
        self.log_event("cinc", "cinc izvucen")

    def _set_pose(self, x, y, th):
        if self.phase != IDLE or self.req:
            return P.Reason.INVALID
        self.plant.set_odom(x / 1000, y / 1000, th * math.pi / 18000)
        return 0

    def _speed(self, ms):
        return ms / 1000 if ms else self.c["V_DEFAULT"]

    def _hook_goto(self, x, y, theta, flags, max_speed):
        if self.match_over:
            return P.Reason.MATCH_OVER
        self.req = dict(type=1, x=x / 1000, y=y / 1000, phi=theta * math.pi / 18000,
                        dir=-1 if flags & P.GotoFlags.REVERSE else 1, v=self._speed(max_speed),
                        final=not (flags & P.GotoFlags.NO_THETA))
        return 0

    def _hook_rotate(self, theta):
        if self.match_over:
            return P.Reason.MATCH_OVER
        self.req = dict(type=-1, phi=theta * math.pi / 18000, final=False)
        return 0

    def _hook_move(self, dist, max_speed):
        if self.match_over:
            return P.Reason.MATCH_OVER
        if dist == 0:
            return P.Reason.INVALID
        d = dist / 1000
        pl = self.plant
        self.req = dict(type=1, x=pl.ox + d * math.cos(pl.oth), y=pl.oy + d * math.sin(pl.oth),
                        dir=1 if d > 0 else -1, v=self._speed(max_speed), final=False, phi=0.0)
        return 0

    def _hook_actuator(self, seq, aid, value):
        if not self.act_on:
            return P.Reason.INVALID             # BlackPill: nema aktuatora
        self.acts.append((self.t + self.act_ms_by_id.get(aid, self.act_ms), seq, aid, value))
        return 0

    def _hook_stop(self):
        self.req = None
        # comm_stop_reason(): posle pada veze LINK (v4), inače STOPPED
        self.stop_request = P.Reason.LINK if self.link_lost and self.version >= 4 else P.Reason.STOPPED

    def _finish(self, reason):
        self.motion_finished(reason)
        self.ctl.reset_goal(self.goal, self.odom())
        self.phase = IDLE

    def _start_turn(self, phi):
        self.ctl.reset_goal(self.goal, self.odom())
        self.goal.phi = phi
        self.goal.w_max = self.c["W_ROTATE"]
        self.goal.type = -1
        self.phase = TURN
        self.phase_t0 = self.t

    def _start(self):
        r = self.req
        self.has_final, self.final_phi = r["final"], r["phi"]
        if r["type"] == -1:
            self._start_turn(r["phi"])
            return
        pl = self.plant
        if math.hypot(r["x"] - pl.ox, r["y"] - pl.oy) < self.c["D_ARRIVED"]:
            if self.has_final:
                self._start_turn(self.final_phi)
            else:
                self._finish(0)
            return
        g = self.goal
        self.ctl.reset_goal(g, self.odom())
        g.x, g.y, g.direction, g.v_max, g.w_max, g.type = r["x"], r["y"], r["dir"], r["v"], self.c["W_GOTO"], 1
        self.phase = DRIVE
        self.phase_t0 = self.t

    def _port_update(self):
        now = self.t
        if self.match_running and not self.match_over and now - self.match_start >= MATCH_MS:
            self.match_over = True
            self.req = None
            self.stop_request = P.Reason.MATCH_OVER
            self.log_event("mec", "100 s: kraj meca")
        if self.stop_request:
            reason, self.stop_request = self.stop_request, 0
            self._finish(reason)
        if self.req:
            self._start()
            self.req = None
        if self.phase == IDLE:
            return
        st = self.goal.status
        if st == -1:
            if self.phase == DRIVE and self.has_final:
                self._start_turn(self.final_phi)
            else:
                self._finish(0)
        elif st in (-3, -4):
            self._finish(P.Reason.BLOCKED)
        elif st == -5:
            self._finish(P.Reason.TIMEOUT)
        elif self.phase == TURN and now - self.phase_t0 > self.c["ROT_TIMEOUT_MS"]:
            self._finish(P.Reason.TIMEOUT)

    # ---------------- restart (NRST, watchdog, pad napona) ----------------

    def hard_reset(self, why="reset", cause=P.ResetCause.PIN):
        """STM32 se restartuje: sve iz comm.c / comm_port.c / regulacije ispočetka, odometrija (0, 0, 0),
        motori stanu. Stvarna poza robota na stolu ostaje."""
        pl = self.plant
        x, y, th, obstacles = pl.x, pl.y, pl.th, pl.obstacles
        trace, t, on = self.trace, self.clock(), self.on
        acts = self.act_ms_by_id
        self.__init__(self.p, self.clock)
        self.plant.place(x * 1000, y * 1000, th * 180 / math.pi)
        self.plant.obstacles = obstacles
        self.trace, self.t, self.on, self.act_ms_by_id = trace, t, on, acts
        self.boot_t, self.reset_cause = t, cause
        self.log_event("stm", "STM32 %s: odometrija 0,0,0, mec ne broji" % why)

    # ---------------- za prikaz ----------------

    def log_event(self, kind, text):
        self.trace.append((self.t, "sim", kind, 0, {"text": text}))

    def snapshot(self):
        pl, c = self.plant, self.ctl
        irh = None                              # IR: udaljenost pogotka po senzoru (mm), -1 = ništa; samo kad ima pogodaka
        if pl.ir_hits:
            names = [s[0] for s in pl.sensors()]
            d = dict(pl.ir_hits)
            irh = [int(d[n] * 1000) if n in d else -1 for n in names]
        return {"irh": irh,
            "x": pl.x * 1000, "y": pl.y * 1000, "th": math.degrees(pl.th),
            "ox": pl.ox * 1000, "oy": pl.oy * 1000, "oth": math.degrees(pl.oth),
            "v": pl.v, "w": pl.w, "vl": pl.vl, "vr": pl.vr,
            "v_ref": c.v_ref, "w_ref": c.w_ref, "phase": self.phase, "reg": c.reg_phase,
            "ms": c.movement_state, "stuck": pl.stuck, "ir": pl.ir,
            "match": self.t - self.match_start if self.match_running and not self.match_over else
            (MATCH_MS if self.match_over else None),
            "link": not self.link_lost and self.esp_seen,
        }
