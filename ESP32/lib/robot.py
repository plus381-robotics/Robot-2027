# Veza sa STM32 (Nucleo ili BlackPill) preko UART-a. Ne blokira: poll() u svakom krugu petlje.
#  - PING na 150 ms (heartbeat; STM32 staje posle 500 ms tišine)
#  - komanda se ponavlja do 3 puta ako ACK ne stigne za 60 ms (isti seq, STM32 je ne izvrši dvaput)
#  - odgovori (ACK/DONE/FAIL) se pretvaraju u događaje:
#    (seq, naziv, "ok"|"done"|"fail"|"timeout", razlog)
try:
    from time import ticks_ms, ticks_diff
except ImportError:
    from ui import ticks_ms, ticks_diff
import protocol as P
from link import build_frame, FrameParser

PING_MS = 150
ALIVE_MS = 500
ACK_MS = 60
TRIES = 3
MOTION = ("GOTO", "ROTATE", "MOVE")      # posle ACK čekaju još DONE/FAIL

REASONS = {getattr(P.Reason, k): k for k in dir(P.Reason) if not k.startswith("_")}


class Robot:
    def __init__(self, uart):
        self.uart = uart
        self.parser = FrameParser()
        self.version = None
        self.status = None             # poslednji STATUS (dict) ili None
        self.status_t = None           # kad je stigao
        self.last_rx = None
        self.fps = 0                   # ispravnih okvira u poslednjoj sekundi
        self._fps_n = 0
        self._fps_t = 0
        self.frames = 0                # ispravno primljeni okviri
        self.retries = 0               # ponovljena slanja
        self.noreply = 0               # komande bez odgovora posle 3 pokušaja
        self.logs = []                 # poslednjih nekoliko LOG poruka
        self.busy = None               # kretanje koje traje (naziv) ili None
        self._seq = 0
        self._last_ping = 0
        self._wait = {}                # seq -> [okvir, vreme slanja, pokušaja, naziv]
        self._motion = {}              # seq -> naziv, čeka DONE/FAIL
        self._events = []

    # ---------------- stanje ----------------

    @property
    def alive(self):
        return self.last_rx is not None and ticks_diff(ticks_ms(), self.last_rx) < ALIVE_MS

    @property
    def ok(self):
        return self.alive and self.version == P.VERSION

    # ---------------- slanje ----------------

    def send(self, name, **fields):
        """Pošalji komandu. Vraća seq. Odgovor stiže kao događaj iz poll()."""
        self._seq = self._seq % 255 + 1
        t, payload = P.encode(name, **fields)
        frame = build_frame(t, self._seq, payload)
        self.uart.write(frame)
        self._wait[self._seq] = [frame, ticks_ms(), 1, name]
        return self._seq

    # ---------------- prijem ----------------

    def poll(self):
        """Pošalji PING kad treba, obradi pristigle okvire. Vraća listu događaja."""
        now = ticks_ms()
        if ticks_diff(now, self._last_ping) >= PING_MS:
            self.uart.write(build_frame(P.PING, 0))
            self._last_ping = now
        data = self.uart.read()
        if data:
            for t, seq, payload in self.parser.feed(data):
                self._frame(now, t, seq, payload)
        for seq in list(self._wait):
            w = self._wait[seq]
            if ticks_diff(now, w[1]) >= ACK_MS:
                if w[2] >= TRIES:
                    del self._wait[seq]
                    self.noreply += 1
                    self._events.append((seq, w[3], "timeout", None))
                else:
                    self.uart.write(w[0])
                    w[1] = now
                    w[2] += 1
                    self.retries += 1
        if ticks_diff(now, self._fps_t) >= 1000:
            self.fps, self._fps_n, self._fps_t = self._fps_n, 0, now
        ev, self._events = self._events, []
        return ev

    def status_age(self):
        """Koliko ms je star poslednji STATUS (None = nije ni stigao)."""
        return None if self.status_t is None else ticks_diff(ticks_ms(), self.status_t)

    def _frame(self, now, t, seq, payload):
        self.frames += 1
        self._fps_n += 1
        self.last_rx = now
        name, d = P.decode(t, payload)
        if name == "PONG":
            self.version = d["version"]
        elif name == "STATUS":
            self.status, self.status_t = d, now
        elif name == "LOG":
            try:
                txt = d["text"].decode()
            except Exception:
                txt = repr(d["text"])
            self.logs = (self.logs + [txt])[-5:]
            print("[stm32]", txt)
        elif name == "ACK":
            w = self._wait.pop(seq, None)
            if w:
                if w[3] in MOTION:          # stara kretanja: STM32 javlja FAIL PREEMPTED za njih
                    self._motion[seq] = w[3]
                    self.busy = w[3]
                self._events.append((seq, w[3], "ok", None))
        elif name in ("DONE", "FAIL"):
            w = self._wait.pop(seq, None)
            label = self._motion.pop(seq, None) or (w[3] if w else None)
            if not self._motion:
                self.busy = None
            if label:
                reason = REASONS.get(d.get("reason"), d.get("reason")) if name == "FAIL" else None
                self._events.append((seq, label, name.lower(), reason))
