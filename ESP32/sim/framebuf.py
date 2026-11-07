# Podskup MicroPython framebuf-a za simulator (isti font i algoritmi linija).
from _font import FONT
MONO_VLSB = 0
MONO_HLSB = 3

class FrameBuffer:
    def __init__(self, buf, w, h, fmt=MONO_VLSB):
        self.width, self.height = w, h
        self.px = [[0] * w for _ in range(h)]
    def pixel(self, x, y, c=None):
        if 0 <= x < self.width and 0 <= y < self.height:
            if c is None:
                return self.px[y][x]
            self.px[y][x] = 1 if c else 0
        elif c is None:
            return 0
    def fill(self, c):
        for row in self.px:
            for i in range(self.width): row[i] = c
    def fill_rect(self, x, y, w, h, c):
        for yy in range(y, y + h):
            for xx in range(x, x + w): self.pixel(xx, yy, c)
    def rect(self, x, y, w, h, c, f=False):
        if f: return self.fill_rect(x, y, w, h, c)
        self.hline(x, y, w, c); self.hline(x, y + h - 1, w, c)
        self.vline(x, y, h, c); self.vline(x + w - 1, y, h, c)
    def hline(self, x, y, w, c): self.fill_rect(x, y, w, 1, c)
    def vline(self, x, y, h, c): self.fill_rect(x, y, 1, h, c)
    def line(self, x0, y0, x1, y1, c):
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
        e = dx + dy
        while True:
            self.pixel(x0, y0, c)
            if x0 == x1 and y0 == y1: break
            e2 = 2 * e
            if e2 >= dy: e += dy; x0 += sx
            if e2 <= dx: e += dx; y0 += sy
    def ellipse(self, cx, cy, xr, yr, c, f=False, m=15):
        import math
        for i in range(720):
            a = math.radians(i / 2)
            self.pixel(round(cx + xr * math.cos(a)), round(cy + yr * math.sin(a)), c)
    def text(self, s, x, y, c=1):
        for ch in s:
            o = ord(ch)
            if o < 32 or o > 127: o = 127
            g = FONT[(o - 32) * 8:(o - 32) * 8 + 8]
            for j, col in enumerate(g):
                for b in range(8):
                    if col & (1 << b): self.pixel(x + j, y + b, c)
            x += 8
