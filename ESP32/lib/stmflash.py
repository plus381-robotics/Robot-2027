# Flešovanje STM32 preko ugrađenog bootloader-a na USART1 (AN3155): 8E1, 0x7F, Extended Erase,
# Write Memory po 256 B, Read Memory (provera), Go. Posle toga UART se vraća na 8N1.
#
# Ulazak u bootloader:
#   - softverski: komanda ENTER_BOOTLOADER (radi dok je na STM32 firmver sa njom)
#   - hardverski (rezerva): ako su u config.py STM_NRST i STM_BOOT0, BOOT0 = 1 i reset
try:
    from time import ticks_ms, ticks_diff, sleep_ms
except ImportError:
    pass

ACK, NACK = 0x79, 0x1F
BASE = 0x08000000
# F401: sektori 0-3 po 16 KB, 4 = 64 KB, 5.. po 128 KB
SECTORS = (16, 16, 16, 16, 64, 128, 128, 128)


class FlashError(Exception):
    pass


class Bootloader:
    def __init__(self, uart, log=print):
        self.u, self.log = uart, log

    def _read(self, n, timeout_ms):
        buf = b""
        t0 = ticks_ms()
        while len(buf) < n:
            d = self.u.read(n - len(buf))
            if d:
                buf += d
            elif ticks_diff(ticks_ms(), t0) > timeout_ms:
                break
            else:
                sleep_ms(1)
        return buf

    def _ack(self, what, timeout_ms=1000):
        b = self._read(1, timeout_ms)
        if b != bytes([ACK]):
            raise FlashError("%s: %s" % (what, "NACK" if b == bytes([NACK]) else "nema odgovora"))

    def _cmd(self, c, what, timeout_ms=1000):
        self.u.write(bytes([c, c ^ 0xFF]))
        self._ack(what, timeout_ms)

    @staticmethod
    def _xor(data):
        x = 0
        for b in data:
            x ^= b
        return x

    def _addr(self, a, what):
        d = bytes([(a >> 24) & 0xFF, (a >> 16) & 0xFF, (a >> 8) & 0xFF, a & 0xFF])
        self.u.write(d + bytes([self._xor(d)]))
        self._ack(what)

    def sync(self):
        """0x7F za automatsko prepoznavanje brzine. NACK znači da je već sinhronizovan."""
        self._read(64, 20)                          # isprazni stare bajtove
        for _ in range(5):
            self.u.write(b"\x7f")
            b = self._read(1, 300)
            if b in (bytes([ACK]), bytes([NACK])):
                return
        raise FlashError("bootloader se ne javlja na 0x7F")

    def get_id(self):
        for i in range(4):                      # posle sinhronizacije redosled može kasniti bajt
            try:
                return self._get_id()
            except FlashError:
                sleep_ms(50)
                self._read(64, 50)
        return self._get_id()

    def _get_id(self):
        self._cmd(0x02, "Get ID")
        n = self._read(1, 500)[0] + 1
        pid = self._read(n, 500)
        self._ack("Get ID kraj")
        return int.from_bytes(pid, "big")

    def erase(self, nbytes):
        """Extended Erase samo sektora koje firmver zauzima."""
        secs, total = [], 0
        for i, kb in enumerate(SECTORS):
            if total >= nbytes:
                break
            secs.append(i)
            total += kb * 1024
        if total < nbytes:
            raise FlashError("firmver je veći od fleša")
        self._cmd(0x44, "Erase")
        d = bytes([0, len(secs) - 1])
        for s in secs:
            d += bytes([0, s])
        self.u.write(d + bytes([self._xor(d)]))
        self._ack("Erase sektora %s" % secs, 5000 + 2000 * len(secs))
        return secs

    def write(self, addr, data):
        self._cmd(0x31, "Write")
        self._addr(addr, "Write adresa")
        n = bytes([len(data) - 1])
        self.u.write(n + data + bytes([self._xor(n + data)]))
        self._ack("Write podaci", 2000)

    def read(self, addr, n):
        self._cmd(0x11, "Read")
        self._addr(addr, "Read adresa")
        self.u.write(bytes([n - 1, (n - 1) ^ 0xFF]))
        self._ack("Read dužina")
        d = self._read(n, 1000)
        if len(d) != n:
            raise FlashError("Read: stiglo %d od %d" % (len(d), n))
        return d

    def go(self, addr=BASE):
        self._cmd(0x21, "Go")
        self._addr(addr, "Go adresa")


