# Ekran sa telemetrijom (enkoder + tasteri), veza sa STM32 i WiFi + WebREPL u pozadini.
# Ctrl+C u bilo kom trenutku prekida program (mpremote i Thonny to rade automatski).
import time
from machine import UART

import config as cfg
from screen import oled
from net import Net
from robot import Robot
from settings import Settings
from inputs import Inputs
from app import App
from upload import Upload

st = Settings()
UART_ARGS = dict(baudrate=cfg.UART_BAUD, tx=cfg.UART_TX, rx=cfg.UART_RX, rxbuf=1024)
uart = UART(cfg.UART_ID, timeout=0, **UART_ARGS)
app = App(Robot(uart), st, oled)               # odmah primenjuje kontrast i okretanje ekrana
inp = Inputs(cfg, lambda: st["enc_rev"])
net = Net()                                    # ne blokira: ikonica WiFi trepće dok se povezuje
gui = app.ui
upload = Upload(app, UART_ARGS, cfg)          # port 8267: tools/esp_push.py i tools/flash_stm32.py

while True:
    net.poll()
    upload.poll()
    app.update()                               # UART: PING, STATUS, odgovori
    for ev in inp.poll(gui.top.wants_hold):
        if ev[0] == "stop":
            app.stop()
        else:
            gui.input(*ev)
    gui.hold(inp.hold_ms)
    gui.tick()                                 # crta samo kad se nešto promenilo
    time.sleep_ms(5)
