# 1) WiFi + WebREPL  2) test protokola sa Nucleom
# Ctrl+C u bilo kom trenutku prekida program (mpremote i Thonny to rade automatski).
import time
from machine import UART

import config as cfg
import state
import net
import protocol as P
from link import build_frame, FrameParser
from screen import show

show("eurokik", "start...", "WiFi...")
net.connect()
show("eurokik.local", state.MODE + " " + state.IP, state.SSID, "", "WebREPL :8266")


def send(uart, name, seq=0, **fields):
    t, payload = P.encode(name, **fields)
    uart.write(build_frame(t, seq, payload))


uart = UART(cfg.UART_ID, baudrate=cfg.UART_BAUD, tx=cfg.UART_TX, rx=cfg.UART_RX, rxbuf=1024, timeout=0)
parser = FrameParser()
version = status = None
last_ping = last_rx = last_draw = 0
pose_sent = False
while True:
    now = time.ticks_ms()
    if time.ticks_diff(now, last_ping) >= 150:          # heartbeat (Nucleo staje posle 500 ms tišine)
        send(uart, "PING")
        last_ping = now
    data = uart.read()
    if data:
        for t, seq, payload in parser.feed(data):
            last_rx = now
            name, d = P.decode(t, payload)
            if name == "PONG":
                version = d["version"]
            elif name == "STATUS":
                status = d
            elif name == "LOG":
                print("[nucleo]", d["text"])
            elif name in ("ACK", "DONE", "FAIL"):
                print(name, "seq", seq, d)
    if version == P.VERSION and not pose_sent:          # probna komanda: postavi poziciju
        send(uart, "SET_POSE", 1, x=250, y=1000, theta=0)
        pose_sent = True
    if time.ticks_diff(now, last_draw) >= 200:
        last_draw = now
        alive = time.ticks_diff(now, last_rx) < 500
        if not alive:
            link = "Nucleo: nema"
        elif version != P.VERSION:
            link = "verzija N%s/E%d" % (version, P.VERSION)
        else:
            link = "Nucleo OK v%d" % version
        s = status or {}
        show("eurokik.local", link,
             "x=%s y=%s" % (s.get("x", "-"), s.get("y", "-")),
             "th=%s" % (s.get("theta", 0) / 100 if s else "-"),
             "v=%s mm/s" % s.get("v", "-"),
             "greske: %d" % parser.errors, log=False)
    time.sleep_ms(5)
