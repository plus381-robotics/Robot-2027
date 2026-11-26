# Pasivni buzzer (PWM na config.BUZZER): zvuci i melodije u RTTTL formatu, bez blokiranja petlje (K-2).
# Servis u glavnoj petlji (main.py): play() samo zapiše note, tick() menja ton kad dođe vreme.
#
# Zvuci su u config.SOUNDS (ime -> RTTTL), pa se melodija menja bez diranja koda:
#   "ok"        1 kratak    potvrda (naoružan, potvrđena opasna radnja)
#   "upoz"      2 kratka    upozorenje (greška koraka van meča, poruka u traci)
#   "greska"    3 kratka    greška / prekid preko celog ekrana (STOP, VEZA, PREKID)
#   "baterija"  1 dug       slaba baterija (za kad bude merenja)
#   "boot"      melodija    ESP je pokrenut
#   "start"     melodija    činč izvučen, meč kreće
#   "kraj"      melodija    kraj meča (100 s)
#   "gotovo"    melodija    test taktika završena bez greške
# Taktika može da pusti svoj zvuk: tac.play("kraj") ili tac.play("ime:d=8,o=6,b=180:c,e,g").
#
# RTTTL format: lib/rtttl.py.
#
# Podešavanje "zvuk" (settings "sound"): 0 = isključen, 1 = samo greška i baterija, 2 = sve.
# U meču (POZA, MEC) se čuju samo greška, start, kraj i zvuk iz taktike. Važniji zvuk prekida manje
# važan, obrnuto ne.
from compat import ticks_ms, ticks_diff
import rtttl
from rtttl import parse, note_hz  # noqa: F401  (parser je u rtttl.py: koristi ga i simulator)

OFF, ERRORS, ALL = 0, 1, 2
IMPORTANT = ("greska", "baterija")          # čuju se i na nivou "samo greške"
IN_MATCH = ("greska", "start", "kraj", "takt")
PRIO = {"greska": 5, "baterija": 4, "start": 3, "kraj": 3, "upoz": 2}     # ostali: 1
MENU = ("ok", "upoz", "greska", "baterija", "boot", "start", "kraj", "gotovo")
DUTY = 32768                                # 50 %: najglasnije za pasivni buzzer
GAP_MS = 12                                 # tišina na kraju svake note (iste note se čuju odvojeno)

# Podrazumevani zvuci, ako config.SOUNDS ne kaže drugačije. Oktave 6 i 7: buzzer (CEM-1206S) je
# najglasniji oko 2,4 kHz; ispod ~1 kHz se jedva čuje.
DEFAULT_SOUNDS = {
    "ok": "ok:d=16,o=7,b=200:d",
    "upoz": "upoz:d=16,o=7,b=200:d,p,d",
    "greska": "greska:d=8,o=7,b=200:d,16p,d,16p,d",
    "baterija": "baterija:d=2,o=6,b=120:g",
    "boot": "boot:d=16,o=6,b=180:c,e,g,8c7",
    "start": "start:d=16,o=6,b=180:c,d,e,f,g,a,b,4c7",
    "kraj": "kraj:d=8,o=6,b=160:c7,g,e,4c",
    "gotovo": "gotovo:d=16,o=6,b=200:e,g,8c7",
}

def tones(notes):
    """Note -> tonovi za PWM (generator): na kraju svake note kratka tišina (GAP_MS)."""
    for hz, ms in notes:
        if hz and ms > 2 * GAP_MS:
            yield hz, ms - GAP_MS
            yield 0, GAP_MS
        else:
            yield hz, ms


def allowed(kind, level, in_match):
    """Da li zvuk sme da se čuje (podešavanje i meč). kind "takt" = zvuk iz taktike (tac.play)."""
    if level <= OFF or not (level >= ALL or kind in IMPORTANT):
        return False
    return not in_match or kind in IN_MATCH


