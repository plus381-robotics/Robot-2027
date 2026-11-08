# Lažni STM32 za testove: ponaša se kao comm.c + most (comm_port.c) na nivou poruka.
#  - duplikat prepoznaje SAMO po poslednjem seq (kao comm.c), pa testovi vide pravo ponašanje
#  - drop = koliko sledećih komandi (ne PING) da "izgubi" pre obrade (kao da je okvir oštećen)
#  - drop_ack = koliko sledećih ACK-ova da izgubi posle obrade
#  - executed = šta je STM32 stvarno izvršio, redom
#  - kretanje traje motion_ms, pa DONE; STOP prekida (FAIL STOPPED)
#  - version: starija verzija šalje kraće PONG/STATUS (bez polja novijih verzija), kao stari firmver
#  - v4: RESET (restart posle ACK), RESUME, uptime_ms, reset_cause; reboot() = restart (npr. watchdog)
import protocol as P
from link import build_frame, FrameParser
import compat


class FakeSTM:
    def __init__(self, version=P.VERSION, motion_ms=1000):
        self.version, self.motion_ms = version, motion_ms
        self.p = FrameParser()
        self.out = b""
        self.on = True
        self.drop = self.drop_ack = self.drop_done = 0
        self.executed = []
        self.sent = []                 # (ime, polja) svake izvršene komande
        self.last_seq = None
        self.pose = [0, 0, 0]
        self.state = 0
        self.match0 = None
        self.motion = None             # (seq, kraj_ms)
        self.last_motion = (0, 0)      # v3: (seq, ishod) poslednje završene komande kretanja
        self.act_ms = 300              # koliko traje aktuator pre DONE
        self.act_fail = None           # razlog FAIL za aktuatore (npr. INVALID kao BlackPill bez njih)
        self.acts = []                 # [(seq, kraj_ms)] aktuatori koji rade
        self._last_status = -1000
        self.boot0 = compat.ticks_ms()  # v4: uptime_ms se računa od ovoga
        self.reset_cause = P.ResetCause.POWER
        self.link_ms = None            # pad veze: posle 500 ms bez PING-a staje (kretanje FAIL LINK/STOPPED)
        self.last_rx = None
        self.ir_raw, self.ir_mask = 0, 0xFF      # v5: šta vide IR senzori (test postavlja), koji su uključeni

    # ---- UART interfejs (ono što robot.py koristi) ----
    def write(self, data):
        if not self.on:
            return
        for t, seq, pl in self.p.feed(bytes(data)):
            self._frame(t, seq, pl)

    def read(self, n=None):
        if not self.on:
            return None
        self._tick()
        o, self.out = self.out, b""
        return o or None

    def init(self, **k):
        pass

    # ---- unutra ----
    # koliko bajtova poruka ima u starijoj verziji (polja novijih verzija su na kraju)
    _OLD = {"STATUS": ((3, 13), (4, 15), (5, 21)), "PONG": ((4, 1),)}

    def _send(self, name, seq=0, **f):
        t, pl = P.encode(name, **f)
        for v, n in self._OLD.get(name, ()):
            if self.version < v:
                pl = pl[:n]
                break
        self.out += build_frame(t, seq, pl)

    def reboot(self, cause=P.ResetCause.IWDG):
        """STM32 se restartuje: kretanje, meč i odometrija ispočetka."""
        self.motion, self.acts, self.last_seq = None, [], None
        self.state, self.match0, self.pose = 0, None, [0, 0, 0]
        self.last_motion = (0, 0)
        self.boot0, self.reset_cause = compat.ticks_ms(), cause
        self.ir_mask = 0xFF
        self._reboot_at = None

    def _frame(self, t, seq, pl):
        name, d = P.decode(t, pl)
        self.last_rx = compat.ticks_ms()
        if name == "PING":
            self._send("PONG", seq, version=self.version, reset_cause=self.reset_cause)
            return
        if self.drop:
            self.drop -= 1
            return
        if seq == self.last_seq:                     # comm.c: samo poslednji seq je duplikat
            self._ack(seq)
            return
        self.last_seq = seq
        self.executed.append(name)
        self.sent.append((name, d))
        if name in ("GOTO", "ROTATE", "MOVE"):
            if self.motion:
                self._send("FAIL", self.motion[0], reason=P.Reason.PREEMPTED)
                self.last_motion = (self.motion[0], P.Reason.PREEMPTED)
            self.motion = (seq, compat.ticks_ms() + self.motion_ms)
            self.state |= P.State.MOVING
        elif name == "STOP":
            self._stop(P.Reason.STOPPED)
        elif name == "SET_POSE":
            if self.motion:
                self._send("FAIL", seq, reason=P.Reason.INVALID)
                return
            self.pose = [d["x"], d["y"], d["theta"]]
        elif name == "ACTUATOR":
            if self.act_fail:
                self._send("FAIL", seq, reason=self.act_fail)
                return
            self.acts.append((seq, compat.ticks_ms() + self.act_ms))
        elif name == "MATCH_START":
            self.match0 = compat.ticks_ms()
            self.state |= P.State.MATCH_RUNNING
        elif name == "RESUME" and self.version >= 4:
            self.pose = [d["x"], d["y"], d["theta"]]
            self.match0 = compat.ticks_ms() - d["elapsed_ms"]
            self.state |= P.State.MATCH_RUNNING
        elif name == "RESET" and self.version >= 4:
            self._ack(seq)
            self.reboot(P.ResetCause.SOFT)
            return
        elif name == "IR_MASK" and self.version >= 5:
            self.ir_mask = d["mask"]
        elif name in ("RESUME", "RESET", "IR_MASK"):
            self._send("FAIL", seq, reason=P.Reason.INVALID)
            return
        self._ack(seq)

    def _ack(self, seq):
        if self.drop_ack:
            self.drop_ack -= 1
        else:
            self._send("ACK", seq)

    def _stop(self, reason):
        if self.motion:
            self._send("FAIL", self.motion[0], reason=reason)
            self.last_motion = (self.motion[0], reason)
        self.motion = None
        self.state &= ~P.State.MOVING

    def _tick(self):
        now = compat.ticks_ms()
        if self.motion and self.last_rx is not None and now - self.last_rx > 500:      # comm_tick_1ms
            self._stop(P.Reason.LINK if self.version >= 4 else P.Reason.STOPPED)
        if self.motion and now >= self.motion[1]:
            if self.drop_done:
                self.drop_done -= 1
            else:
                self._send("DONE", self.motion[0])
            self.last_motion = (self.motion[0], 0)
            self.motion = None
            self.state &= ~P.State.MOVING
        for a in [a for a in self.acts if now >= a[1]]:
            self.acts.remove(a)
            self._send("DONE", a[0])
        if now - self._last_status >= 50:
            self._last_status = now
            mm = now - self.match0 if self.match0 is not None else 0
            self._send("STATUS", x=self.pose[0], y=self.pose[1], theta=self.pose[2],
                       v=300 if self.motion else 0, state=self.state, match_ms=mm,
                       last_seq=self.last_motion[0], last_result=self.last_motion[1],
                       uptime_ms=now - self.boot0, w=0, ir_raw=self.ir_raw, ir_mask=self.ir_mask)
