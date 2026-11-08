# API za taktike (fajlovi u /tactics). Taktika je običan skript:
#
#   from tac import *
#   START = (250, 1000, 0)            # startna poza (za meč: postavlja se kad se izvuče činč)
#   TOTAL = 4                         # koliko koraka ima (za ekran "3/4"), može i bez
#   if not goto(600, 1000, speed=300, next="okret"):
#       move(-100)                     # npr. prepreka: malo nazad
#   turn_to(90)                        # apsolutni ugao terena
#   turn_by(-45)                       # relativno od trenutnog
#   actuator("hvataljka", 1)           # čeka DONE sa STM32 (imena u config.ACTUATORS)
#   h = actuator("lift", 300, wait=False); goto(...); wait_done(h)   # paralelno sa vožnjom
#
# Jedinice: mm, stepeni (0° = +x, pozitivno = levo), mm/s, sekunde.
# Strana terena: taktika se piše za REF_SIDE ("zuta", leva strana stola, x 0..500 po pravilima 2027). Na drugoj strani se sve koordinate same
# ogledaju (x -> 3000 - x, ugao -> 180° - ugao, relativni okret menja smer).
# goto/turn_to/turn_by/move vraćaju True (DONE) ili False (FAIL, nema odgovora, isteklo vreme).
# Dok taktika čeka, glavna petlja radi dalje (ekran, PING, WiFi); taster STOP ili
# `tools/tactic.py` Ctrl+C prekidaju taktiku i šalju STOP.
from compat import ticks_ms, ticks_diff
import protocol as P
from tactic import tracker

__all__ = ("pose", "goto", "turn_to", "turn_by", "rotate", "move", "wait", "wait_until", "step",
           "actuator", "done", "wait_done", "log", "status", "here", "remaining", "side", "Abort")

FIELD_X = 3000                 # mm, dužina terena (ogledanje po x)
REF_SIDE = "zuta"              # strana za koju se taktike pišu (pravila 2027: žuta startna zona x 0..500)
SIDES = ("plava", "zuta")
MIN_SPEED = 150                # regulacija na STM32 ne ide sporije (mm/s)

app = None                     # postavlja main.py
current_side = REF_SIDE        # postavlja runner pre pokretanja taktike


class Abort(BaseException):
    """Prekid taktike (STOP, kraj meča, nema STM32). BaseException, da ga `except Exception:`
    u taktici ne bi slučajno progutao: posle STOP-a taktika mora da stane."""
    pass


# ---------------- strana terena ----------------

def _mirrored():
    return current_side != REF_SIDE


def _wrap(deg):
    while deg > 180:
        deg -= 360
    while deg <= -180:
        deg += 360
    return deg


def mirror_xy(x, y):
    return (FIELD_X - x, y) if _mirrored() else (x, y)


def mirror_deg(deg):
    return _wrap(180 - deg) if _mirrored() else deg


def side():
    return current_side


# ---------------- osnovno ----------------

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


def wait_until(cond, timeout, name=None):
    """Čekaj dok cond() ne bude True, najviše timeout sekundi. Vraća True ako je dočekano."""
    if name:
        tracker.step(name, timeout)
    t0 = ticks_ms()
    while ticks_diff(ticks_ms(), t0) < timeout * 1000:
        if cond():
            if name:
                tracker.ok()
            return True
        _pump()
    if name:
        tracker.fail("TIMEOUT")
    return False


def step(name, next=None):
    """Korak bez komande, samo za ekran (npr. 'čekam protivnika'). Zatvara ga sledeći korak."""
    tracker.step(name, None, next)


def status():
    """Poslednji STATUS (sirovo, koordinate terena): dict x, y, theta (cdeg), v, state, match_ms."""
    return app.robot.status


def here(max_age_ms=300):
    """(x, y, ugao) robota u koordinatama naše strane, iz STATUS-a koji nije stariji od max_age_ms."""
    t0 = ticks_ms()
    while True:
        r = app.robot
        age = r.status_age()
        if r.status and age is not None and age <= max_age_ms:
            s = r.status
            x, y = mirror_xy(s["x"], s["y"])
            return x, y, mirror_deg(s["theta"] / 100)
        if ticks_diff(ticks_ms(), t0) > 1000:
            raise Abort("nema svežeg STATUS-a")
        _pump()


