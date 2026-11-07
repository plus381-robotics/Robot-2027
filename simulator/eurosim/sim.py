# Jedna simulacija: taktika (pravi ESP kod) + SimSTM, od postavljanja robota do kraja, sa snimkom.
#
#   from eurosim.sim import simulate
#   rec = simulate("primer", side="zuta", mode="mec")
#
# Režimi (isto kao na robotu):
#   "mec":  izbor taktike i strane -> NAORUZAN -> činč (cord_s) -> START poza -> taktika -> 100 s
#   "test": odmah, bez meča (kao tools/tactic.py / RUN preko WiFi-ja)
import contextlib
import io
import math
import pathlib
import subprocess
import tempfile

from . import field, paths, profile as profmod
from .esp import Esp
from .plant import Obstacle
from .record import Recording, FRAME_MS
from .stm import SimSTM

SETTLE_MS = 500              # posle kraja taktike još ovoliko (robot se smiri)
WARMUP_MS = 300              # veza, PONG, auto SET_POSE pre pokretanja


def _git_version():
    try:
        return subprocess.run(["git", "describe", "--always", "--dirty"], cwd=paths.ROOT,
                              capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception:
        return ""


class Sim:
    def __init__(self, name, side="plava", mode="mec", prof=None, tactics_dir=None, start=None,
                 cord_s=1.0, max_s=None, obstacles=(), screen=False, schedule=()):
        """start: (x, y, ugao) stvarna poza na stolu u koordinatama naše strane (None = START iz taktike).
        schedule: [(s, fn(sim))] radnje u zadatom trenutku (npr. STOP, pomeranje protivnika)."""
        self.name, self.side, self.mode = name, side, mode
        self.prof = prof or profmod.load()
        self.tactics_dir = pathlib.Path(tactics_dir or paths.TACTICS)
        self.cord_ms = int(cord_s * 1000)
        self.max_ms = int((max_s if max_s is not None else (105 if mode == "mec" else 120)) * 1000)
        self._tmp = tempfile.TemporaryDirectory(prefix="eurosim-")
        self.out = io.StringIO()                 # print-ovi iz ESP koda
        with contextlib.redirect_stdout(self.out):
            self.esp = Esp(lambda clock: SimSTM(self.prof, clock), self.tactics_dir, self._tmp.name,
                           screen=screen, loop_extra_ms=self.prof.get("esp", {}).get("loop_extra_ms", 5))
        self.stm = self.esp.stm
        self.app = self.esp.app
        self.tracker = self.esp.tracker
        ids = self.esp.actuator_ids()
        for nm, ms in self.prof.get("actuators", {}).get("ms", {}).items():
            if nm in ids:
                self.stm.act_ms_by_id[ids[nm]] = ms
        self.stm.plant.obstacles = [o if isinstance(o, Obstacle) else Obstacle(**o) for o in obstacles]
        self.schedule = sorted(schedule, key=lambda s: s[0])
        self.t0 = self.esp.now()
        self.rec = Recording()
        self._last_frame = -FRAME_MS
        self._trace_n = 0
        self._log_n = 0
        self._hist_seen = None
        self._step_idx = 0
        self._started = False
        self._ended_at = None
        self._abort_sent = False
        self.stop_requested = False
        self.esp.services.append(self._service)
        meta = self.esp.tactic_meta(name)
        self.start_meta = meta.get("START")
        st = start or self.start_meta or (250, 1000, 0)
        self.start = tuple(st) + (0,) * (3 - len(st))
        mx, my, mdeg = self.esp.mirror(side, *self.start)
        self.stm.plant.place(mx, my, mdeg)
        own = side
        self.start_in_zone = field.in_zone(own, [(x * 1000, y * 1000) for x, y in self.stm.plant.corners()])
        src = (self.tactics_dir / (name + ".py"))
        self.rec.meta = {
            "tactic": name, "side": side, "mode": mode, "source": src.read_text() if src.exists() else None,
            "start": list(self.start), "start_field": [mx, my, mdeg], "total": meta.get("TOTAL"),
            "profile": self.prof.get("name"), "body": self.prof["body"], "drive": self.prof["drive"],
            "field": field.describe(), "obstacles": [o.to_dict() for o in self.stm.plant.obstacles],
            "frame_ms": FRAME_MS, "git": _git_version(),
        }

    # ---------------- vreme ----------------

    def t(self):
        return self.esp.now() - self.t0

    # ---------------- servis u ESP petlji (radi i dok taktika čeka) ----------------

    def _service(self):
        self.stm.advance()
        t = self.t()
        if self.app.running:
            self._started = True
        while self.schedule and self.schedule[0][0] * 1000 <= t:
            _, fn = self.schedule.pop(0)
            fn(self)
        if self.stop_requested:
            self.stop_requested = False
            self.event("sim", {"text": "STOP (taster)"})
            self.app.stop()
        if t >= self.max_ms and self.app.running and not self._abort_sent:
            self._abort_sent = True
            self.app.abort = "sim: isteklo %ds" % (self.max_ms // 1000)
        self._collect(t)

    def event(self, kind, data):
        self.rec.event(self.t(), kind, data)

    def _collect(self, t):
        st = self.stm
        for tt, d, nm, seq, f in st.trace[self._trace_n:]:
            if d == "sim":
                self.rec.event(tt - self.t0, "sim", {"kind": nm, "text": f["text"]})
            else:
                self.rec.event(tt - self.t0, d, {"name": nm, "seq": seq, "f": {k: (v.decode(errors="replace")
                                                                                   if isinstance(v, bytes) else v)
                                                                               for k, v in f.items()}})
        self._trace_n = len(st.trace)
        a = self.app
        if a.log_n != self._log_n:
            first = a.log_n - len(a.log)
            for i, line in enumerate(a.log):
                if first + i >= self._log_n:
                    self.rec.event(t, "log", line)
            self._log_n = a.log_n
        tr = self.tracker
        if tr.step_name and tr.idx != self._step_idx:
            self._step_idx = tr.idx
            self.rec.event(t, "step", [tr.idx, tr.step_name, tr.timeout_ms, tr.next])
        h = tr.history[-1] if tr.history else None
        if h is not None and h is not self._hist_seen:
            # history se pravi kao nova lista; novi zatvoreni koraci su oni posle poslednjeg viđenog
            seen = self._hist_seen
            new = tr.history if seen is None or seen not in tr.history else \
                tr.history[tr.history.index(seen) + 1:]
            for x in new:
                self.rec.event(t, "step_end", list(x))
            self._hist_seen = h
        if t - self._last_frame >= FRAME_MS:
            self._last_frame = t - t % FRAME_MS
            s = st.snapshot()
            r = a.robot
            s.update(t=t, mec=a.match.state, ok=r.ok, run=a.running,
                     tac=tr.name, i=tr.idx, n=tr.total, step=tr.step_name, el=tr.elapsed(), to=tr.timeout_ms)
            if st.acts or st.act_state:
                s["act"] = {str(k): v for k, v in st.act_state.items()}
            self.rec.frame(s)

    # ---------------- tok ----------------

    def run(self):
        with contextlib.redirect_stdout(self.out):
            self._run()
        return self.rec

    def _until(self, cond):
        while not cond():
            self.esp.step()

    def _run(self):
        a, esp = self.app, self.esp
        self._until(lambda: self.t() >= WARMUP_MS)
        if not a.robot.ok:
            self.event("sim", {"text": "STM32 se ne javlja"})
        if self.mode == "test":
            a.start_tactic(self.name, self.side)
        else:
            a.select(self.name, self.side)
            a.arm()
            cord_at = self.t() + self.cord_ms
            self._until(lambda: self.t() >= cord_at)
            self.stm.pull_cord()
        while True:
            esp.step()
            t = self.t()
            if self._started and not a.running and not a.request and self._ended_at is None:
                self._ended_at = t
            if self._ended_at is not None and t - self._ended_at >= SETTLE_MS and self.stm.phase == "IDLE":
                break
            if t >= self.max_ms + SETTLE_MS:
                break
            if not self._started and t > WARMUP_MS + self.cord_ms + 3000:
                self.event("sim", {"text": "taktika nije krenula"})
                break
        self._collect(self.t())
        self._finish()

    def _finish(self):
        a, pl = self.app, self.stm.plant
        rp = a.report or {}
        corners = [(x * 1000, y * 1000) for x, y in pl.corners()]
        own = "plava" if self.side == "plava" else "zuta"
        self.rec.result = {
            "ok": bool(rp.get("ok")), "how": rp.get("how"), "ms": rp.get("ms"),
            "steps": rp.get("steps"), "done": rp.get("done"), "fail": rp.get("fail"),
            "pose": [round(pl.x * 1000, 1), round(pl.y * 1000, 1), round(math.degrees(pl.th), 1)],
            "odom": [round(pl.ox * 1000, 1), round(pl.oy * 1000, 1), round(math.degrees(pl.oth), 1)],
            "in_own_zone": field.in_zone(own, corners), "start_in_zone": self.start_in_zone,
            "errors": [e[1] for e in a.errors],
            "sim_ms": self.t(), "match_over": self.stm.match_over,
            "esp_out": self.out.getvalue().splitlines()[-200:],
        }
        self._tmp.cleanup()


def simulate(name, **kw):
    return Sim(name, **kw).run()
