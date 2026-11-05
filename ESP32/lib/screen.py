# Ekran koji radi i kad OLED nije povezan ili drajver nije instaliran (ispis u konzolu).
from machine import I2C, Pin
import config as cfg

_oled = None
try:
    import ssd1306
    _i2c = I2C(cfg.I2C_ID, sda=Pin(cfg.I2C_SDA), scl=Pin(cfg.I2C_SCL), freq=400000)
    if 0x3C in _i2c.scan():
        _oled = ssd1306.SSD1306_I2C(128, 64, _i2c)
except Exception as e:
    print("ekran nije dostupan:", e)


def show(*lines, log=True):
    if _oled:
        _oled.fill(0)
        for i, l in enumerate(lines[:6]):
            _oled.text(str(l)[:16], 0, i * 10)
        _oled.show()
    if log:
        print(" | ".join(str(l) for l in lines))
