# WiFi bez blokiranja: poll() u glavnoj petlji. Pokušava poznate mreže redom
# (WIFI_TIMEOUT_S po mreži), a ako nijedna ne uspe, pravi svoju (AP). Zatim WebREPL.
# Dok traje povezivanje, state.MODE je None (ikonica WiFi trepće), a state.SSID je mreža koja se proba.
import network
from compat import ticks_ms, ticks_diff

import config as cfg
import secrets
import state


class Net:
    def __init__(self):
        network.hostname(cfg.HOSTNAME)
        self.sta = network.WLAN(network.STA_IF)
        self.sta.active(True)
        self.i = -1                     # koja mreža iz secrets.WIFI_NETWORKS se proba
        self.t = 0
        self.done = False

    def poll(self):
        if self.done:
            return
        if self.i >= 0 and self.sta.isconnected():
            state.MODE, state.IP = "STA", self.sta.ifconfig()[0]
            self._finish()
            return
        if self.i >= 0 and ticks_diff(ticks_ms(), self.t) < cfg.WIFI_TIMEOUT_S * 1000:
            return
        if self.i >= 0:
            self.sta.disconnect()
        self.i += 1
        if self.i >= len(secrets.WIFI_NETWORKS):
            self.sta.active(False)
            ap = network.WLAN(network.AP_IF)
            ap.active(True)
            ap.config(essid=secrets.AP_SSID, password=secrets.AP_PASS, authmode=network.AUTH_WPA2_PSK)
            state.MODE, state.SSID, state.IP = "AP", secrets.AP_SSID, ap.ifconfig()[0]
            self._finish()
            return
        ssid, pw = secrets.WIFI_NETWORKS[self.i]
        state.SSID = ssid
        self.t = ticks_ms()
        try:
            self.sta.connect(ssid, pw)
        except OSError as e:
            print("wifi:", ssid, e)

    def _finish(self):
        self.done = True
        print("wifi:", state.MODE, state.SSID, state.IP)
        try:
            import webrepl
            webrepl.start()
        except Exception as e:
            print("webrepl:", e)
