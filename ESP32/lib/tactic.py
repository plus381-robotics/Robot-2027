# Praćenje taktike korak po korak, za prikaz na ekranu (i kasnije za log preko WiFi-ja).
# Taktika samo javlja šta radi; ovaj modul ne šalje ništa robotu.
#
#   t = tracker
#   t.start("Plava strana", total=12)
#   t.step("GOTO kocka B", timeout=3.0, next="ROTATE 90")   # prethodni korak se zatvara kao OK
#   t.fail("BLOCKED")           # ili t.ok() kad se korak završi
#   t.finish()
from compat import ticks_ms, ticks_diff

HISTORY = 20
TACTICS_DIR = "/tactics"      # gde su taktike na ESP-u (testovi ga menjaju)


class Tracker:
    def __init__(self):
        self.name = None          # ime taktike, None = ništa ne radi
        self.total = None         # ukupno koraka (ako se zna)
        self.idx = 0              # redni broj trenutnog koraka (od 1)
        self.step_name = None     # trenutni korak, None = između koraka
        self.next = None          # sledeći korak (tekst), ako taktika zna
        self.timeout_ms = None
        self.t_step = 0
        self.t_start = 0
        self.history = []         # (idx, ime, ok, razlog, trajanje_ms), najnoviji poslednji
        self.demo = False

    @property
    def running(self):
        return self.name is not None

    def start(self, name, total=None):
        self.name, self.total = name, total
        self.idx, self.step_name, self.next = 0, None, None
        self.history = []
        self.t_start = ticks_ms()

    def step(self, name, timeout=None, next=None):
        if self.step_name:
            self.ok()
        self.idx += 1
        self.step_name, self.next = name, next
        self.timeout_ms = int(timeout * 1000) if timeout else None
        self.t_step = ticks_ms()

    def ok(self):
        self._close(True, None)

    def fail(self, reason):
        self._close(False, reason)

    def finish(self):
        if self.step_name:
            self.ok()
        self.name = None

    def _close(self, ok, reason):
        if not self.step_name:
            return
        self.history = (self.history + [(self.idx, self.step_name, ok, reason, self.elapsed())])[-HISTORY:]
        self.step_name = None

    def elapsed(self):
        """Koliko traje trenutni korak (ms)."""
        return ticks_diff(ticks_ms(), self.t_step) if self.step_name else 0

    @property
    def last(self):
        return self.history[-1] if self.history else None


tracker = Tracker()


class Demo:
    """Lažna taktika samo za prikaz na ekranu (uključuje se u Podešavanjima).
    NE šalje ništa robotu."""
    STEPS = (("GOTO start", 1.5, 2.0, True), ("ROTATE 90", 0.6, 1.0, True),
             ("GOTO kocka B", 2.4, 3.0, True), ("HVATALJKA dole", 0.8, 1.0, True),
             ("GOTO zona 2", 3.2, 3.0, False), ("MOVE -150", 0.7, 1.5, True),
             ("GOTO baza", 2.0, 4.0, True))

    def __init__(self, t):
        self.t = t
        self.i = -1

    def update(self):
        t = self.t
        if not t.running:
            t.start("DEMO", total=len(self.STEPS))
            self.i = -1
        cur = self.STEPS[self.i] if self.i >= 0 else None
        if cur is None or t.elapsed() >= cur[1] * 1000:
            if cur and not cur[3]:
                t.fail("BLOCKED")
            self.i += 1
            if self.i >= len(self.STEPS):
                t.finish()
                return
            name, _, timeout, _ = self.STEPS[self.i]
            nxt = self.STEPS[self.i + 1][0] if self.i + 1 < len(self.STEPS) else None
            t.step(name, timeout, nxt)
