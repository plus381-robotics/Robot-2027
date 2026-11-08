# Nacrt putanje dok se piše (plan S7): taktika se izvrši sa lažnim tac modulom koji ne vozi ništa, nego samo
# zabeleži komande i izračuna idealnu putanju (goto = okret pa prava, move = prava, okreti, aktuatori kao
# oznake, wait kao vreme). Komande vraćaju True (sve uspeva). Radi sa promenljivama, petljama i funkcijama,
# što obično čitanje teksta (AST) ne može. Za svaku komandu se pamti red u kodu (veza kod <-> mapa).
#
# Ograničenja: najviše MAX_CMDS komandi, 100 s procenjenog vremena i MAX_LINES izvršenih redova (beskonačna
# petlja bez komande), pa se izvršavanje prekida i nacrt je "skraćen". Ne uvozi pravi tac ni ESP kod.
import math
import sys
import threading
import types

from . import field

MAX_CMDS = 300
MAX_S = 100.0
MAX_LINES = 200000
TURN_DPS = 180.0               # okret ~3,14 rad/s (comm_port.c W_ROTATE)
FILENAME = "<taktika>"
_lock = threading.Lock()       # sys.modules["tac"] i settrace su globalni: jedan nacrt u isto vreme


class _Stop(BaseException):
    """Prekid nacrta (ograničenje); BaseException da ga taktika ne uhvati sa except Exception."""


class TimeUp(Exception):
    pass


class Abort(Exception):
    pass


def _wrap(deg):
    return (deg + 180.0) % 360.0 - 180.0


class _Fake:
    def __init__(self, side, ref_side, field_x, in_match, start=None, timed=False):
        self.side, self.ref, self.fx, self.match = side, ref_side, field_x, in_match
        self.x, self.y, self.th = start or (250.0, 1000.0, 0.0)     # naša strana (koordinate taktike)
        self.timed = timed                                 # protivnik (plan E4): wait_until čeka u vremenu
        self.t = 0.0
        self.cmds = []
        self.started = False
        self.g = None                                      # globali taktike (za START)

    def begin(self):
        """Prva komanda: robot kreće sa START poze (u meču je ESP postavi na činč)."""
        if self.started:
            return
        self.started = True
        st = self.g.get("START") if self.g else None
        if isinstance(st, (tuple, list)) and len(st) >= 2:
            self.x, self.y = float(st[0]), float(st[1])
            self.th = float(st[2]) if len(st) > 2 else 0.0

    # koordinate: taktika -> teren (crtanje)
    def field_xy(self, x, y):
        return (self.fx - x, y) if self.side != self.ref else (x, y)

    def field_deg(self, d):
        return _wrap(180 - d) if self.side != self.ref else _wrap(d)

    def _line(self):
        f = sys._getframe(2)
        while f and f.f_code.co_filename != FILENAME:
            f = f.f_back
        return f.f_lineno if f else None

    def _add(self, kind, label, x0, y0, x1, y1, dt, **extra):
        if len(self.cmds) >= MAX_CMDS or self.t >= MAX_S:
            raise _Stop("skraćeno: više od %d komandi ili %d s" % (MAX_CMDS, MAX_S))
        a, b = self.field_xy(x0, y0), self.field_xy(x1, y1)
        self.cmds.append(dict(kind=kind, label=label, line=self._line(), t0=round(self.t, 2),
                              t1=round(self.t + dt, 2), x0=a[0], y0=a[1], x1=b[0], y1=b[1],
                              th=round(self.field_deg(self.th), 1), **extra))
        self.t += dt

    def _turn(self, deg):
        d = abs(_wrap(deg - self.th))
        self.th = _wrap(deg)
        return d / TURN_DPS

    def _drive(self, x, y, speed, reverse=False):
        dx, dy = x - self.x, y - self.y
        dist = math.hypot(dx, dy)
        dt = 0.0
        if dist > 20:
            head = math.degrees(math.atan2(dy, dx)) + (180 if reverse else 0)
            dt += self._turn(head)
        dt += dist / max(speed or 1000, 150) * 1.15 + (0.3 if dist > 0 else 0)
        self.x, self.y = x, y
        return dist, dt


