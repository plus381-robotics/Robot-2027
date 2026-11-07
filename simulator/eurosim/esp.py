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


def fresh_import():
    """Izbaci ESP module iz sys.modules i stavi ESP putanje na početak sys.path (kao conftest.py)."""
    for n in _esp_module_names():
        sys.modules.pop(n, None)
    for d in reversed(_esp_dirs()):
        s = str(d)
        while s in sys.path:
            sys.path.remove(s)
        sys.path.insert(0, s)


class Esp:
    """ESP strana: App, Robot, Loop, tac, kao na robotu. stm = UART objekat (SimSTM)."""

    def __init__(self, make_stm, tactics_dir, workdir, screen=False, loop_extra_ms=5):
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

        def sleep(ms):
            compat.sleep_ms(ms + loop_extra_ms)

        self.loop = Loop([("robot", self.app.update), ("sim", self._sim_services), ("ekran", self.app.ui.tick)],
                         sleep)
        self.app.loop = self.loop
        self.app.pump = self.loop.step
        tac.app = self.app

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
