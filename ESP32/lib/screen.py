# OLED (SSD1306 128x64 na I2C). oled je None ako ekran nije povezan ili drajver nije instaliran;
# tada sve radi isto, samo se ništa ne crta (poruke idu u konzolu).
from machine import I2C, Pin
import config as cfg

oled = None
try:
    import ssd1306
    _i2c = I2C(cfg.I2C_ID, sda=Pin(cfg.I2C_SDA), scl=Pin(cfg.I2C_SCL), freq=400000)
    if 0x3C in _i2c.scan():
        oled = ssd1306.SSD1306_I2C(128, 64, _i2c)
except Exception as e:
    print("ekran nije dostupan:", e)
