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
# Vreme meča (pravila 2027: 100 s, faza napada od 85. s, robot na kraju u svojoj zoni):
#   remaining(), match_time(), in_match(), attack_phase()   # u testu se vreme broji od starta taktike
#   deadline(12)                       # kad ostane 12 s: tekuća komanda staje i baca TimeUp
#   try:
#       ...                            # glavni posao
#   except TimeUp:
#       go_home()                      # centar svoje startne zone
# Restart ESP-a usred meča: ako postoji <taktika>_obnova.py, ESP posle restarta pokreće nju (npr. go_home()).
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
           "actuator", "done", "wait_done", "log", "status", "here", "remaining", "side", "Abort",
           "match_time", "in_match", "attack_phase", "deadline", "go_home", "TimeUp")

FIELD_X = 3000                 # mm, dužina terena (ogledanje po x)
REF_SIDE = "zuta"              # strana za koju se taktike pišu (pravila 2027: žuta startna zona x 0..500)
SIDES = ("plava", "zuta")
MIN_SPEED = 150                # regulacija na STM32 ne ide sporije (mm/s)
MAX_SPEED = 1500               # ni brže (BlackPill V_MAX; novi robot ~1200)
MATCH_S = 100
ATTACK_S = 85                  # pravila 2027 (E.4): faza napada od 85. s
HOME = (250, 1000)             # centar startne zone ("throne room") za REF_SIDE (pravila 2027: x 0..500, y 750..1250)

app = None                     # postavlja main.py
current_side = REF_SIDE        # postavlja runner pre pokretanja taktike


class Abort(BaseException):
    """Prekid taktike (STOP, kraj meča, nema STM32). BaseException, da ga `except Exception:`
    u taktici ne bi slučajno progutao: posle STOP-a taktika mora da stane."""
    pass


class TimeUp(Exception):
    """Isteklo vreme zadato sa deadline(): tekuća komanda je zaustavljena. Taktika ga hvata
    (`except TimeUp: go_home()`); posle toga deadline više ne važi."""
    pass


_deadline = None               # deadline(s): sekunde do kraja meča kad se baca TimeUp


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
    global _deadline
    app.pump()                         # jedan krug glavne petlje
    if app.abort:
        raise Abort(app.abort)
    if _deadline is not None:
        rem = remaining()
        if rem is not None and rem <= _deadline:
            _deadline = None           # jednom; posle toga se vozi kući bez prekida
            raise TimeUp("ostalo %.1f s" % rem)


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


def match_time():
    """Sekunde od početka meča (ESP sat od činča). U testu: od starta taktike, kao da je meč, pa se taktika
    ponaša isto. None ako ništa ne radi."""
    m = getattr(app, "match", None)
    if m is not None and m.t_cord is not None and m.state in ("MEC", "KRAJ"):
        return m.elapsed() / 1000
    s = app.robot.status
    if s and s["state"] & P.State.MATCH_OVER:
        return MATCH_S
    if s and s["state"] & P.State.MATCH_RUNNING:
        return s["match_ms"] / 1000
    if tracker.running:
        return ticks_diff(ticks_ms(), tracker.t_start) / 1000
    return None


def remaining():
    """Preostalo vreme meča u sekundama (0 posle kraja). U meču po ESP satu (od činča), jer STM32 posle
    restarta broji ispočetka; u testu od starta taktike (100 s). None ako ništa ne radi."""
    t = match_time()
    return None if t is None else max(0, MATCH_S - t)


def in_match():
    """True u pravom meču (činč), False u testu."""
    m = getattr(app, "match", None)
    return bool(m is not None and m.t_cord is not None and m.state in ("MEC", "KRAJ"))


def attack_phase():
    """Faza napada (pravila 2027: od 85. s do kraja)."""
    t = match_time()
    return t is not None and t >= ATTACK_S


def deadline(s):
    """Kad do kraja meča ostane s sekundi, tekuća komanda (goto, move, wait...) staje i baca TimeUp.
    deadline(None) isključuje."""
    global _deadline
    _deadline = s


def _robot():
    """Robot spreman za komandu. Van meča čeka najviše 2 s; u meču čeka povratak veze (labav konektor) do
    kraja meča, pa taktika nastavlja od sledećeg koraka umesto da se prekine (L17)."""
    t0 = ticks_ms()
    m = getattr(app, "match", None)
    said = False
    while not app.robot.ok or (m is not None and m.restoring()):
        _pump()                         # i dok se posle restarta STM32 vraća poza (match.py)
        waited = ticks_diff(ticks_ms(), t0)
        if waited > 2000:
            if not in_match():
                raise Abort("STM32 se ne javlja")
            if not said:
                said = True
                log("nema veze sa STM32: cekam")
    if said:
        log("veza sa STM32 je tu: nastavljam")
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
    try:
        return _cmd_wait(r, name, label, timeout, motion, long, m, resets, seq_box=r.send(name, **f))
    except TimeUp:
        if motion:
            _stop_and_wait(r)           # vreme je isteklo usred kretanja: robot staje
        tracker.fail("VREME")
        log("%s: prekinuto (deadline)" % label)
        raise


