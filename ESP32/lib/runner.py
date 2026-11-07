# Glavna petlja (Loop) i izvršavanje taktike (run_tactic).
#
# Loop.step() je jedan krug: svaki servis dobije poll(), pa kratka pauza. Taktika zove step()
# dok čeka (tac.py), pa ekran, heartbeat i WiFi rade i tokom taktike. Ugnežđeni poziv step()
# (npr. iz callback-a koji je pozvan iz step()) se preskače.
# Meri se najduže trajanje svake faze (ms) u poslednjoj sekundi: app.loop.max, ekran VEZA, upload STAT.
from compat import ticks_ms, ticks_us, ticks_diff
import tactic
from tactic import tracker
import tac


class Loop:
    def __init__(self, services, sleep_ms, pause_ms=5):
        self.services, self.sleep_ms, self.pause_ms = services, sleep_ms, pause_ms
        self.max = {}                   # faza -> najduže trajanje u prethodnoj sekundi (ms)
        self.step_max = 0               # najduži ceo krug u prethodnoj sekundi (ms)
        self._cur, self._cur_step = {}, 0
        self._t_reset = ticks_ms()
        self._in = False

    def step(self):
        if self._in:
            return
        self._in = True
        try:
            t0 = ticks_us()
            for name, fn in self.services:
                t = ticks_us()
                fn()
                d = ticks_diff(ticks_us(), t) // 1000
                if d > self._cur.get(name, 0):
                    self._cur[name] = d
            d = ticks_diff(ticks_us(), t0) // 1000
            if d > self._cur_step:
                self._cur_step = d
            if ticks_diff(ticks_ms(), self._t_reset) >= 1000:
                self.max, self.step_max = self._cur, self._cur_step
                self._cur, self._cur_step = {}, 0
                self._t_reset = ticks_ms()
        finally:
            self._in = False
        self.sleep_ms(self.pause_ms)

    def slowest(self):
        """(faza, ms) najsporije faze u prethodnoj sekundi."""
        if not self.max:
            return ("-", 0)
        k = max(self.max, key=lambda n: self.max[n])
        return (k, self.max[k])


_code = {}                              # ime -> (veličina, vreme izmene, prevedeni kod)


def _compiled(name):
    """Prevedena taktika; ponovo se prevodi samo kad se fajl promeni (prevođenje na ESP-u traje)."""
    import os
    path = "%s/%s.py" % (tactic.TACTICS_DIR, name)
    st = os.stat(path)
    key = (st[6], st[8])
    c = _code.get(name)
    if c and c[0] == key:
        return c[1]
    with open(path) as f:
        src = f.read()
    try:
        code = compile(src, name, "exec")
    except NameError:                   # firmver bez compile(): izvrši tekst
        code = src
    _code[name] = (key, code)
    return code


def run_tactic(app, name):
    """Izvrši /tactics/<name>.py za stranu app.side. Svaka greška ili prekid: STOP robotu, dnevnik."""
    import match
    app.running, app.abort = name, None
    tac.current_side = app.side
    tracker.start(name, total=match.read_meta(name).get("TOTAL"))
    app.on_tactic_start(name)
    app.tlog("START %s (%s)" % (name, app.side))
    t0 = ticks_ms()
    try:
        app.last = (name, app.side)
        exec(_compiled(name), {"__name__": "taktika"})
        tracker.finish()
        app.tlog("KRAJ %s %.1fs" % (name, ticks_diff(ticks_ms(), t0) / 1000))
        app.on_tactic_end(name, None)
    except KeyboardInterrupt:
        _stop(app, "Ctrl+C")
        app.on_tactic_end(name, "Ctrl+C")
        raise
    except tac.Abort as e:
        _stop(app, "PREKID: %s" % e)
        app.on_tactic_end(name, str(e))
    except BaseException as e:          # i SystemExit iz taktike: ne sme da ugasi main.py
        _stop(app, "GRESKA: %r" % (e,))
        app.error("taktika: %s" % type(e).__name__)
        app.on_tactic_end(name, "greska %s" % type(e).__name__)
    finally:
        app.running = None
        app.request = None


def _stop(app, why):
    try:
        app.robot.send("STOP")
    except Exception:
        pass
    if tracker.step_name:
        tracker.fail(why.split(":")[0])
    tracker.finish()
    app.tlog(why)