def _module(fk):
    """Lažni tac: ista imena i potpisi kao ESP32/lib/tac.py (__all__), bez kretanja."""
    m = types.ModuleType("tac")

    def pose(x, y, deg=0):
        fk.begin()
        fk.x, fk.y, fk.th = float(x), float(y), float(deg)
        fk._add("pose", "POZA %d,%d" % (x, y), x, y, x, y, 0, target=list(fk.field_xy(x, y)) + [fk.field_deg(deg)])

    def goto(x, y, deg=None, reverse=False, speed=500, timeout=None, name=None, next=None):
        fk.begin()
        x0, y0 = fk.x, fk.y
        dist, dt = fk._drive(float(x), float(y), speed, reverse)
        if deg is not None:
            dt += fk._turn(float(deg))
        tgt = list(fk.field_xy(x, y)) + [None if deg is None else fk.field_deg(deg)]
        fk._add("goto", name or "GOTO %d,%d" % (x, y), x0, y0, x, y, dt, target=tgt)
        return True

    def turn_to(deg, timeout=5.0, name=None, next=None):
        fk.begin()
        dt = fk._turn(float(deg))
        fk._add("turn", name or "OKRET na %d" % deg, fk.x, fk.y, fk.x, fk.y, dt)
        return True

    def turn_by(deg, timeout=5.0, name=None, next=None):
        fk.begin()
        dt = fk._turn(fk.th + float(deg))
        fk._add("turn", name or "OKRET za %d" % deg, fk.x, fk.y, fk.x, fk.y, dt)
        return True

    def move(dist, speed=300, timeout=None, name=None, next=None):
        fk.begin()
        x0, y0 = fk.x, fk.y
        a = math.radians(fk.th)
        x1, y1 = x0 + dist * math.cos(a), y0 + dist * math.sin(a)
        dt = abs(dist) / max(speed or 1000, 150) * 1.15 + 0.3
        fk.x, fk.y = x1, y1
        fk._add("move", name or "MOVE %d" % dist, x0, y0, x1, y1, dt)
        return True

    def go_home(speed=600, name="KUCI", timeout=None):
        return goto(250, 1000, speed=speed, name=name)

    def actuator(name, value, wait=True, timeout=3.0, label=None, next=None):
        fk.begin()
        fk._add("act", label or "%s %s" % (name, value), fk.x, fk.y, fk.x, fk.y, 0.3 if wait else 0)
        return True if wait else (0, label or str(name))

    def wait(s):
        fk.begin()
        fk._add("wait", "pauza %.1f s" % s, fk.x, fk.y, fk.x, fk.y, float(s))

    def wait_until(cond, timeout, name=None):
        if not fk.timed:
            return True                                     # nacrt: sve uspeva odmah
        fk.begin()
        t_end = fk.t + timeout                              # protivnik: vreme teče dok uslov ne bude ispunjen
        while fk.t < t_end:
            if cond():
                return True
            fk.t += 0.05
            if fk.t >= MAX_S:
                raise _Stop("kraj meča")
        return False

    def done(h):
        return True

    def wait_done(h, timeout=3.0):
        return True

    def step(name, next=None):
        pass

    def log(text):
        pass

    def status():
        fk.begin()
        fx, fy = fk.field_xy(fk.x, fk.y)
        return {"x": int(fx), "y": int(fy), "theta": int(fk.field_deg(fk.th) * 100), "v": 0, "state": 0,
                "match_ms": int(fk.t * 1000)}

    def here(max_age_ms=300):
        fk.begin()
        return (int(fk.x), int(fk.y), int(fk.th))

    def remaining():
        return max(0.0, 100.0 - fk.t) if fk.match else None

    def match_time():
        return fk.t if fk.match else None

    def in_match():
        return fk.match

    def attack_phase():
        return fk.match and fk.t >= 85

    def deadline(s):
        pass

    def side():
        return fk.side

    def ir_off(*names):
        fk._add("ir", "IR off " + (" ".join(names) or "sve"), fk.x, fk.y, fk.x, fk.y, 0)
        return True

    def ir_on(*names):
        fk._add("ir", "IR on " + (" ".join(names) or "sve"), fk.x, fk.y, fk.x, fk.y, 0)
        return True

    def ir_sees(*names):
        return False

    for k, v in list(locals().items()):
        if callable(v) and not k.startswith("_"):
            setattr(m, k, v)
    m.rotate = turn_to
    m.TimeUp, m.Abort = TimeUp, Abort
    m.REF_SIDE, m.FIELD_X, m.HOME = fk.ref, fk.fx, (250, 1000)
    m.MIN_SPEED, m.MAX_SPEED = 150, 1500
    m.__all__ = tuple(n for n in dir(m) if not n.startswith("_") and n not in ("REF_SIDE", "FIELD_X", "HOME",
                                                                                 "MIN_SPEED", "MAX_SPEED"))
    return m


def preview(source, side="zuta", ref_side="zuta", field_x=field.W, mode="mec", start=None, timed=False):
    """{"cmds": [...], "start": [x, y, ugao] (teren), "t": procena s, "error": None | {line, msg},
    "truncated": None | razlog}. Ne baca izuzetke."""
    fk = _Fake(side, ref_side, field_x, mode == "mec", start=start, timed=timed)
    out = {"cmds": fk.cmds, "start": None, "t": 0.0, "error": None, "truncated": None}
    try:
        code = compile(source, FILENAME, "exec")
    except SyntaxError as e:
        out["error"] = {"line": e.lineno or 1, "msg": "sintaksa: %s" % e.msg}
        return out
    g = {"__name__": "__taktika__"}
    lines = [0]

    def tracer(frame, event, arg):
        if frame.f_code.co_filename != FILENAME:
            return None
        if event == "line":
            lines[0] += 1
            if lines[0] > MAX_LINES:
                raise _Stop("skraćeno: petlja bez komande (više od %d redova)" % MAX_LINES)
        return tracer

    fk.g = g
    with _lock:
        old = sys.modules.get("tac"), sys.modules.get("gambit")
        sys.modules["tac"] = sys.modules["gambit"] = _module(fk)       # Gambit Micro: oba imena
        try:
            sys.settrace(tracer)
            exec(code, g)
        except _Stop as e:
            out["truncated"] = str(e)
        except (TimeUp, Abort):
            pass
        except Exception as e:                                  # noqa: BLE001 (greška u taktici: prikaži red)
            tb, line = e.__traceback__, None
            while tb:
                if tb.tb_frame.f_code.co_filename == FILENAME:
                    line = tb.tb_lineno
                tb = tb.tb_next
            out["error"] = {"line": line or 1, "msg": "%s: %s" % (type(e).__name__, e)}
        finally:
            sys.settrace(None)
            for name, mod in zip(("tac", "gambit"), old):
                if mod is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = mod
    st = g.get("START")
    if isinstance(st, (tuple, list)) and len(st) >= 2:
        sx, sy = fk.field_xy(float(st[0]), float(st[1]))
        out["start"] = [sx, sy, fk.field_deg(float(st[2]) if len(st) > 2 else 0.0)]
    out["t"] = round(fk.t, 2)
    return out
