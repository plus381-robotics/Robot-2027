# Ekran koji radi i kad OLED nije povezan ili drajver nije instaliran (ispis u konzolu).
# oled: SSD1306 objekat ili None. show(): jednostavan ispis dok se ne pokrene meni (WiFi...).
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


def show(*lines, log=True):
    """Prvi red je naslov (inverzna traka), ostali ispod."""
    if oled:
        oled.fill(0)
        if lines:
            oled.fill_rect(0, 0, 128, 10, 1)
            oled.text(str(lines[0])[:16], 2, 1, 0)
        for i, l in enumerate(lines[1:6]):
            oled.text(str(l)[:16], 0, 13 + i * 10)
        oled.show()
    if log:
        print(" | ".join(str(l) for l in lines))
