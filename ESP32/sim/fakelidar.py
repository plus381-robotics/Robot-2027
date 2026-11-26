# Lažni RPLIDAR A2 za laptop (testovi, render.py, simulator): isti bajtovi kao pravi lidar na 115200 baud-a.
# Odgovara na STOP, RESET, GET_INFO, GET_HEALTH i SCAN; u SCAN-u šalje RATE tačaka u sekundi, HZ krugova
# u sekundi, samo dok se motor vrti (motor() -> True). Udaljenost daje ranges(ugao_lidara) -> mm (0 = nema),
# ugao u smeru kazaljke kao pravi lidar. Bafer je ograničen kao UART rxbuf (najstariji bajtovi se gube).
# Kao UART: any(), read(n), write(b). Prijava: machine.UART.devices[config.LIDAR_UART] = FakeRplidar(...).
import math

RATE, HZ = 2000, 10


def node(angle, mm, quality=47, start=False):
    """Jedna tačka SCAN-a (5 bajtova)."""
    q6 = int(angle * 64) % (360 * 64)
    d = max(0, min(0xFFFF, int(mm * 4)))
    return bytes((quality << 2 | (1 if start else 2), (q6 & 0x7F) << 1 | 1, q6 >> 7, d & 0xFF, d >> 8))


def descriptor(size, kind, mode=0):
    v = size | mode << 30
    return bytes((0xA5, 0x5A, v & 0xFF, v >> 8 & 0xFF, v >> 16 & 0xFF, v >> 24 & 0xFF, kind))


def room(angle):
    """Podrazumevana scena: robot u sredini sobe 1200 x 800 mm (napred x), protivnik (krug r = 100 mm)
    na 500 mm napred i 300 mm levo. angle: ugao lidara (u smeru kazaljke, 0 = napred)."""
    a = math.radians(-angle)
    dx, dy = math.cos(a), math.sin(a)
    t = min(600 / abs(dx) if abs(dx) > 1e-9 else 1e9, 400 / abs(dy) if abs(dy) > 1e-9 else 1e9)
    ox, oy, r = 500, 300, 100
    b = dx * ox + dy * oy                     # zrak iz (0, 0): t^2 - 2bt + |o|^2 - r^2 = 0
    c = ox * ox + oy * oy - r * r
    disc = b * b - c
    if disc >= 0 and b - math.sqrt(disc) > 0:
        t = min(t, b - math.sqrt(disc))
    return t


class FakeRplidar:
    def __init__(self, clock, ranges=room, motor=None, rxbuf=4096, model=0x28, fw=(1, 29), hw=7, health=(0, 0)):
        self.clock, self.ranges = clock, ranges
        self.motor = motor or (lambda: True)
        self.rxbuf = rxbuf
        self.model, self.fw, self.hw, self.health = model, fw, hw, health
        self.out = bytearray()
        self.scanning = False
        self.mute = False                     # True = ne odgovara (isključen, pogrešan TX/RX)
        self.cmds = []                        # primljene komande (za testove)
        self.lost = 0                         # bajtova izgubljenih zbog punog bafera
        self._t = 0.0
        self._k = 0

    # ---------------- UART ----------------

    def write(self, b):
        b = bytes(b)
        for i in range(len(b) - 1):
            if b[i] == 0xA5:
                self._cmd(b[i + 1])
        return len(b)

    def any(self):
        self._gen()
        return len(self.out)

    def read(self, n=-1):
        self._gen()
        if not self.out:
            return None
        n = len(self.out) if n is None or n < 0 else n
        data = bytes(self.out[:n])
        del self.out[:n]
        return data

    # ---------------- lidar ----------------

    def _put(self, data):
        self.out += data
        over = len(self.out) - self.rxbuf
        if over > 0:
            del self.out[:over]
            self.lost += over

    def _cmd(self, c):
        self.cmds.append(c)
        if self.mute:
            return
        if c in (0x25, 0x40):                  # STOP, RESET
            self.scanning = False
            if c == 0x40:
                self._put(b"RP LIDAR System.\r\nFirmware Ver 1.29 - rc0\r\n")
        elif c == 0x50:                        # GET_INFO
            self._put(descriptor(20, 0x04) + bytes((self.model, self.fw[1], self.fw[0], self.hw)) + bytes(range(16)))
        elif c == 0x52:                        # GET_HEALTH
            st, code = self.health
            self._put(descriptor(3, 0x06) + bytes((st, code & 0xFF, code >> 8)))
        elif c == 0x20:                        # SCAN
            self._put(descriptor(5, 0x81, mode=1))
            self.scanning = True
            self._t = self.clock()
            self._k = 0

    def _gen(self):
        if not self.scanning or self.mute:
            return
        now = self.clock()
        if not self.motor():
            self._t = now
            return
        n = int((now - self._t) * RATE / 1000)
        if n <= 0:
            return
        self._t += n * 1000 / RATE
        per = RATE // HZ
        out = bytearray()
        for _ in range(min(n, self.rxbuf // 5 + per)):    # posle dugog zastoja ionako ostaje samo kraj
            k = self._k % per
            a = k * 360 / per
            d = self.ranges(a)
            out += node(a, d or 0, 47 if d else 0, k == 0)
            self._k += 1
        self._put(out)
