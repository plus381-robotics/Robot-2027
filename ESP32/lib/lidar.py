# RPLIDAR A2 (standardni SCAN, 115200 baud) na UART-u, bez blokiranja petlje (L-2, docs/faza4).
#
# Za sada služi za Meni -> Lidar test (lib/lidar_test.py): ekran zove start(), poll() u svakom krugu
# petlje i stop() kad se izađe. Model za taktike (opponent(), seen(zona), L-1/L-3) dolazi posle.
#
# Tok: motor (PWM na MOTOCTL) -> STOP -> GET_INFO -> GET_HEALTH -> SCAN -> tačke. Na svaki zahtev lidar
# odgovara opisom "A5 5A dužina(30 b) mod(2 b) tip"; posle SCAN-a šalje tačke od 5 bajtova:
#   b0 = kvalitet << 2 | !S << 1 | S     (S = 1: prva tačka novog kruga)
#   b1 = ugao_q6[6:0] << 1 | 1           (C = 1: provera)
#   b2 = ugao_q6[14:7]                   ugao = ugao_q6 / 64 stepeni, u smeru kazaljke gledano odozgo
#   b3, b4 = udaljenost_q2 (LE)          mm = udaljenost_q2 / 4 (0 = nema merenja)
# Tačka koja ne prolazi proveru se odbacuje bajt po bajt dok se ne nađe ispravna (resync, broji se u bad).
#
# Uglovi napolju su u konvenciji robota (kao taktike): 0° = napred, pozitivno = levo.
# config.LIDAR_MOUNT_DEG kaže gde gleda 0° lidara. Krug se pamti kao 360 binova po 1° (najbliža tačka u binu).
from compat import ticks_ms, ticks_diff

SYNC = 0xA5
CMD_STOP, CMD_RESET, CMD_SCAN, CMD_INFO, CMD_HEALTH = 0x25, 0x40, 0x20, 0x50, 0x52
DESC = {CMD_INFO: (20, 0x04), CMD_HEALTH: (3, 0x06), CMD_SCAN: (5, 0x81)}   # očekivana (dužina, tip)
HEALTH = ("ok", "upoz", "greska")

BINS = 360
MIN_MM = 120             # bliže od ovoga je sam robot ili šum (A2: od 150 mm)
STOP_MS = 30             # posle STOP-a lidar ćuti bar 1 ms; ulaz se baca dok ne prođe
REPLY_MS = 600           # odgovor na GET_INFO/GET_HEALTH/SCAN
STALL_MS = 1500          # bez tačaka ovoliko u SCAN-u: ponovo pokreni
TRIES = 3                # pokušaja zahteva pre "nema odgovora"
CHUNK = 1000             # najviše bajtova po krugu petlje (~200 tačaka, par ms na ESP32-S3)
RXBUF = 4096             # UART bafer: ~350 ms podataka na 115200 baud-a (sporiji krug petlje ne gubi tačke)


