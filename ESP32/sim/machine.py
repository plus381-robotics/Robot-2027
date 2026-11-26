# Lažni machine modul za testove i simulator na laptopu.
# Pin: test postavlja Pin.levels[broj] = 0/1 i zove Pin.handlers[broj](None).


class Pin:
    IN, OUT, OPEN_DRAIN, PULL_UP, IRQ_RISING, IRQ_FALLING = 1, 2, 3, 4, 8, 16
    levels, handlers, hard = {}, {}, {}

    def __init__(self, n, mode=None, pull=None, value=None):
        self.n = n
        Pin.levels.setdefault(n, 1 if value is None else value)

    def value(self, v=None):
        if v is None:
            return Pin.levels[self.n]
        Pin.levels[self.n] = v

    def irq(self, handler, trigger, hard=False):
        Pin.handlers[self.n] = handler
        Pin.hard[self.n] = hard


def disable_irq():
    return 0


def enable_irq(state):
    pass


class I2C:
    def __init__(self, *a, **k):
        pass

    def scan(self):
        return [0x3C]


class UART:
    """Ka STM32 se zamenjuje lažnim STM32 (sim/fakestm.py). Ostali UART-ovi: ako je za id prijavljen lažni
    uređaj (UART.devices[id] = npr. sim/fakelidar.FakeRplidar), UART(id, ...) vraća njega; inače ćuti."""
    devices = {}

    def __new__(cls, id=None, *a, **k):
        dev = cls.devices.get(id)
        return dev if dev is not None else super().__new__(cls)

    def __init__(self, *a, **k):
        pass

    def any(self):
        return 0

    def read(self, n=-1):
        return None

    def write(self, b):
        return len(b)


class PWM:
    """PWM pamti frekvenciju i popunu; PWM.pins[pin] = poslednji PWM na tom pinu (buzzer, motor lidara)."""
    pins = {}

    def __init__(self, pin, freq=0, duty_u16=0, **k):
        self.pin = pin.n if isinstance(pin, Pin) else pin
        self._freq, self._duty = freq, duty_u16
        PWM.pins[self.pin] = self

    def freq(self, f=None):
        if f is None:
            return self._freq
        self._freq = f

    def duty_u16(self, d=None):
        if d is None:
            return self._duty
        self._duty = d

    def deinit(self):
        self._duty = 0


class WDT:
    fed = 0

    def __init__(self, timeout=5000):
        self.timeout = timeout

    def feed(self):
        WDT.fed += 1


class RTC:
    _mem = b""

    def memory(self, data=None):
        if data is None:
            return RTC._mem
        RTC._mem = bytes(data)


def reset():
    raise SystemExit("machine.reset()")