def flash_file(uart, path, uart_args, robot=None, cfg=None, log=print):
    """Upiši .bin iz fajla na STM32. uart_args: dict za uart.init() (tx, rx, baudrate, rxbuf).
    robot: Robot za softverski ulazak u bootloader. Vraća broj upisanih bajtova."""
    import os
    size = os.stat(path)[6]
    if size == 0 or size % 4:
        raise FlashError("neispravan .bin (%d B)" % size)
    hw = cfg is not None and getattr(cfg, "STM_NRST", None) is not None and getattr(cfg, "STM_BOOT0", None) is not None
    if robot is not None:                       # dok je stizao fajl, UART se nije čitao: obnovi vezu
        t0 = ticks_ms()
        while not robot.ok and ticks_diff(ticks_ms(), t0) < 1500:
            robot.poll()
            sleep_ms(5)
    if robot is not None and robot.ok:
        # Posle ove komande ESP ne sme ništa da šalje (ni PING): bootloader po prvom
        # primljenom bajtu meri brzinu i mora da to bude 0x7F.
        seq = robot.send("ENTER_BOOTLOADER")
        acked = False
        t0 = ticks_ms()
        while ticks_diff(ticks_ms(), t0) < 300:
            d = uart.read()
            if d:
                for t, s, _ in robot.parser.feed(d):
                    if s == seq and t == 0x90:      # ACK
                        acked = True
            if acked:
                break
            sleep_ms(1)
        # 8E1 odmah, dok STM32 još 30 ms radi u aplikaciji: smetnja na TX liniji pri promeni
        # UART-a ne sme da stigne do bootloader-a (njegov prvi bajt mora biti 0x7F)
        uart.init(parity=0, bits=8, stop=1, timeout=0, **uart_args)
        sleep_ms(300)
        log("ENTER_BOOTLOADER: " + ("ACK" if acked else "bez ACK"))
    elif hw:
        log("BOOT0 + reset")
    else:
        log("STM32 se ne javlja; probam bootloader (možda je već u njemu)")
    if hw:
        from machine import Pin
        boot0 = Pin(cfg.STM_BOOT0, Pin.OUT, value=1)
        nrst = Pin(cfg.STM_NRST, Pin.OPEN_DRAIN, value=0)
        sleep_ms(20)
        nrst.value(1)
        sleep_ms(80)
    uart.init(parity=0, bits=8, stop=1, timeout=0, **uart_args)
    bl = Bootloader(uart, log)
    try:
        for attempt in range(3):                # STM32 ostaje u bootloader-u, pa ponovni pokušaj pomaže
            try:
                bl.sync()
                log("ID 0x%03X" % bl.get_id())
                break
            except FlashError as e:
                if attempt == 2:
                    raise
                log("ponovo: %s" % e)
                uart.init(parity=0, bits=8, stop=1, timeout=0, **uart_args)
                sleep_ms(300)
        log("brisem sektore %s" % bl.erase(size))
        buf = bytearray(256)
        mv = memoryview(buf)
        with open(path, "rb") as f:
            addr = BASE
            while True:
                n = f.readinto(buf)
                if not n:
                    break
                bl.write(addr, bytes(mv[:n]))
                addr += n
                if (addr - BASE) % 8192 == 0:
                    log("upisano %d/%d" % (addr - BASE, size))
            f.seek(0)
            addr = BASE
            while True:
                n = f.readinto(buf)
                if not n:
                    break
                if bl.read(addr, n) != bytes(mv[:n]):
                    raise FlashError("provera nije prošla na 0x%08X" % addr)
                addr += n
        log("provera OK, pokrecem")
        bl.go()
    finally:
        if hw:
            boot0.value(0)
            nrst.value(0)
            sleep_ms(20)
            nrst.value(1)
        uart.init(parity=None, bits=8, stop=1, timeout=0, **uart_args)
    return size
