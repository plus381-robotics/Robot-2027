# Pravi ESP kod (ESP32/lib) u CPython-u, sastavljen kao u ESP32/main.py, ali sa simuliranim STM32
# umesto UART-a i bez WiFi-ja (net, upload, telem). Ništa iz ESP32/ se ne kopira niti menja.
#
# ESP moduli imaju globalno stanje (compat.fake, tac.app, tactic.tracker...), pa se pre svake
# simulacije izbacuju iz sys.modules i uvoze ispočetka. Jedna simulacija u isto vreme po procesu
# (server ih zato pokreće u posebnim procesima).
import pathlib
import sys

from . import paths

EPOCH_MS = 10000                 # virtuelni sat kreće od ovoga (0 bi ESP kod mogao da shvati kao "nije postavljeno")


def _esp_dirs():
    return [paths.ESP / "sim", paths.ESP, paths.ESP / "lib"]


def _esp_module_names():
    names = set()
    for d in _esp_dirs():
        for f in d.glob("*.py"):
            names.add(f.stem)
    return names


def micropython_shims():
    """Funkcije koje postoje samo u MicroPython-u, a ESP kod ih zove (npr. upload STAT -> gc.mem_free).
    Samo u procesu simulacije; vrednosti su izmišljene (simulator nema ESP memoriju)."""
    import gc
    if not hasattr(gc, "mem_free"):
        gc.mem_free = lambda: 100 * 1024
        gc.mem_alloc = lambda: 60 * 1024
    if not hasattr(gc, "threshold"):
        gc.threshold = lambda *a: -1


def fresh_import():
    """Izbaci ESP module iz sys.modules i stavi ESP putanje na početak sys.path (kao conftest.py)."""
    micropython_shims()
    for n in _esp_module_names():
        sys.modules.pop(n, None)
    for d in reversed(_esp_dirs()):
        s = str(d)
        while s in sys.path:
            sys.path.remove(s)
        sys.path.insert(0, s)


class Esp:
    """ESP strana: App, Robot, Loop, tac, kao na robotu. stm = UART objekat (SimSTM)."""

    def __init__(self, make_stm, tactics_dir, workdir, screen=False, loop_extra_ms=5, inputs=False):
        fresh_import()
        import compat
        compat.fake = [EPOCH_MS]
        self.compat = compat
        import state
        state.MODE, state.SSID, state.IP = None, None, None
        import tactic
        import tac
        import app as appmod
        from robot import Robot
        from settings import Settings
        from app import App
        from runner import Loop, run_tactic
        tactic.tracker.__init__()
        tactic.TACTICS_DIR = str(tactics_dir)
        workdir = pathlib.Path(workdir)
        (workdir / "mec").mkdir(parents=True, exist_ok=True)
        appmod.MEC_DIR = str(workdir / "mec")
        self.stm = make_stm(compat.ticks_ms)
        fb = None
        if screen:
            import ssd1306
            fb = ssd1306.SSD1306_I2C(128, 64)
        self.app = App(Robot(self.stm), Settings(str(workdir / "settings.json")), fb)
        self.fb = fb
        self.tracker = tactic.tracker
        self.tac = tac
        self.run_tactic = run_tactic
        self.services = []                       # dodatni servisi simulatora (snimanje, scenario)
        self.inputs = None
        services = [("robot", self.app.update)]
        if inputs:
            # pravi inputs.py (enkoder i tasteri) nad lažnim pinovima; isto kao handle_inputs u main.py
            import config as cfg
            from inputs import Inputs
            from machine import Pin
            self.cfg, self.Pin = cfg, Pin
            st = self.app.st
            self.inputs = Inputs(cfg, lambda: st["enc_rev"])
            services.append(("ulaz", self._handle_inputs))
        services += [("sim", self._sim_services), ("ekran", self.app.ui.tick)]

        def sleep(ms):
            compat.sleep_ms(ms + loop_extra_ms)

        self.loop = Loop(services, sleep)
        self.app.loop = self.loop
        self.app.pump = self.loop.step
        tac.app = self.app

    def _handle_inputs(self):
        gui, app = self.app.ui, self.app
        for ev in self.inputs.poll(gui.top.wants_hold):
            if ev[0] == "stop":
                app.stop()
            else:
                gui.input(*ev)
        gui.hold(self.inputs.hold_ms)

    # ---------------- virtuelni tasteri (kao fizički: nivo pina, 0 = pritisnut) ----------------

    BUTTONS = {"back": "BTN_BACK", "ok": "BTN_OK", "stop": "BTN_STOP", "enc": "ENC_SW"}

    def button(self, name, down):
        pin = getattr(self.cfg, self.BUTTONS[name])
        if pin is not None:
            self.Pin.levels[pin] = 0 if down else 1

    def rotate(self, clicks):
        """Okret enkodera za clicks klikova (+ = u smeru kazaljke), kao pravi kvadraturni signal."""
        a, b = self.cfg.ENC_A, self.cfg.ENC_B
        seq = [(0, 1), (0, 0), (1, 0), (1, 1)] if clicks > 0 else [(1, 0), (0, 0), (0, 1), (1, 1)]
        for _ in range(abs(clicks)):
            for la, lb in seq:
                self.Pin.levels[a], self.Pin.levels[b] = la, lb
                self.Pin.handlers[a](None)

    def screen(self):
        """Poslednja nacrtana slika ekrana (128x64, 0/1) ili None ako nije bilo novog crtanja."""
        fb = self.fb
        if not fb or not fb.frames:
            return None
        px = fb.frames[-1]
        fb.frames.clear()
        return px

    def _sim_services(self):
        for fn in self.services:
            fn()

    def now(self):
        return self.compat.ticks_ms()

    def step(self):
        """Jedan krug kao while True u main.py: petlja, pa taktika ako je zatražena (blokira dok radi)."""
        self.loop.step()
        if self.app.request:
            name, self.app.request = self.app.request, None
            self.run_tactic(self.app, name)

    def actuator_ids(self):
        import config
        return dict(getattr(config, "ACTUATORS", {}))

    def tactic_meta(self, name):
        import match
        return match.read_meta(name)

    def mirror(self, side, x, y, deg):
        """Koordinate naše strane -> teren (kao tac.mirror_xy / mirror_deg)."""
        tac = self.tac
        old, tac.current_side = tac.current_side, side
        try:
            mx, my = tac.mirror_xy(x, y)
            return mx, my, tac.mirror_deg(deg)
        finally:
            tac.current_side = old