def remaining():
    """Preostalo vreme meča u sekundama, ili None ako meč ne traje. U meču po ESP satu (od činča), jer
    STM32 posle restarta broji ispočetka."""
    m = getattr(app, "match", None)
    if m is not None and m.t_cord is not None and m.state in ("MEC", "KRAJ"):
        return max(0, 100 - m.elapsed() / 1000)
    s = app.robot.status
    if not s or not (s["state"] & P.State.MATCH_RUNNING):
        return None
    return max(0, 100 - s["match_ms"] / 1000)


def _robot():
    t0 = ticks_ms()
    m = getattr(app, "match", None)
    while not app.robot.ok or (m is not None and m.restoring()):
        _pump()                         # i dok se posle restarta STM32 vraća poza (match.py)
        if ticks_diff(ticks_ms(), t0) > 2000:
            raise Abort("STM32 se ne javlja")
    return app.robot


def _stop_and_wait(r, ms=300):
    """STOP i čekanje njegovog ACK-a (najviše ms), da robot sigurno stoji pre sledećeg koraka."""
    seq = r.send("STOP")
    t0 = ticks_ms()
    while ticks_diff(ticks_ms(), t0) < ms:
        app.pump()
        if any(s == seq and kind == "ok" for s, _, kind, _ in app.events):
            return True
    return False


def _cmd(name, label, timeout, next, motion, long=None, **f):
    """motion: kretanje (STOP kad nema odgovora, kraj i po STATUS-u). long: posle ACK čeka DONE."""
    long = motion if long is None else long
    r = _robot()
    m = getattr(app, "match", None)
    resets = m.stm_resets if m is not None else 0
    tracker.step(label, timeout, next)
    seq = r.send(name, **f)
    t0 = ticks_ms()
    acked = moving_seen = False
    quiet = 0                          # STATUS-a zaredom bez MOVING posle MOVING
    last_n = r.status_n
    while ticks_diff(ticks_ms(), t0) < timeout * 1000:
        _pump()
        if m is not None and m.stm_resets != resets:
            tracker.fail("RESTART")         # STM32 restartovan: komanda je izgubljena, poza vraćena
            log("%s: STM32 restart, komanda prekinuta" % label)
            return False
        for s, _, kind, reason in app.events:
            if s != seq:
                continue
            if kind == "ok" and long:
                acked = True
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
        # P-2: DONE/FAIL može da se izgubi (CRC). Protokol v3: STATUS nosi seq i ishod poslednje završene
        # komande kretanja, pa se tačan ishod zna iz sledećeg STATUS-a (50 ms).
        # Stariji STM32 (v1/v2): procena po bitu MOVING (3 STATUS-a bez MOVING posle MOVING); ona ne zna
        # da li je kretanje uspelo ili prekinuto (izgubljen FAIL), pa se tako i javlja.
        if motion and acked and r.status_n != last_n and r.status:
            last_n = r.status_n
            st = r.status
            if st.get("last_seq") == seq:
                res = st.get("last_result")
                if res == 0:
                    tracker.ok()
                    log("%s: OK po STATUS-u (DONE nije stigao)" % label)
                    return True
                why = _REASONS.get(res, str(res))
                tracker.fail(why)
                log("%s: %s po STATUS-u (FAIL nije stigao)" % (label, why))
                return False
            if st.get("last_seq") is not None:
                continue
            if st["state"] & P.State.MOVING:
                moving_seen, quiet = True, 0
            elif moving_seen:
                quiet += 1
                if quiet >= 3:
                    tracker.ok()
                    log("%s: kraj po STATUS-u, ishod nepoznat (stari STM32 bez v3)" % label)
                    return True
    _stop_and_wait(r)
    tracker.fail("TIMEOUT")
    log("%s: isteklo %.0fs, STOP" % (label, timeout))
    return False


_REASONS = {getattr(P.Reason, k): k for k in dir(P.Reason) if not k.startswith("_")}


def _drive_timeout(dist, speed):
    """Procena: put / brzina * 1.5 + 2 s (ubrzanje, okret na početku)."""
    return abs(dist) / max(speed, MIN_SPEED) * 1.5 + 2.0


