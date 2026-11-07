import framebuf
class SSD1306_I2C(framebuf.FrameBuffer):
    def __init__(self, w=128, h=64, i2c=None):
        super().__init__(None, w, h)
        self.frames, self.on, self.contrast_v, self.flip = [], True, 255, 0
    def show(self): self.frames.append([r[:] for r in self.px])
    @property
    def buffer(self):          # kao pravi drajver: slika u memoriji (ovde za poređenje)
        return bytes(b for row in self.px for b in row)
    def contrast(self, v): self.contrast_v = v
    def rotate(self, f): self.flip = f
    def poweroff(self): self.on = False
    def poweron(self): self.on = True
