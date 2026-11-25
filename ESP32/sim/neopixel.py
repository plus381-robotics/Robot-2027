# Lažni neopixel za laptop (testovi, simulator): pamti boje i broj upisa.
class NeoPixel:
    def __init__(self, pin, n):
        self.pin, self.n = pin, n
        self.buf = [(0, 0, 0)] * n
        self.writes = 0

    def __setitem__(self, i, c):
        self.buf[i] = tuple(c)

    def __getitem__(self, i):
        return self.buf[i]

    def write(self):
        self.writes += 1
