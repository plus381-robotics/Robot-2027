# Ekran sa telemetrijom (enkoder + tasteri), veza sa STM32, WiFi + WebREPL i upload u pozadini,
# i pokretanje taktika iz /tactics (sa ekrana ili preko WiFi-ja: tools/tactic.py).
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
from tactic import tracker
import tac

st = Settings()
UART_ARGS = dict(baudrate=cfg.UART_BAUD, tx=cfg.UART_TX, rx=cfg.UART_RX, rxbuf=1024)
uart = UART(cfg.UART_ID, timeout=0, **UART_ARGS)
app = App(Robot(uart), st, oled)               # odmah primenjuje kontrast i okretanje ekrana
inp = Inputs(cfg, lambda: st["enc_rev"])
net = Net()                                    # ne blokira: ikonica WiFi trepće dok se povezuje
gui = app.ui
upload = Upload(app, UART_ARGS, cfg)          # port 8267: esp_push, flash_stm32, tactic


def step():
    """Jedan krug glavne petlje. Taktika ga zove dok čeka (tac.py), pa ekran i veza rade."""
    net.poll()
    upload.poll()
    app.update()                               # UART: PING, STATUS, odgovori
    for ev in inp.poll(gui.top.wants_hold):
        if ev[0] == "stop":
            app.stop()                         # i prekida taktiku
        else:
            gui.input(*ev)
    gui.hold(inp.hold_ms)
    gui.tick()                                 # crta samo kad se nešto promenilo
    time.sleep_ms(5)


def run_tactic(name):
    app.running, app.abort = name, None
    tracker.start(name)
    app.tlog("START " + name)
    t0 = time.ticks_ms()
    try:
        with open("/tactics/%s.py" % name) as f:
            src = f.read()
        exec(src, {"__name__": "taktika"})
        tracker.finish()
        app.tlog("KRAJ %s %.1fs" % (name, time.ticks_diff(time.ticks_ms(), t0) / 1000))
    except tac.Abort as e:
        app.robot.send("STOP")
        tracker.fail(str(e))
        tracker.finish()
        app.tlog("PREKID: %s" % e)
    except Exception as e:
        app.robot.send("STOP")
        tracker.fail("GRESKA")
        tracker.finish()
        app.tlog("GRESKA: %r" % e)
        gui.toast("taktika: greska", 3000, alert=True)
    app.running = None


app.pump = step
tac.app = app
while True:
    step()
    if app.request:
        name, app.request = app.request, None
        run_tactic(name)
