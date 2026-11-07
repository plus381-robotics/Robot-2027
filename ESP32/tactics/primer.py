# Primer taktike. POKREĆE MOTORE.
#   mpremote connect /dev/ttyUSB0 run tactics/primer.py
# Ctrl+C šalje STOP. Posle: mpremote connect /dev/ttyUSB0 reset (vraća ekran).
#
# Jedinice: mm, ugao u stotinkama stepena (9000 = 90°), 0° = +x osa, pozitivno = levo (CCW).
# do() šalje komandu i čeka kraj: kretanje čeka DONE/FAIL, ostalo samo ACK. Vraća True ako je uspelo.
import time
from machine import UART

import config as cfg
import protocol as P
from robot import Robot

r = Robot(UART(cfg.UART_ID, baudrate=cfg.UART_BAUD, tx=cfg.UART_TX, rx=cfg.UART_RX, rxbuf=1024, timeout=0))
MOTION = ("GOTO", "ROTATE", "MOVE")


def do(name, timeout_ms=10000, **fields):
    seq = r.send(name, **fields)
    t0 = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), t0) < timeout_ms:
        for s, _, kind, reason in r.poll():       # poll() i drži vezu (PING)
            if s != seq:
                continue
            if kind == "ok" and name in MOTION:
                continue                          # ACK: krenuo, čekaj DONE/FAIL
            print("%-9s %s -> %s %s" % (name, fields, kind, reason or ""))
            return kind in ("ok", "done")
        time.sleep_ms(5)
    r.send("STOP")
    print(name, "-> isteklo vreme, STOP")
    return False


def wait_stm32():
    t0 = time.ticks_ms()
    while not r.ok:
        r.poll()
        time.sleep_ms(20)
        if time.ticks_diff(time.ticks_ms(), t0) > 3000:
            raise SystemExit("STM32 se ne javlja (verzija: %s)" % r.version)


try:
    wait_stm32()
    do("SET_POSE", x=250, y=1000, theta=0)
    if not do("GOTO", x=600, y=1000, theta=0, flags=P.GotoFlags.NO_THETA, max_speed=300):
        raise SystemExit("GOTO nije uspeo")
    do("ROTATE", theta=9000)
    do("MOVE", dist=-200, max_speed=200)
    print("kraj, poza:", r.status)
except KeyboardInterrupt:
    r.send("STOP")
    r.poll()
    print("STOP (Ctrl+C)")
