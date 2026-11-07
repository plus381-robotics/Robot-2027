# Probna vožnja: jedan GOTO preko ESP-a. POKREĆE MOTORE.
#
#   mpremote connect /dev/ttyUSB0 run tests/goto_test.py
#
# Pre pokretanja: robot na podu (ili podignut, točkovi u vazduhu), ispred njega bar
# DIST_MM + 20 cm slobodno, ruka na prekidaču za motore. mpremote prekida main.py dok
# test traje; posle testa: mpremote connect /dev/ttyUSB0 reset.
#
# Tok: čeka STM32 -> SET_POSE (0, 0, 0) -> GOTO (DIST_MM, 0) bez završnog ugla ->
# ispisuje STATUS dok ne stigne DONE/FAIL. Ctrl+C, isteklo vreme ili pad veze -> STOP.
import time
from machine import UART

import config as cfg
import protocol as P
from robot import Robot

DIST_MM = 300          # koliko napred
SPEED = 200            # mm/s (regulacija ne ide ispod 150 mm/s)
TIMEOUT_MS = 10000     # posle ovoga STOP

uart = UART(cfg.UART_ID, baudrate=cfg.UART_BAUD, tx=cfg.UART_TX, rx=cfg.UART_RX, rxbuf=1024, timeout=0)
r = Robot(uart)


def poll(ms):
    """Drži vezu (PING) ms milisekundi i vraća događaje."""
    ev = []
    t0 = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), t0) < ms:
        ev += r.poll()
        time.sleep_ms(5)
    return ev


def stop(why):
    print("STOP:", why)
    r.send("STOP")
    poll(200)


print("cekam STM32...")
t0 = time.ticks_ms()
while not r.ok:
    poll(50)
    if time.ticks_diff(time.ticks_ms(), t0) > 3000:
        raise SystemExit("STM32 se ne javlja (ili druga verzija protokola: %s)" % r.version)
print("STM32 OK v%d, status: %s" % (r.version, r.status))

seq = r.send("SET_POSE", x=0, y=0, theta=0)
if not any(e[0] == seq and e[2] == "ok" for e in poll(300)):
    raise SystemExit("SET_POSE nije potvrđen")

seq = r.send("GOTO", x=DIST_MM, y=0, theta=0, flags=P.GotoFlags.NO_THETA, max_speed=SPEED)
print("GOTO poslat (seq %d): %d mm napred, %d mm/s" % (seq, DIST_MM, SPEED))
t0 = time.ticks_ms()
last_print = 0
try:
    while True:
        for s, name, kind, reason in poll(20):
            if s == seq:
                print(name, kind, reason or "")
                if kind in ("done", "fail", "timeout"):
                    raise StopIteration
        now = time.ticks_ms()
        if time.ticks_diff(now, last_print) >= 200 and r.status:
            last_print = now
            st = r.status
            print("x=%5d y=%5d th=%6.1f v=%4d" % (st["x"], st["y"], st["theta"] / 100, st["v"]))
        if not r.alive:
            stop("veza sa STM32 je pala")   # STM32 i sam staje posle 500 ms bez PING-a
            break
        if time.ticks_diff(now, t0) > TIMEOUT_MS:
            stop("isteklo %d ms" % TIMEOUT_MS)
            break
except StopIteration:
    pass
except KeyboardInterrupt:
    stop("Ctrl+C")
st = r.status or {}
print("kraj: x=%s y=%s th=%s" % (st.get("x"), st.get("y"), st.get("theta", 0) / 100))
