# WiFi: skenira, povezuje se na prvu poznatu mrežu, inače pravi svoju. Zatim WebREPL.
import time
import network

import config as cfg
import secrets
import state
from screen import show


def connect():
    network.hostname(cfg.HOSTNAME)
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    try:
        visible = {n[0].decode() for n in sta.scan()}
    except OSError:
        visible = set()
    for ssid, pw in secrets.WIFI_NETWORKS:
        if ssid not in visible:
            continue
        show("eurokik", "WiFi: " + ssid, "povezujem...")
        try:
            sta.connect(ssid, pw)
        except OSError as e:
            print("connect:", e)
        t0 = time.time()
        while not sta.isconnected() and time.time() - t0 < cfg.WIFI_TIMEOUT_S:
            time.sleep(0.2)
        if sta.isconnected():
            state.MODE, state.SSID, state.IP = "STA", ssid, sta.ifconfig()[0]
            break
        sta.disconnect()
    if state.MODE != "STA":
        sta.active(False)
        ap = network.WLAN(network.AP_IF)
        ap.active(True)
        ap.config(essid=secrets.AP_SSID, password=secrets.AP_PASS, authmode=network.AUTH_WPA2_PSK)
        state.MODE, state.SSID, state.IP = "AP", secrets.AP_SSID, ap.ifconfig()[0]
    try:
        import webrepl
        webrepl.start()
    except Exception as e:
        print("webrepl:", e)