# ---------------- komande ----------------

def pose(x, y, deg=0):
    """Postavi pozu robota (koordinate naše strane)."""
    mx, my = mirror_xy(x, y)
    return _cmd("SET_POSE", "POZA %d,%d" % (x, y), 1.0, None, False,
                x=int(mx), y=int(my), theta=int(mirror_deg(deg) * 100))


def goto(x, y, deg=None, reverse=False, speed=500, timeout=None, name=None, next=None):
    """Idi na x, y (naša strana). deg = završni ugao (None = ostani kako je stigao)."""
    if timeout is None:
        hx, hy, _ = here()
        timeout = _drive_timeout(((x - hx) ** 2 + (y - hy) ** 2) ** 0.5, speed)
    mx, my = mirror_xy(x, y)
    flags = (P.GotoFlags.REVERSE if reverse else 0) | (P.GotoFlags.NO_THETA if deg is None else 0)
    th = int(mirror_deg(deg) * 100) if deg is not None else 0
    return _cmd("GOTO", name or "GOTO %d,%d" % (x, y), timeout, next, True,
                x=int(mx), y=int(my), theta=th, flags=flags, max_speed=speed)


def turn_to(deg, timeout=5.0, name=None, next=None):
    """Okreni se na apsolutni ugao terena (naša strana)."""
    return _cmd("ROTATE", name or "OKRET na %d" % deg, timeout, next, True,
                theta=int(_wrap(mirror_deg(deg)) * 100))


def turn_by(deg, timeout=5.0, name=None, next=None):
    """Okreni se za deg od trenutnog ugla (pozitivno = levo na našoj strani)."""
    _, _, h = here()
    return turn_to(_wrap(h + deg), timeout, name or "OKRET za %d" % deg, next)


rotate = turn_to               # staro ime (apsolutni ugao)


def _actuator_id(name):
    import config as cfg
    if isinstance(name, int):
        return name, str(name)
    if _mirrored():
        name = getattr(cfg, "ACTUATOR_MIRROR", {}).get(name, name)
    try:
        return cfg.ACTUATORS[name], name
    except (AttributeError, KeyError):
        raise Abort("nepoznat aktuator: %s" % name)


def actuator(name, value, wait=True, timeout=3.0, label=None, next=None):
    """Aktuator na STM32 (ime iz config.ACTUATORS ili broj). wait=True: čeka DONE, vraća True/False.
    wait=False: pošalje i odmah vrati oznaku za done()/wait_done() (radi paralelno sa vožnjom)."""
    aid, nm = _actuator_id(name)
    label = label or "%s %d" % (nm, value)
    if wait:
        return _cmd("ACTUATOR", label, timeout, next, False, long=True, id=aid, value=value)
    seq = _robot().send("ACTUATOR", id=aid, value=value)
    log("%s: poslato" % label)
    return (seq, label)


def done(h):
    """Ishod aktuatora pokrenutog sa wait=False: None (još radi), True (DONE) ili False (FAIL)."""
    res = app.robot.results.get(h[0])
    if res is None:
        return None
    return res[0] == "done"


def wait_done(h, timeout=3.0):
    """Sačekaj aktuator pokrenut sa wait=False. True = DONE."""
    seq, label = h
    tracker.step(label, timeout)
    t0 = ticks_ms()
    while ticks_diff(ticks_ms(), t0) < timeout * 1000:
        r = done(h)
        if r is not None:
            res = app.robot.results[seq]
            if r:
                tracker.ok()
            else:
                tracker.fail(res[1] or res[0])
            log("%s: %s" % (label, "OK" if r else res[1] or res[0]))
            return r
        _pump()
    tracker.fail("TIMEOUT")
    log("%s: isteklo %.0fs" % (label, timeout))
    return False


def move(dist, speed=300, timeout=None, name=None, next=None):
    """Pravo napred (dist > 0) ili nazad (dist < 0), u mm."""
    if timeout is None:
        timeout = _drive_timeout(dist, speed)
    return _cmd("MOVE", name or "MOVE %d" % dist, timeout, next, True, dist=dist, max_speed=speed)
