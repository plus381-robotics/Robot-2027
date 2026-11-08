# Jedna simulacija: taktika (pravi ESP kod) + SimSTM, od postavljanja robota do kraja, sa snimkom.
#
#   from eurosim.sim import simulate
#   rec = simulate("primer", side="zuta", mode="mec")
#
# Režimi (isto kao na robotu):
#   "mec":  izbor taktike i strane -> NAORUZAN -> činč (cord_s) -> START poza -> taktika -> 100 s
#   "test": odmah, bez meča (kao tools/tactic.py / RUN preko WiFi-ja)
import base64
import contextlib
import io
import math
import pathlib
import subprocess
import sys
import tempfile
import time

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
    def __init__(self, name, side="zuta", mode="mec", prof=None, tactics_dir=None, start=None,
                 cord_s=1.0, max_s=None, obstacles=(), screen=True, schedule=(), control=None, emit=None,
                 net=None):
        """start: (x, y, ugao) stvarna poza na stolu u koordinatama naše strane (None = START iz taktike).
        schedule: [(s, fn(sim))] radnje u zadatom trenutku (npr. STOP, pomeranje protivnika).
        mode "live": interaktivno, u stvarnom vremenu; control() vraća listu komandi (vidi command()),
        emit(dict) dobija nove frame-ove, događaje i sliku ekrana (~20 puta u sekundi).
        net = {"upload": 8267, "telem": 8268, "password": "eurosim"}: virtuelni robot na mreži, sa pravim
        upload.py i telem.py (tools/tactic.py, tools/watch.py i Robot panel rade sa njim kao sa robotom);
        taktike su u njegovom "flešu" (privremeni folder), kao na ESP-u."""
        self.name, self.side, self.mode = name, side, mode
        self.prof = prof or profmod.load()
        self.tactics_dir = pathlib.Path(tactics_dir or paths.TACTICS)
        self.cord_ms = int(cord_s * 1000)
        self.max_ms = int((max_s if max_s is not None else (105 if mode == "mec" else 120)) * 1000)
        self._tmp = tempfile.TemporaryDirectory(prefix="eurosim-")
        self.flash = None
        if net:
            import shutil
            self.flash = pathlib.Path(self._tmp.name) / "flash"
            (self.flash / "tactics").mkdir(parents=True)
            for f in self.tactics_dir.glob("*.py"):
                shutil.copy(f, self.flash / "tactics")
            self.tactics_dir = self.flash / "tactics"
        self.out = io.StringIO()                 # print-ovi iz ESP koda
        with contextlib.redirect_stdout(self.out):
            self.esp = Esp(lambda clock: SimSTM(self.prof, clock), self.tactics_dir, self._tmp.name,
                           screen=screen, loop_extra_ms=self.prof.get("esp", {}).get("loop_extra_ms", 5),
                           inputs=True)
        self.stm = self.esp.stm
        self.app = self.esp.app
        if net:
            self._net(net)
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
        self._tac_seen = None
        self._screen = None
        # live
        self.control, self.emit = control, emit
        self.quit = False
        self.paused = False
        self.speed = 1.0
        self._anchor = None                      # (virtuelno ms, zid s) za ritam u stvarnom vremenu
        self._sent = (0, 0)                      # koliko frame-ova i događaja je poslato
        self._t_emit = 0.0
        self.esp.services.append(self._service)
        self._hook_lines()
        meta = self.esp.tactic_meta(name) if name else {}
        self.start_meta = meta.get("START")
        st = start or self.start_meta or (250, 1000, 0)
        self.start = tuple(st) + (0,) * (3 - len(st))
        mx, my, mdeg = self.esp.mirror(side, *self.start)
        self.stm.plant.place(mx, my, mdeg)
        own = side
        self.start_in_zone = field.in_zone(own, [(x * 1000, y * 1000) for x, y in self.stm.plant.corners()])
        src = self.tactics_dir / ((name or "") + ".py")
        self.rec.meta = {
            "tactic": name, "side": side, "mode": mode, "source": src.read_text(encoding="utf-8") if name and src.exists() else None,
            "start": list(self.start), "start_field": [mx, my, mdeg], "total": meta.get("TOTAL"),
            "profile": self.prof.get("name"), "body": self.prof["body"], "drive": self.prof["drive"],
            "field": field.describe(), "obstacles": [o.to_dict() for o in self.stm.plant.obstacles],
            "frame_ms": FRAME_MS, "git": _git_version(),
        }

    def _net(self, net):
        """Pravi ESP upload server i telemetrija, kao u main.py (bez WiFi-ja: mreža je ovaj računar)."""
        import types
        sys.modules["webrepl_cfg"] = types.SimpleNamespace(PASS=net.get("password", "eurosim"))
        import state
        import upload
        import telem
        state.MODE, state.SSID, state.IP = "STA", "eurosim", "127.0.0.1"
        upload.ROOT = str(self.flash)
        self.upload = upload.Upload(self.app, {}, None, port=net.get("upload", upload.PORT))
        self.telem = telem.Telem(self.app, port=net.get("telem", telem.PORT))
        self.esp.services.insert(0, self.telem.poll)
        from .esp import utf8_modules
        utf8_modules()
        self.esp.services.insert(0, self.upload.poll)

    # ---------------- linije koda (za editor) ----------------

    def _hook_lines(self):
        """Linija taktike za svaki korak i za izuzetak. Samo omotač oko tracker.step i app.error u ovom
        procesu (runner prevodi taktiku sa imenom fajla = ime taktike); ESP kod se ne menja."""
        tr, app = self.tracker, self.app
        orig_step, orig_error, orig_start = tr.step, app.error, tr.start
        cur = [None]                             # ime taktike koja radi (tracker ga briše pre app.error)

        def start(name, total=None):
            cur[0] = name
            orig_start(name, total)

        def line_here(tb=None):
            name = cur[0]
            if tb is not None:
                line = None
                while tb is not None:
                    if tb.tb_frame.f_code.co_filename == name:
                        line = tb.tb_lineno
                    tb = tb.tb_next
                return line
            f = sys._getframe(2)
            while f is not None:
                if f.f_code.co_filename == name:
                    return f.f_lineno
                f = f.f_back
            return None

        def step(name, timeout=None, next=None):
            line = line_here()
            orig_step(name, timeout, next)
            if line:
                self.rec.event(self.t(), "line", [tr.idx, line])

        def error(text):
            _, ev, tb = sys.exc_info()
            if ev is not None:
                line = ev.lineno if isinstance(ev, SyntaxError) else line_here(tb)
                self.rec.event(self.t(), "exception", {"type": type(ev).__name__, "msg": str(ev), "line": line})
            orig_error(text)

        tr.start = start
        tr.step = step
        app.error = error

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
        if self.mode == "live":
            self._live_service()
        elif t >= self.max_ms and self.app.running and not self._abort_sent:
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
        if tr.running and tr.t_start != self._tac_seen:     # nova taktika (u live režimu može ih biti više)
            self._tac_seen = tr.t_start
            self._step_idx = 0
            self.rec.event(t, "tactic", [tr.name, a.side])
            if self.mode == "live":
                src = self.tactics_dir / (tr.name + ".py")
                self.rec.meta.update(tactic=tr.name, side=a.side, total=tr.total,
                                     source=src.read_text(encoding="utf-8") if src.exists() else None)
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
        px = self.esp.screen()
        if px is not None:
            fb = self.esp.fb
            b = bytes(sum(row[x * 8 + k] << (7 - k) for k in range(8)) for row in px for x in range(16))
            if b != self._screen or not fb.on:
                self._screen = b
                self.rec.event(t, "screen", {"b": base64.b64encode(b).decode(), "on": fb.on, "flip": fb.flip})
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
        if self.mode == "live":
            return self._run_live()
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

    # ---------------- live ----------------

    def command(self, c):
        """Komanda iz UI-ja (live): ("btn", ime, dole), ("rot", klikova), ("cord",), ("arm", taktika, strana),
        ("test", taktika, strana), ("stop",), ("obstacles", [..]), ("place", x, y, ugao), ("speed", x),
        ("pause", bool), ("quit",). ime tastera: back, ok, stop, enc."""
        k, a = c[0], self.app
        if k == "btn":
            self.esp.button(c[1], bool(c[2]))
        elif k == "rot":
            self.esp.rotate(int(c[1]))
        elif k == "cord":
            self.stm.pull_cord()
        elif k == "arm":
            a.select(c[1], c[2])
            a.arm()
        elif k == "test":
            a.start_tactic(c[1], c[2])
        elif k == "stop":
            self.event("sim", {"text": "STOP (iz simulatora)"})
            a.stop()
        elif k == "obstacles":
            self.stm.plant.obstacles = [Obstacle(**o) for o in c[1]]
            self.rec.meta["obstacles"] = [o.to_dict() for o in self.stm.plant.obstacles]
            self.event("obstacles", self.rec.meta["obstacles"])
        elif k == "place":
            if self.stm.phase == "IDLE":
                self.stm.plant.place(c[1], c[2], c[3])
                self.event("sim", {"text": "robot postavljen na %d, %d, %d°" % (c[1], c[2], c[3])})
        elif k == "speed":
            self.speed = max(0.05, float(c[1]))
            self._anchor = None
        elif k == "pause":
            self.paused = bool(c[1])
            self._anchor = None
        elif k == "quit":
            self.quit = True
            if a.running:
                a.abort = "sim: kraj"

    def _poll_control(self):
        if self.control:
            for c in self.control():
                self.command(c)

    def _live_service(self):
        self._poll_control()
        while self.paused and not self.quit:
            self._emit()
            time.sleep(0.03)
            self._poll_control()
        now_v, wall = self.t(), time.monotonic()
        if self._anchor is None:
            self._anchor = (now_v, wall)
        v0, w0 = self._anchor
        d = w0 + (now_v - v0) / 1000 / self.speed - wall
        if d > 0:
            time.sleep(min(d, 0.1))
        elif d < -0.5:                            # računar ne stiže: ne sustiži, nastavi odavde
            self._anchor = (now_v, wall)
        if time.monotonic() - self._t_emit >= 0.05:
            self._emit()

    def _emit(self, final=False):
        self._t_emit = time.monotonic()
        if not self.emit:
            return
        nf, ne = self._sent
        a = self.app
        self.emit({"frames": self.rec.frames[nf:], "events": self.rec.events[ne:], "t": self.t(),
                   "paused": self.paused, "speed": self.speed, "running": a.running, "mec": a.match.state,
                   "meta": self.rec.meta if final or nf == 0 else None, "final": final})
        self._sent = (len(self.rec.frames), len(self.rec.events))

    def _run_live(self):
        while not self.quit:
            self.esp.step()
        self._collect(self.t())
        self._emit(final=True)                   # poslednji podaci uvek stignu (ne čeka zidni sat)
        self._finish()

    def _finish(self):
        a, pl = self.app, self.stm.plant
        rp = a.report or {}
        corners = [(x * 1000, y * 1000) for x, y in pl.corners()]
        own = self.side
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
