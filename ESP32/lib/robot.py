# Veza sa STM32 (Nucleo ili BlackPill) preko UART-a. Ne blokira: poll() u svakom krugu petlje.
#  - PING na 150 ms (heartbeat; STM32 staje posle 500 ms tišine)
#  - komanda se ponavlja do 3 puta ako ACK ne stigne za 60 ms (isti seq, STM32 je ne izvrši dvaput)
#  - ponavlja se SAMO poslednja poslata komanda: STM32 (comm.c) duplikat prepoznaje samo po
#    poslednjem seq, pa bi starija komanda ponovljena posle novije (npr. GOTO posle STOP-a)
#    bila izvršena ponovo. Starija se ne ponavlja, ali njen ACK/DONE se prihvata ako stigne
#    (npr. aktuator pa odmah GOTO); ako ne stigne, dobije događaj ("timeout", "SUPERSEDED").
#  - odgovori (ACK/DONE/FAIL) se pretvaraju u događaje:
#    (seq, naziv, "ok"|"done"|"fail"|"timeout", razlog)
from compat import ticks_ms, ticks_diff
import protocol as P
from link import build_frame, FrameParser

PING_MS = 150
ALIVE_MS = 500
ACK_MS = 60
TRIES = 3
MOTION = ("GOTO", "ROTATE", "MOVE")      # kretanje: posle ACK čeka DONE/FAIL, jedno u isto vreme
LONG = MOTION + ("ACTUATOR",)            # posle ACK čekaju DONE/FAIL (aktuatori mogu paralelno)
RESULTS = 32                             # koliko poslednjih ishoda se pamti (za tac.done())

REASONS = {getattr(P.Reason, k): k for k in dir(P.Reason) if not k.startswith("_")}
COMPAT = (1, 2, 3, 4, 5)                 # verzije protokola sa kojima ESP sme da radi
# mogućnost -> najmanja verzija. result: ishod kretanja u STATUS-u. v4: komanda RESET, RESUME (poza + meč
# jednom porukom), uptime u STATUS-u (siguran znak restarta), razlog LINK, ugaona brzina w.
FEATURES = {"bootloader": 2, "result": 3, "reset": 4, "resume": 4, "uptime": 4, "link_reason": 4, "w": 4,
            "ir": 5}                     # v5: IR_MASK (pojedinačni IR senzori), STATUS.ir_raw/ir_mask
CAUSES = (("PIN", "NRST"), ("POWER", "napajanje"), ("SOFT", "softver"), ("IWDG", "watchdog"),
          ("WWDG", "WWDG"), ("LOW_POWER", "low power"))


