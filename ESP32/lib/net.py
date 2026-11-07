# WiFi bez blokiranja: poll() u glavnoj petlji. Pokušava poznate mreže redom
# (WIFI_TIMEOUT_S po mreži), a ako nijedna ne uspe, pravi svoju (AP). Zatim WebREPL.
# Dok traje povezivanje, state.MODE je None (ikonica WiFi trepće), a state.SSID je mreža koja se proba.
# Posle povezivanja (STA) se veza proverava jednom u sekundi; ako je nema duže od LOST_MS,
# povezivanje kreće iz početka (ikonica opet trepće). Štednja energije WiFi-ja je isključena
# (manje kašnjenje za upload i telemetriju).
import network
from compat import ticks_ms, ticks_diff

import config as cfg
import secrets
import state

LOST_MS = 5000


class Net:
    def __init__(self, busy=None):
        """busy(): True dok taktika radi ili je meč naoružan. Ponovno povezivanje tada čeka,
        jer connect() ume da blokira petlju ~1 s (a STM32 staje posle 500 ms bez PING-a)."""
        self.busy = busy or (lambda: False)
        network.hostname(cfg.HOSTNAME)
        self.sta = network.WLAN(network.STA_IF)
        self.sta.active(True)
        self.i = -1                     # koja mreža iz secrets.WIFI_NETWORKS se proba
        self.t = 0
        self.done = False
        self._check = 0
        self._lost = None
        self._web = False

    def poll(self):
        if self.done:
            if state.MODE == "STA" and ticks_diff(ticks_ms(), self._check) >= 1000:
                self._check = ticks_ms()
                if self.sta.isconnected():
                    self._lost = None
                elif self._lost is None:
                    self._lost = ticks_ms()
                elif ticks_diff(ticks_ms(), self._lost) > LOST_MS and not self.busy():
                    print("wifi: veza pala, ponovo")
                    state.MODE = state.IP = None
                    self.done, self.i, self._lost = False, -1, None
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
        if state.MODE == "STA":
            try:
                self.sta.config(pm=self.sta.PM_NONE)
            except Exception:
                pass
        if not self._web:
            self._web = True
            try:
                import webrepl
                webrepl.start()
            except Exception as e:
                print("webrepl:", e)