class Lidar:
    def __init__(self, uart, motor=None, mount_deg=0, motor_duty=60):
        """uart: već otvoren UART (timeout=0). motor: PWM na MOTOCTL ili None. motor_duty: % popune."""
        self.uart, self.motor = uart, motor
        self.mount = mount_deg
        self.duty = max(0, min(100, motor_duty)) * 65535 // 100
        self.state = "off"           # off, stop, info, health, scanwait, scan, greska
        self.why = ""                # zašto nije u SCAN-u (za ekran)
        self.info = None             # {"model", "fw", "hw", "serial"}
        self.health = None           # (stanje 0/1/2, kod greške)
        self.dist = [0] * BINS       # poslednji ceo krug: mm po stepenu robota (0 = nema tačke)
        self._cur = [0] * BINS       # krug koji se upravo puni
        self.scans = 0               # celih krugova od start()
        self.points = 0              # tačaka u poslednjem krugu
        self._n = 0
        self.hz = 0.0                # krugova u sekundi
        self.nearest = None          # (mm, ugao robota -180..180) u poslednjem krugu
        self.bad = 0                 # odbačeni bajtovi (resync)
        self.restarts = 0
        self._buf = b""
        self._cmd = None             # na koji zahtev se čeka odgovor
        self._tries = 0
        self._t = 0                  # početak čekanja (ms)
        self._t_scan = None          # kad je počeo poslednji krug
        self._t_pt = 0               # poslednja tačka

    # ---------------- upravljanje ----------------

    def start(self):
        """Motor, pa STOP/INFO/HEALTH/SCAN (poll() vodi dalje)."""
        self._motor(True)
        self.info = self.health = None
        self.scans = self.points = self._n = 0
        self.hz, self.nearest, self._t_scan = 0.0, None, None
        for i in range(BINS):
            self.dist[i] = self._cur[i] = 0
        self._send(CMD_STOP)
        self.state, self.why = "stop", "pokrecem"
        self._t = ticks_ms()

    def stop(self):
        if self.state != "off":
            self._send(CMD_STOP)
        self._motor(False)
        self.state, self.why = "off", ""
        self._cmd = None
        self._buf = b""

    @property
    def scanning(self):
        return self.state == "scan" and self.scans > 0

    def _motor(self, on):
        if self.motor is not None:
            self.motor.duty_u16(self.duty if on else 0)

    def _send(self, cmd):
        self.uart.write(bytes((SYNC, cmd)))

    def _ask(self, cmd, state):
        self._buf = b""
        self._send(cmd)
        self._cmd, self.state = cmd, state
        self._t = ticks_ms()

    def _fail(self, why):
        self.state, self.why = "greska", why
        self._cmd = None
        self._motor(False)

    # ---------------- petlja ----------------

    def _read(self):
        n = self.uart.any()
        if not n:
            return b""
        return self.uart.read(min(n, CHUNK)) or b""

    def poll(self):
        st = self.state
        if st in ("off", "greska"):
            if st == "off" or self.uart.any():
                self._read()                 # ništa ne čekamo: samo prazni bafer
            return
        data = self._read()
        now = ticks_ms()
        if st == "stop":
            if ticks_diff(now, self._t) >= STOP_MS:
                self._tries = 0
                self._ask(CMD_INFO, "info")
            return
        if data:
            self._buf += data
        if st == "scan":
            self._nodes()
            if ticks_diff(now, self._t_pt) > STALL_MS:      # tačke ne stižu (motor, kabl): ispočetka
                self.restarts += 1
                self.start()
                self.why = "nema tacaka"
            return
        d = self._reply()
        if d is None:
            if ticks_diff(now, self._t) > REPLY_MS:
                self._tries += 1
                if self._tries >= TRIES:
                    self._fail("nema odgovora")
                else:
                    self._ask(self._cmd, st)
            return
        if st == "info":
            self.info = {"model": d[0], "fw": "%d.%02d" % (d[2], d[1]), "hw": d[3],
                         "serial": "".join("%02X" % b for b in d[4:20])}
            self._tries = 0
            self._ask(CMD_HEALTH, "health")
        elif st == "health":
            self.health = (d[0], d[1] | d[2] << 8)
            if d[0] >= 2:
                self._fail("zdravlje: kod %d" % self.health[1])
                return
            self._tries = 0
            self._ask(CMD_SCAN, "scanwait")
        elif st == "scanwait":
            self.state, self.why = "scan", "ceka krug"
            self._t_pt = now
            self._nodes()

    def _reply(self):
        """Opis odgovora na self._cmd i njegovi podaci (bytes), ili None dok ne stigne ceo.
        Za SCAN vraća b"" (podaci su tačke, ostaju u baferu)."""
        b = self._buf
        while True:
            j = b.find(b"\xa5\x5a")
            if j < 0:
                keep = 1 if b[-1:] == b"\xa5" else 0
                self.bad += len(b) - keep
                self._buf = b[len(b) - keep:]
                return None
            if len(b) < j + 7:
                self._buf = b[j:]
                return None
            size = b[j + 2] | b[j + 3] << 8 | b[j + 4] << 16 | (b[j + 5] & 0x3F) << 24
            if (size, b[j + 6]) != DESC[self._cmd]:
                self.bad += j + 2
                b = b[j + 2:]                # nije naš opis: traži dalje
                continue
            body = j + 7
            if self._cmd == CMD_SCAN:
                self._buf = b[body:]
                return b""
            if len(b) < body + size:
                self._buf = b[j:]
                return None
            self._buf = b[body + size:]
            return b[body:body + size]

    def _nodes(self):
        b = self._buf
        n = len(b)
        i = 0
        got = False
        while i + 5 <= n:
            b0, b1 = b[i], b[i + 1]
            s = b0 & 1
            q6 = b[i + 2] << 7 | b1 >> 1
            if s == (b0 >> 1) & 1 or not b1 & 1 or q6 >= 23040:     # 23040 = 360 * 64
                i += 1
                self.bad += 1
                continue
            if s:
                self._new_scan()
            q = b0 >> 2
            d = (b[i + 3] | b[i + 4] << 8) >> 2
            i += 5
            got = True
            if q and d >= MIN_MM:
                k = int((self.mount - q6 / 64) % 360 + 0.5) % BINS
                c = self._cur[k]
                if c == 0 or d < c:
                    self._cur[k] = d
                self._n += 1
        self._buf = b[i:]
        if got:
            self._t_pt = ticks_ms()

    def _new_scan(self):
        now = ticks_ms()
        if self._t_scan is not None:          # prvi (nepotpun) krug se ne računa
            dt = ticks_diff(now, self._t_scan)
            if dt > 0:
                hz = 1000 / dt
                self.hz = hz if not self.hz else self.hz * 0.7 + hz * 0.3
            self.dist, self._cur = self._cur, self.dist
            self.points = self._n
            self.scans += 1
            self.nearest = self._closest()
            self.why = ""
        cur = self._cur
        for k in range(BINS):
            cur[k] = 0
        self._n = 0
        self._t_scan = now

    def _closest(self):
        best, at = 0, 0
        for k in range(BINS):
            d = self.dist[k]
            if d and (not best or d < best):
                best, at = d, k
        return (best, at - 360 if at > 180 else at) if best else None


_dev = None


def get(cfg):
    """Lidar sa ploče (config.LIDAR_*), jedan za ceo rad; None ako ga ploča nema."""
    global _dev
    if _dev is None and getattr(cfg, "LIDAR_UART", None) is not None:
        from machine import UART, Pin, PWM
        uart = UART(cfg.LIDAR_UART, baudrate=getattr(cfg, "LIDAR_BAUD", 115200), tx=cfg.LIDAR_TX,
                    rx=cfg.LIDAR_RX, rxbuf=RXBUF, timeout=0)
        motor = None
        if getattr(cfg, "LIDAR_MOTOCTL", None) is not None:
            motor = PWM(Pin(cfg.LIDAR_MOTOCTL), freq=getattr(cfg, "LIDAR_MOTOR_HZ", 25000), duty_u16=0)
        _dev = Lidar(uart, motor, getattr(cfg, "LIDAR_MOUNT_DEG", 0), getattr(cfg, "LIDAR_MOTOR_DUTY", 60))
    return _dev
