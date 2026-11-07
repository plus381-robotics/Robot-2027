# API za taktike (fajlovi u /tactics). Taktika je običan skript:
#
#   from tac import *
#   pose(250, 1000, 0)
#   if not goto(600, 1000, speed=300, next="okret 90"):
#       move(-100)                     # npr. prepreka: malo nazad
#   rotate(90)
#
# Jedinice: mm, stepeni (0° = +x, pozitivno = levo), mm/s, sekunde.
# goto/rotate/move vraćaju True (DONE) ili False (FAIL, nema odgovora, isteklo vreme).
# Dok taktika čeka, glavna petlja radi dalje (ekran, PING, WiFi); taster STOP ili
# `tools/tactic.py` Ctrl+C prekidaju taktiku i šalju STOP.
from compat import ticks_ms, ticks_diff
import protocol as P
from tactic import tracker

app = None          # postavlja main.py


class Abort(Exception):
    pass


def _pump():
    app.pump()                         # jedan krug glavne petlje
    if app.abort:
        raise Abort(app.abort)


def log(text):
    app.tlog(str(text))


def wait(s):
    t0 = ticks_ms()
    while ticks_diff(ticks_ms(), t0) < s * 1000:
        _pump()


def _robot():
    t0 = ticks_ms()
    while not app.robot.ok:
        _pump()
        if ticks_diff(ticks_ms(), t0) > 2000:
            raise Abort("STM32 se ne javlja")
    return app.robot


def _cmd(name, label, timeout, next, motion, **f):
    r = _robot()
    tracker.step(label, timeout, next)
    seq = r.send(name, **f)
    t0 = ticks_ms()
    while ticks_diff(ticks_ms(), t0) < timeout * 1000:
        _pump()
        for s, _, kind, reason in app.events:
            if s != seq or (kind == "ok" and motion):
                continue
            if kind in ("ok", "done"):
                tracker.ok()
                log("%s: OK %.1fs" % (label, ticks_diff(ticks_ms(), t0) / 1000))
                return True
            if kind == "timeout" and motion and reason != "SUPERSEDED":
                _stop_and_wait(r)       # STM32 je komandu možda primio, a izgubljeni su samo ACK-ovi
            tracker.fail(reason or kind)
            log("%s: %s" % (label, reason or kind))
            return False
    _stop_and_wait(r)
    tracker.fail("TIMEOUT")
    log("%s: isteklo %.0fs, STOP" % (label, timeout))
    return False


def _stop_and_wait(r, ms=300):
    """STOP i čekanje njegovog ACK-a (najviše ms), da robot sigurno stoji pre sledećeg koraka."""
    seq = r.send("STOP")
    t0 = ticks_ms()
    while ticks_diff(ticks_ms(), t0) < ms:
        app.pump()
        if any(s == seq and kind == "ok" for s, _, kind, _ in app.events):
            return True
    return False


def pose(x, y, deg=0):
    return _cmd("SET_POSE", "POZA %d,%d" % (x, y), 1.0, None, False, x=x, y=y, theta=int(deg * 100))


def goto(x, y, deg=None, reverse=False, speed=500, timeout=10.0, name=None, next=None):
    flags = (P.GotoFlags.REVERSE if reverse else 0) | (P.GotoFlags.NO_THETA if deg is None else 0)
    return _cmd("GOTO", name or "GOTO %d,%d" % (x, y), timeout, next, True,
                x=x, y=y, theta=int((deg or 0) * 100), flags=flags, max_speed=speed)


def rotate(deg, timeout=5.0, name=None, next=None):
    return _cmd("ROTATE", name or "ROTATE %d" % deg, timeout, next, True, theta=int(deg * 100))


def move(dist, speed=300, timeout=10.0, name=None, next=None):
    return _cmd("MOVE", name or "MOVE %d" % dist, timeout, next, True, dist=dist, max_speed=speed)


def status():
    """Poslednji STATUS: dict x, y, theta (cdeg), v, state, match_ms."""
    return app.robot.status
