# Enkoder i tasteri -> događaji za meni (ui.py).
#
#   okret enkodera        -> ("rot", n)
#   klik enkodera          -> ("ok",)        dugi klik -> ("back",)  (osim kad ekran traži držanje)
#   taster NAZAD           -> ("back",)      dugi -> ("home",)
#   taster OK              -> ("ok",)
#   taster STOP            -> ("stop",)      odmah na pritisak, ne čeka puštanje
#   držanje OK (enkoder ili taster) -> hold_ms (za "drži za potvrdu")
# Svi tasteri su na GND sa internim pull-up otpornikom.
from machine import Pin, disable_irq, enable_irq
from time import ticks_ms, ticks_diff

DEBOUNCE_MS = 20
LONG_MS = 600

# Prelaz (staro_stanje << 2 | novo_stanje) -> korak; nevažeći skokovi (odskakanje) daju 0.
_STEP = (0, -1, 1, 0, 1, 0, 0, -1, -1, 0, 0, 1, 0, 1, -1, 0)


class Encoder:
    """Kvadraturni enkoder preko prekida. steps = prelaza po jednom "kliku" (obično 4, neki 2)."""
    def __init__(self, pin_a, pin_b, steps=4):
        self.a = Pin(pin_a, Pin.IN, Pin.PULL_UP)
        self.b = Pin(pin_b, Pin.IN, Pin.PULL_UP)
        self.steps = steps
        self._s = (self.a.value() << 1) | self.b.value()
        self._acc = 0
        self._clicks = 0
        self.a.irq(self._irq, Pin.IRQ_RISING | Pin.IRQ_FALLING)
        self.b.irq(self._irq, Pin.IRQ_RISING | Pin.IRQ_FALLING)

    def _irq(self, _):
        s = (self.a.value() << 1) | self.b.value()
        self._acc += _STEP[(self._s << 2) | s]
        self._s = s
        if self._acc >= self.steps:
            self._acc -= self.steps
            self._clicks += 1
        elif self._acc <= -self.steps:
            self._acc += self.steps
            self._clicks -= 1

    def take(self):
        """Koliko klikova od prošlog poziva (+ = u smeru kazaljke)."""
        st = disable_irq()
        n, self._clicks = self._clicks, 0
        enable_irq(st)
        return n


class Button:
    def __init__(self, pin):
        self.p = Pin(pin, Pin.IN, Pin.PULL_UP)
        self.down = False
        self._since = None      # kad je sirovo stanje počelo da se razlikuje
        self._t = 0             # kad je pritisnut
        self._long = False

    def update(self, now):
        """Vraća "press", "click", "long" ili None. Klik = pušten pre LONG_MS."""
        raw = self.p.value() == 0
        if raw == self.down:
            self._since = None
        elif self._since is None:
            self._since = now
        elif ticks_diff(now, self._since) >= DEBOUNCE_MS:
            self._since = None
            self.down = raw
            if raw:
                self._t, self._long = now, False
                return "press"
            return None if self._long else "click"
        if self.down and not self._long and ticks_diff(now, self._t) >= LONG_MS:
            self._long = True
            return "long"
        return None

    def held(self, now):
        return ticks_diff(now, self._t) if self.down else 0


class Inputs:
    def __init__(self, cfg, reverse=lambda: False):
        """cfg: config.py (pinovi). reverse(): True = obrni smer enkodera (podešavanje)."""
        self.enc = Encoder(cfg.ENC_A, cfg.ENC_B, cfg.ENC_STEPS) if cfg.ENC_A is not None else None
        self.sw = Button(cfg.ENC_SW) if cfg.ENC_SW is not None else None
        self.b_back = Button(cfg.BTN_BACK)
        self.b_ok = Button(cfg.BTN_OK)
        self.b_stop = Button(cfg.BTN_STOP)
        self.reverse = reverse
        self.hold_ms = 0

    def poll(self, wants_hold=False):
        """Lista događaja od prošlog poziva. Posle poziva self.hold_ms = koliko se drži OK."""
        now = ticks_ms()
        ev = []
        if self.enc:
            n = self.enc.take()
            if n:
                ev.append(("rot", -n if self.reverse() else n))
        if self.sw:
            e = self.sw.update(now)
            if e == "click":
                ev.append(("ok",))
            elif e == "long" and not wants_hold:
                ev.append(("back",))
        e = self.b_back.update(now)
        if e == "click":
            ev.append(("back",))
        elif e == "long":
            ev.append(("home",))
        if self.b_ok.update(now) == "click":
            ev.append(("ok",))
        if self.b_stop.update(now) == "press":
            ev.append(("stop",))
        self.hold_ms = max(self.sw.held(now) if self.sw else 0, self.b_ok.held(now))
        return ev