def sounds():
    """Zvuci: podrazumevani, pa izmene iz config.SOUNDS."""
    out = dict(DEFAULT_SOUNDS)
    try:
        import config
        out.update(getattr(config, "SOUNDS", {}))
    except ImportError:
        pass
    return out


class Buzzer:
    """Melodija se ne parsira unapred: note se čitaju iz teksta jedna po jedna (rtttl.stream), pa i duga
    melodija (Paganini, ~430 nota) kreće odmah i ne zauzima RAM. Loša nota u sred melodije je prekida."""

    def __init__(self, app, pin):
        self.app = app
        self.pwm = None
        try:
            from machine import Pin, PWM
            self.pwm = PWM(Pin(pin), freq=2000, duty_u16=0)
        except Exception as e:          # buzzer nije obavezan: bez njega sve radi isto
            print("buzzer nije dostupan:", e)
        self.sounds = sounds()
        self.text = None                # RTTTL tekst koji svira
        self.last = None                # poslednji pušten tekst (simulator: note za browser)
        self._it = None                 # preostali tonovi (generator)
        self.kind = None
        self.prio = 0
        self._t = 0                     # kad se menja sledeći ton
        self._hz = 0                    # ton koji sada svira (0 = tišina)
        self.played = []                # poslednji pušteni zvukovi (za testove i dijagnostiku)
        self.n = 0                      # koliko zvukova je pušteno (simulator: novi zvuk)

    def _in_match(self):
        return self.app.match.state in ("POZA", "MEC")

    @property
    def notes(self):
        """Svi tonovi tekućeg zvuka (Hz, ms) sa pauzama, kao lista (simulator ih šalje browseru)."""
        return list(tones(parse(self.last))) if self.last else []

    def play(self, kind, force=False, melody=None):
        """Pusti zvuk kind (ime iz SOUNDS). melody: druga melodija (ime ili RTTTL) sa pravilima za kind
        (tac.play: kind "takt"). force=True: čuje se uvek (Meni -> test zvuka)."""
        prio = PRIO.get(kind, 1)
        if not force and not allowed(kind, self.app.st["sound"], self._in_match()):
            return False
        if self.kind is not None and prio < self.prio:
            return False                # važniji zvuk još traje
        name = melody or kind
        text = self.sounds.get(name, name)
        try:
            it = tones(rtttl.stream(text))
            first = next(it)
        except (ValueError, StopIteration) as e:
            print("zvuk %s: %s" % (name, e or "nema nota"))
            return False
        self.kind, self.prio, self.text, self.last = kind, prio, text, text
        self._it = it
        self.played = (self.played + [kind])[-10:]
        self.n += 1
        self._t = ticks_ms()
        self._tone(first)
        return True

    def _set(self, hz):
        if hz == self._hz:
            return
        if self.pwm is not None:
            if hz:
                self.pwm.freq(hz)
                if not self._hz:
                    self.pwm.duty_u16(DUTY)
            else:
                self.pwm.duty_u16(0)
        self._hz = hz

    def _tone(self, t):
        self._set(t[0])
        self._t += t[1]                  # od planiranog trenutka, ne od sada: ritam ne kasni za petljom

    def _end(self):
        self._set(0)
        self.kind, self.prio, self.text, self._it = None, 0, None, None

    def _next(self):
        try:
            self._tone(next(self._it))
        except StopIteration:
            self._end()
        except ValueError as e:          # loša nota u sred melodije (config.SOUNDS)
            print("zvuk %s: %s" % (self.kind, e))
            self._end()

    def stop(self):
        """Prekini zvuk koji svira."""
        if self.kind is not None:
            self._end()

    @property
    def sounding(self):
        return bool(self._hz)

    @property
    def hz(self):
        return self._hz

    def tick(self):
        # posle zastoja petlje (npr. crtanje ekrana) preskoči note koje su već prošle: ritam ostaje isti
        while self.kind is not None and ticks_diff(ticks_ms(), self._t) >= 0:
            self._next()
