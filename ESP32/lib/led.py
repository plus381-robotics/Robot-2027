# RGB LED (WS2812 na config.NEOPIXEL): stanje robota da se vidi i bez ekrana (K-1, docs/faza4).
# Servis u glavnoj petlji (main.py); na ploči bez LED-a (NEOPIXEL = None) se ne uvozi.
#
# Boje, prvo pravilo koje važi:
#   crveno, brzo treptanje    alarm na ekranu (STOP, VEZA, MEC U TOKU...), čeka OK
#   ljubičasto, treptanje     STM32 se restartuje (pri naoružavanju ili zaglavljen u meču)
#   žuto, stalno              NAORUZAN: čeka se činč
#   žuto, brzo treptanje      robot BLOKIRAN (STATUS), u meču ili testu
#   belo, disanje             meč traje (taktika ide)
#   plavo, disanje            test taktika (bez meča)
#   zeleno, sporo treptanje   meč gotov (do kraja 100 s)
#   zeleno, stalno            PROVERA prolazi: može da se naoružava
#   crveno, stalno            PROVERA ne prolazi (nema STM32, nije izabrana taktika ili strana...)
# Svetlina: Meni -> LED (settings "led", 0 = ugašen). Upis u LED samo kad se boja promeni.
import protocol as P
from compat import ticks_ms, ticks_diff

RED, PURPLE, YELLOW, WHITE, BLUE, GREEN = ((255, 0, 0), (160, 0, 255), (255, 140, 0), (255, 255, 255),
                                           (0, 60, 255), (0, 255, 0))
STEADY, BLINK_FAST, BLINK, BLINK_SLOW, BREATHE = "stalno", 250, 500, 1000, "disanje"
BREATHE_MS = 2000
CHECK_MS = 1000                 # PROVERA (app.check) najviše jednom u sekundi, samo u mirovanju


def pick(app, ok_cache):
    """(boja, način) po stanju aplikacije. ok_cache(): da li PROVERA prolazi (keširano)."""
    m, r = app.match, app.robot
    if app.ui.alarmed:
        return RED, BLINK_FAST
    if m.state == "RESET":
        return PURPLE, BLINK
    if m.state == "NAORUZAN":
        return YELLOW, STEADY
    in_match = m.state in ("POZA", "MEC")
    if in_match or app.running:
        s = r.status if r.alive else None
        if s and s["state"] & P.State.BLOCKED:
            return YELLOW, BLINK_FAST
        return (WHITE if in_match else BLUE), BREATHE
    if m.state == "KRAJ" and m.armed:
        return GREEN, BLINK_SLOW
    return (GREEN if ok_cache() else RED), STEADY


def level(mode, now):
    """Koliko je LED upaljen (0..255) za način u trenutku now (ms)."""
    if mode == STEADY:
        return 255
    if mode == BREATHE:
        t = now % BREATHE_MS
        tri = t if t < BREATHE_MS // 2 else BREATHE_MS - t          # 0..1000..0
        return (20 + 235 * tri // (BREATHE_MS // 2)) & ~7     # u koracima od 8: manje upisa u LED
    return 255 if (now // mode) % 2 == 0 else 0


class Led:
    def __init__(self, app, pin):
        self.app = app
        self.np = None
        try:
            from machine import Pin
            from neopixel import NeoPixel
            self.np = NeoPixel(Pin(pin, Pin.OUT), 1)
        except Exception as e:          # LED nije obavezan: bez njega sve radi isto
            print("LED nije dostupan:", e)
        self._shown = None
        self._ok, self._t_ok = False, None

    def _check_ok(self):
        now = ticks_ms()
        if self._t_ok is None or ticks_diff(now, self._t_ok) >= CHECK_MS:
            self._t_ok = now
            self._ok = self.app.check()[0]
        return self._ok

    def color(self, now=None):
        """Boja koja treba da se vidi sada (r, g, b), sa svetlinom iz podešavanja."""
        now = ticks_ms() if now is None else now
        rgb, mode = pick(self.app, self._check_ok)
        k = level(mode, now) * self.app.st["led"] // 255
        return tuple(c * k // 255 for c in rgb)

    def tick(self):
        if self.np is None:
            return
        c = self.color()
        if c != self._shown:
            self._shown = c
            self.np[0] = c
            self.np.write()
