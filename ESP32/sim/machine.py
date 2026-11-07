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
    """Zamenjuje se lažnim STM32 (sim/fakestm.py) u testovima."""
    def __init__(self, *a, **k):
        pass


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
