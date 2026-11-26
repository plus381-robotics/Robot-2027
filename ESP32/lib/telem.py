# Telemetrija ka laptopu preko UDP-a (port 8268): python tools/watch.py, simulator (Robot, izvor lidara)
# Laptop pošalje "WATCH"; ESP mu 10 puta u sekundi šalje jedan JSON red sa stanjem robota,
# taktike i meča, plus nove redove dnevnika. Pretplata ističe posle SUB_MS ako se ne obnovi.
# Do MAX_SUBS pretplatnika u isto vreme (npr. Robot u simulatoru i izvor lidara za simulaciju).
#
# Lidar: dok lidar radi (Meni -> Lidar test, ili upaljen preko WiFi-ja komandom LIDAR ON, upload.py),
# svaki završen krug ide pretplatnicima kao binarni paket (LIDAR_FMT + 360 x uint16 mm po stepenu robota,
# 0 = nema tačke; isti binovi kao lib/lidar.py). Lidar upaljen preko WiFi-ja ovde se i čita, a gasi se sam
# kad nema pretplatnika SUB_MS ili kad se robot naoruža / taktika krene (meč ima prednost).
# Samo čitanje: preko ovoga se ništa ne pokreće, pa nema lozinke (LIDAR ON ide preko upload servera).
import socket
import json
import sys
from compat import ticks_ms, ticks_diff
from tactic import tracker
from lidarpkt import lidar_packet, parse_lidar  # noqa: F401  (format paketa: lidarpkt.py)

PORT = 8268
PERIOD_MS = 100
SUB_MS = 10000
MAX_SUBS = 3
REMOTE_GRACE_MS = 3000                  # LIDAR ON bez pretplatnika: toliko se čeka (WATCH stiže posle ON)
def _lidar():
    """lib/lidar.py uređaj ako je već otvoren (Lidar test ili LIDAR ON), inače None (bez uvoza modula)."""
    m = sys.modules.get("lidar")
    return getattr(m, "_dev", None) if m else None


class Telem:
    def __init__(self, app, port=PORT):
        self.app, self.port = app, port
        self.s = None
        self.subs = {}                  # adresa laptopa -> kad je poslednji put poslao WATCH
        self.t_send = 0
        self.log_n = 0
        self._scan = None               # broj kruga lidara koji je poslednji poslat
        self._buf = None

    @property
    def sub(self):                      # staro ime (jedan pretplatnik)
        return next(iter(self.subs), None)

    def poll(self):
        import state
        self._lidar_remote()
        if self.s is None:
            if not state.MODE:
                return
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.bind(("0.0.0.0", self.port))
                s.setblocking(False)
                self.s = s
            except OSError as e:
                print("telem:", e)
                return
        now = ticks_ms()
        try:
            d, addr = self.s.recvfrom(64)
            if d.startswith(b"WATCH"):
                if not self.subs:
                    self.log_n = max(0, self.app.log_n - 10)     # poslednjih 10 redova odmah
                if addr not in self.subs and len(self.subs) >= MAX_SUBS:
                    del self.subs[min(self.subs, key=lambda a: self.subs[a])]   # najstariji ustupa mesto
                self.subs[addr] = now
        except OSError:
            pass
        for a in [a for a, t in self.subs.items() if ticks_diff(now, t) > SUB_MS]:
            del self.subs[a]
        if not self.subs:
            return
        self._send_lidar(now)
        if ticks_diff(now, self.t_send) < PERIOD_MS:
            return
        self.t_send = now
        data = json.dumps(self.snapshot()).encode()
        for a in self.subs:
            try:
                self.s.sendto(data, a)
            except OSError:
                pass

    def _send_lidar(self, now):
        L = _lidar()
        if L is None or not L.scanning or L.scans == self._scan:
            return
        self._scan = L.scans
        self._buf = lidar_packet(L, now, self._buf)
        for a in self.subs:
            try:
                self.s.sendto(self._buf, a)
            except OSError:
                pass

    def _lidar_remote(self):
        """Lidar upaljen preko WiFi-ja (app.lidar_remote = vreme): čita se ovde; gasi se kad nema
        pretplatnika (ističu posle SUB_MS bez WATCH, pa još REMOTE_GRACE_MS) ili kad robot postane zauzet."""
        a = self.app
        t = getattr(a, "lidar_remote", None)
        if t is None:
            return
        L = _lidar()
        now = ticks_ms()
        if self.subs:
            a.lidar_remote = now
        if L is None or a.busy() or ticks_diff(now, a.lidar_remote) > REMOTE_GRACE_MS:
            a.lidar_remote = None
            if L is not None and type(a.ui.top).__name__ != "LidarScreen":
                L.stop()
            return
        if type(a.ui.top).__name__ != "LidarScreen":     # ekran Lidar test sam čita lidar
            L.poll()

    def snapshot(self):
        a, r = self.app, self.app.robot
        s = r.status if r.alive else None
        m = {"t": ticks_ms(), "ok": r.ok, "v": r.version}
        if s:
            m.update(x=s["x"], y=s["y"], th=s["theta"] / 100, sp=s["v"], st=s["state"], mm=s["match_ms"])
        if tracker.running:
            m.update(tac=tracker.name, i=tracker.idx, n=tracker.total, step=tracker.step_name,
                     el=tracker.elapsed(), to=tracker.timeout_ms, nx=tracker.next)
        m["side"] = a.side
        m["mec"] = a.match.state
        L = _lidar()
        if L is not None and L.state != "off":
            m["lidar"] = L.state
        first = a.log_n - len(a.log)
        new = [l for i, l in enumerate(a.log) if first + i >= self.log_n]
        self.log_n = a.log_n
        if new:
            m["log"] = new
        return m
