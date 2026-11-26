# Pasivni buzzer (PWM na config.BUZZER): kratki signali bez blokiranja petlje (K-2, docs/faza4).
# Servis u glavnoj petlji (main.py): play() samo zapiše tonove, tick() pali i gasi PWM kad dođe vreme.
#
#   "ok"        1 kratak    potvrda (naoružan, potvrđena opasna radnja)
#   "upoz"      2 kratka    upozorenje (greška koraka van meča, poruka u traci)
#   "greska"    3 kratka    greška / prekid preko celog ekrana (STOP, VEZA, PREKID)
#   "baterija"  1 dug       slaba baterija (za kad bude merenja)
#
# Podešavanje "zvuk" (settings "sound"): 0 = isključen, 1 = samo greška i baterija, 2 = sve.
# U meču (POZA, MEC) se čuje samo greška. Važniji zvuk prekida manje važan, obrnuto ne.
from compat import ticks_ms, ticks_diff

OFF, ERRORS, ALL = 0, 1, 2
# (ton: 1 = ton, 0 = tišina, trajanje ms); prioritet: veći prekida manji
PATTERNS = {
    "ok": (3, ((1, 70),)),
    "upoz": (2, ((1, 90), (0, 90), (1, 90))),
    "greska": (4, ((1, 130), (0, 80), (1, 130), (0, 80), (1, 130))),
    "baterija": (5, ((1, 900),)),
}
IMPORTANT = ("greska", "baterija")      # čuju se i na nivou "samo greške"
DUTY = 32768                            # 50 %: najglasnije za pasivni buzzer


def allowed(kind, level, in_match):
    """Da li zvuk sme da se čuje (podešavanje i meč)."""
    if level <= OFF:
        return False
    if in_match:
        return kind == "greska"
    return level >= ALL or kind in IMPORTANT


class Buzzer:
    def __init__(self, app, pin, hz=2700):
        self.app, self.hz = app, hz
        self.pwm = None
        try:
            from machine import Pin, PWM
            self.pwm = PWM(Pin(pin), freq=hz, duty_u16=0)
        except Exception as e:          # buzzer nije obavezan: bez njega sve radi isto
            print("buzzer nije dostupan:", e)
        self.tones = ()                 # preostali tonovi tekućeg zvuka
        self.kind = None
        self.prio = 0
        self._t = 0                     # kad se menja sledeći ton
        self._on = False
        self.played = []                # poslednji pušteni zvukovi (za testove i dijagnostiku)
        self.n = 0                      # koliko zvukova je pušteno (simulator: novi zvuk)

    def _in_match(self):
        m = self.app.match
        return m.state in ("POZA", "MEC")

    def play(self, kind, force=False):
        """Pusti zvuk po imenu. force=True: čuje se uvek (Meni -> test zvuka)."""
        prio, tones = PATTERNS[kind]
        if not force and not allowed(kind, self.app.st["sound"], self._in_match()):
            return False
        if self.kind is not None and prio < self.prio:
            return False                # važniji zvuk još traje
        self.kind, self.prio, self.tones = kind, prio, tones
        self.played = (self.played + [kind])[-10:]
        self.n += 1
        self._t = ticks_ms()
        self._next()
        return True

    def _set(self, on):
        if on == self._on:
            return
        self._on = on
        if self.pwm is not None:
            if on:
                self.pwm.freq(self.hz)
            self.pwm.duty_u16(DUTY if on else 0)

    def _next(self):
        if self.tones:
            (on, ms), self.tones = self.tones[0], self.tones[1:]
            self._set(bool(on))
            self._t += ms                # od planiranog trenutka, ne od sada: ritam ne kasni za petljom
        else:
            self._set(False)
            self.kind, self.prio = None, 0

    @property
    def sounding(self):
        return self._on

    def tick(self):
        if self.kind is not None and ticks_diff(ticks_ms(), self._t) >= 0:
            self._next()