class Robot:
    def __init__(self, uart):
        self.uart = uart
        self.parser = FrameParser()
        self.version = None
        self.status = None             # poslednji STATUS (dict) ili None
        self.status_t = None           # kad je stigao
        self.status_n = 0              # koliko STATUS-a je stiglo (za praćenje kraja kretanja)
        self.boot_n = 0                # koliko restarta STM32 je viđeno (v4: uptime u STATUS-u se smanjio)
        self.reset_cause = None        # v4: razlog poslednjeg pokretanja STM32 (bitovi ResetCause)
        self.cause_n = 0               # boot_n za koji važi reset_cause (PONG stigao posle restarta)
        self._uptime = None
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
        self.ping_gap = 0                  # najduža pauza između dva PING-a u poslednjoj sekundi (ms)
        self._gap_cur = 0
        self._wait = {}                # seq -> [okvir, vreme slanja, pokušaja, naziv]
        self._late = {}                # seq -> [None, vreme slanja, 0, naziv]: ne ponavlja se, čeka ACK
        self._motion = {}              # seq -> naziv, čeka DONE/FAIL
        self.results = {}              # seq -> ("ok"|"done"|"fail"|"timeout", razlog), poslednji RESULTS
        self._res_order = []
        self._events = []

    # ---------------- stanje ----------------

    @property
    def alive(self):
        return self.last_rx is not None and ticks_diff(ticks_ms(), self.last_rx) < ALIVE_MS

    @property
    def ok(self):
        return self.alive and self.version in COMPAT

    def cause(self):
        """Razlog poslednjeg pokretanja STM32 kao tekst ("watchdog", "NRST"...), ili None (stari STM32)."""
        c = self.reset_cause
        if not c:
            return None
        return "+".join(t for k, t in CAUSES if c & getattr(P.ResetCause, k))

    def can(self, feature):
        """Da li STM32 (po verziji protokola) podržava mogućnost, npr. "bootloader"."""
        return (self.version or 0) >= FEATURES.get(feature, 1)

    # ---------------- slanje ----------------

    def send(self, name, **fields):
        """Pošalji komandu. Vraća seq. Odgovor stiže kao događaj iz poll()."""
        for s in list(self._wait):         # starije se više ne ponavljaju (vidi gore)
            w = self._wait.pop(s)
            self._late[s] = [None, w[1], 0, w[3]]
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
        gap = ticks_diff(now, self._last_ping)
        if gap >= PING_MS:
            self.uart.write(build_frame(P.PING, 0))
            self._last_ping = now
            if gap < 60000 and gap > self._gap_cur:
                self._gap_cur = gap
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
                    self._result(seq, "timeout", "NOREPLY")
                    self._events.append((seq, w[3], "timeout", "NOREPLY"))
                else:
                    self.uart.write(w[0])
                    w[1] = now
                    w[2] += 1
                    self.retries += 1
        for seq in list(self._late):
            w = self._late[seq]
            if ticks_diff(now, w[1]) >= ACK_MS * TRIES:
                del self._late[seq]
                self._result(seq, "timeout", "SUPERSEDED")
                self._events.append((seq, w[3], "timeout", "SUPERSEDED"))
        if ticks_diff(now, self._fps_t) >= 1000:
            self.fps, self._fps_n, self._fps_t = self._fps_n, 0, now
            self.ping_gap, self._gap_cur = self._gap_cur, 0
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
            self.reset_cause = d.get("reset_cause")
            self.cause_n = self.boot_n
        elif name == "STATUS":
            up = d.get("uptime_ms")
            if up is not None:
                if self._uptime is not None and up < self._uptime:
                    self.boot_n += 1           # STM32 je krenuo ispočetka (NRST, watchdog, napajanje, RESET)
                self._uptime = up
            self.status, self.status_t = d, now
            self.status_n += 1
        elif name == "LOG":
            try:
                txt = d["text"].decode()
            except Exception:
                txt = repr(d["text"])
            self.logs = (self.logs + [txt])[-5:]
            print("[stm32]", txt)
        elif name == "ACK":
            w = self._wait.pop(seq, None) or self._late.pop(seq, None)
            if w:
                if w[3] in LONG:            # stara kretanja: STM32 javlja FAIL PREEMPTED za njih
                    self._motion[seq] = w[3]
                    if w[3] in MOTION:
                        self.busy = w[3]
                else:
                    self._result(seq, "ok", None)
                self._events.append((seq, w[3], "ok", None))
        elif name in ("DONE", "FAIL"):
            w = self._wait.pop(seq, None) or self._late.pop(seq, None)
            label = self._motion.pop(seq, None) or (w[3] if w else None)
            if not any(n in MOTION for n in self._motion.values()):
                self.busy = None
            if label:
                reason = REASONS.get(d.get("reason"), d.get("reason")) if name == "FAIL" else None
                self._result(seq, name.lower(), reason)
                self._events.append((seq, label, name.lower(), reason))

    def _result(self, seq, kind, reason):
        self.results[seq] = (kind, reason)
        self._res_order.append(seq)
        if len(self._res_order) > RESULTS:
            self.results.pop(self._res_order.pop(0), None)
