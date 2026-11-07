# Vreme isto na ESP-u (MicroPython) i na laptopu (CPython, testovi i simulator).
# Na laptopu testovi mogu da zaustave sat: compat.fake = [0], pa sleep_ms() samo pomera vreme.
try:
    from time import ticks_ms, ticks_us, ticks_diff, ticks_add, sleep_ms
except ImportError:
    import time as _t

    fake = None                          # [ms] = lažni sat (testovi), None = pravo vreme

    def ticks_ms():
        return fake[0] if fake else int(_t.monotonic() * 1000)

    def ticks_us():
        return fake[0] * 1000 if fake else int(_t.monotonic() * 1000000)

    def ticks_diff(a, b):
        return a - b

    def ticks_add(a, b):
        return a + b

    def sleep_ms(ms):
        if fake:
            fake[0] += ms
        else:
            _t.sleep(ms / 1000)
