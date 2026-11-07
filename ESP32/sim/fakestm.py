# Lažni STM32 za testove: ponaša se kao comm.c + most (comm_port.c) na nivou poruka.
#  - duplikat prepoznaje SAMO po poslednjem seq (kao comm.c), pa testovi vide pravo ponašanje
#  - drop = koliko sledećih komandi (ne PING) da "izgubi" pre obrade (kao da je okvir oštećen)
#  - drop_ack = koliko sledećih ACK-ova da izgubi posle obrade
#  - executed = šta je STM32 stvarno izvršio, redom
#  - kretanje traje motion_ms, pa DONE; STOP prekida (FAIL STOPPED)
import protocol as P
from link import build_frame, FrameParser
import compat


class FakeSTM:
    def __init__(self, version=P.VERSION, motion_ms=1000):
        self.version, self.motion_ms = version, motion_ms
        self.p = FrameParser()
        self.out = b""
        self.on = True
        self.drop = self.drop_ack = 0
        self.executed = []
        self.last_seq = None
        self.pose = [0, 0, 0]
        self.state = 0
        self.match0 = None
        self.motion = None             # (seq, kraj_ms)
        self._last_status = -1000

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
    def _send(self, name, seq=0, **f):
        t, pl = P.encode(name, **f)
        self.out += build_frame(t, seq, pl)

    def _frame(self, t, seq, pl):
        name, d = P.decode(t, pl)
        if name == "PING":
            self._send("PONG", seq, version=self.version)
            return
        if self.drop:
            self.drop -= 1
            return
        if seq == self.last_seq:                     # comm.c: samo poslednji seq je duplikat
            self._ack(seq)
            return
        self.last_seq = seq
        self.executed.append(name)
        if name in ("GOTO", "ROTATE", "MOVE"):
            if self.motion:
                self._send("FAIL", self.motion[0], reason=P.Reason.PREEMPTED)
            self.motion = (seq, compat.ticks_ms() + self.motion_ms)
            self.state |= P.State.MOVING
        elif name == "STOP":
            self._stop(P.Reason.STOPPED)
        elif name == "SET_POSE":
            if self.motion:
                self._send("FAIL", seq, reason=P.Reason.INVALID)
                return
            self.pose = [d["x"], d["y"], d["theta"]]
        elif name == "MATCH_START":
            self.match0 = compat.ticks_ms()
            self.state |= P.State.MATCH_RUNNING
        self._ack(seq)

    def _ack(self, seq):
        if self.drop_ack:
            self.drop_ack -= 1
        else:
            self._send("ACK", seq)

    def _stop(self, reason):
        if self.motion:
            self._send("FAIL", self.motion[0], reason=reason)
        self.motion = None
        self.state &= ~P.State.MOVING

    def _tick(self):
        now = compat.ticks_ms()
        if self.motion and now >= self.motion[1]:
            self._send("DONE", self.motion[0])
            self.motion = None
            self.state &= ~P.State.MOVING
        if now - self._last_status >= 50:
            self._last_status = now
            mm = now - self.match0 if self.match0 is not None else 0
            self._send("STATUS", x=self.pose[0], y=self.pose[1], theta=self.pose[2],
                       v=300 if self.motion else 0, state=self.state, match_ms=mm)