def _cmd_wait(r, name, label, timeout, motion, long, m, resets, seq_box):
    seq = seq_box
    t0 = ticks_ms()
    acked = moving_seen = False
    quiet = 0                          # STATUS-a zaredom bez MOVING posle MOVING
    last_n = r.status_n
    lost = None                         # od kada nema veze sa STM32 (L17)
    while ticks_diff(ticks_ms(), t0) < timeout * 1000:
        _pump()
        if not r.alive:
            lost = lost or ticks_ms()
            if ticks_diff(ticks_ms(), lost) > 300:
                tracker.fail("VEZA")    # STM32 staje posle 500 ms bez PING-a; ishod se ne pogađa po STATUS-u
                log("%s: nema veze sa STM32" % label)
                return False
        else:
            lost = None
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
            if reason == "MATCH_OVER":
                tracker.fail("KRAJ")
                raise Abort("kraj meca")        # L9: odmah kraj, bez još jedne komande koja bi pala
            if kind == "timeout" and motion and reason != "SUPERSEDED":
                _stop_and_wait(r)       # STM32 je komandu možda primio, a izgubljeni su samo ACK-ovi
            tracker.fail(reason or kind)
            log("%s: %s" % (label, _reason(reason or kind)))
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


def _reason(r):
    """Razlog kao na ekranu ("prepreka", "kraj meca"...), da dnevnik i traka grešaka pišu isto (L25)."""
    import tekst
    return tekst.reason(r)


def _drive_timeout(dist, speed):
    """Procena: put / brzina * 1.5 + 2 s (ubrzanje, okret na početku)."""
    return abs(dist) / max(speed, MIN_SPEED) * 1.5 + 2.0


def _speed(speed):
    """mm/s za STM32: ceo broj u opsegu MIN_SPEED..MAX_SPEED (0 bi na STM32 značilo 1 m/s)."""
    if speed <= 0:
        raise ValueError("speed mora biti > 0 (mm/s)")
    return int(round(max(MIN_SPEED, min(MAX_SPEED, speed))))


def _cdeg(deg):
    """Stepeni -> stotinke stepena za protokol, uvek u -180..180."""
    return int(round(_wrap(deg) * 100))


# ---------------- komande ----------------

def pose(x, y, deg=0):
    """Postavi pozu robota (koordinate naše strane)."""
    mx, my = mirror_xy(x, y)
    return _cmd("SET_POSE", "POZA %d,%d" % (x, y), 1.0, None, False,
                x=int(round(mx)), y=int(round(my)), theta=_cdeg(mirror_deg(deg)))


def goto(x, y, deg=None, reverse=False, speed=500, timeout=None, name=None, next=None):
    """Idi na x, y (naša strana). deg = završni ugao (None = ostani kako je stigao)."""
    speed = _speed(speed)
    if timeout is None:
        hx, hy, _ = here()
        timeout = _drive_timeout(((x - hx) ** 2 + (y - hy) ** 2) ** 0.5, speed)
    mx, my = mirror_xy(x, y)
    flags = (P.GotoFlags.REVERSE if reverse else 0) | (P.GotoFlags.NO_THETA if deg is None else 0)
    th = _cdeg(mirror_deg(deg)) if deg is not None else 0
    return _cmd("GOTO", name or "GOTO %d,%d" % (x, y), timeout, next, True,
                x=int(round(mx)), y=int(round(my)), theta=th, flags=flags, max_speed=speed)


def turn_to(deg, timeout=5.0, name=None, next=None):
    """Okreni se na apsolutni ugao terena (naša strana)."""
    return _cmd("ROTATE", name or "OKRET na %d" % deg, timeout, next, True,
                theta=_cdeg(mirror_deg(deg)))


def turn_by(deg, timeout=5.0, name=None, next=None):
    """Okreni se za deg od trenutnog ugla (pozitivno = levo na našoj strani). Više od 170° (npr. 270, 360)
    ide u više okreta, da smer bude tačno onaj koji je zadat (jedan okret uvek ide kraćim putem)."""
    _, _, h = here()
    n = int(abs(deg) // 170) + 1 if abs(deg) > 170 else 1
    ok = True
    for k in range(1, n + 1):
        lb = name or ("OKRET za %d" % deg if n == 1 else "OKRET za %d (%d/%d)" % (deg, k, n))
        ok = turn_to(_wrap(h + deg * k / n), timeout, lb, next if k == n else None) and ok
        if not ok:
            break
    return ok


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
    r = _robot()
    seq = r.send("ACTUATOR", id=aid, value=value)
    # Sačekaj ACK (najviše ~200 ms) pre povratka: sledeća komanda bi inače potisnula ponavljanje ovog okvira,
    # pa izgubljen okvir aktuatora ne bi bio ponovljen (pregled logike L15).
    t0 = ticks_ms()
    while ticks_diff(ticks_ms(), t0) < 200:
        _pump()
        ev = [(k, why) for s2, _, k, why in app.events if s2 == seq]
        if ev:
            k, why = ev[0]
            if k in ("fail", "timeout"):
                log("%s: %s" % (label, why or k))
            break
    else:
        log("%s: nema ACK" % label)
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
    speed = _speed(speed)
    dist = int(round(dist))
    if timeout is None:
        timeout = _drive_timeout(dist, speed)
    return _cmd("MOVE", name or "MOVE %d" % dist, timeout, next, True, dist=dist, max_speed=speed)


def go_home(speed=600, name="KUCI", timeout=None):
    """Vozi do centra svoje startne zone (pravila 2027: robot na kraju meča u zoni = 5/10 poena)."""
    return goto(HOME[0], HOME[1], speed=speed, name=name, timeout=timeout)
