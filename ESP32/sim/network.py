# Lažni network modul (testovi): WLAN sa ručno podešenom vezom.
STA_IF, AP_IF, AUTH_WPA2_PSK = 0, 1, 3
_ifaces = {}
connected = [False]             # test menja: network.connected[0] = True/False


def hostname(n=None):
    pass


class WLAN:
    PM_NONE = 0

    def __new__(cls, i):
        if i not in _ifaces:
            o = object.__new__(cls)
            o.i, o._active, o.cfg, o.tries = i, False, {}, []
            _ifaces[i] = o
        return _ifaces[i]

    def __init__(self, i):
        pass

    def active(self, v=None):
        if v is None:
            return self._active
        self._active = v

    def connect(self, ssid, pw):
        self.tries.append(ssid)

    def disconnect(self):
        pass

    def isconnected(self):
        return connected[0]

    def ifconfig(self):
        return ("10.0.0.5", "255.255.255.0", "10.0.0.1", "10.0.0.1")

    def config(self, **k):
        self.cfg.update(k)
