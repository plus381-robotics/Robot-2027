# 1) WiFi + WebREPL  2) meni na OLED-u (enkoder + tasteri)  3) veza sa STM32
# Ctrl+C u bilo kom trenutku prekida program (mpremote i Thonny to rade automatski).
import time
from machine import UART

import config as cfg
import net
from screen import show, oled

show("eurokik", "start...", "WiFi...")
net.connect()

from robot import Robot
from settings import Settings
from inputs import Inputs
from app import App

uart = UART(cfg.UART_ID, baudrate=cfg.UART_BAUD, tx=cfg.UART_TX, rx=cfg.UART_RX, rxbuf=1024, timeout=0)
st = Settings()
app = App(Robot(uart), st, oled)
inp = Inputs(cfg, lambda: st["enc_rev"])
gui = app.ui

while True:
    app.update()                                   # UART: PING, STATUS, odgovori
    for ev in inp.poll(gui.top.wants_hold):
        if ev[0] == "stop":
            app.stop()
        else:
            gui.input(*ev)
    gui.hold(inp.hold_ms)
    gui.tick()                                     # crta samo kad se nešto promenilo
    time.sleep_ms(5)
