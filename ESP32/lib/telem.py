# Telemetrija ka laptopu preko UDP-a (port 8268): python tools/watch.py
# Laptop pošalje "WATCH"; ESP mu 10 puta u sekundi šalje jedan JSON red sa stanjem robota,
# taktike i meča, plus nove redove dnevnika. Pretplata ističe posle SUB_MS ako se ne obnovi.
# Samo čitanje: preko ovoga se ništa ne pokreće, pa nema lozinke.
import socket
import json
from compat import ticks_ms, ticks_diff
from tactic import tracker

PORT = 8268
PERIOD_MS = 100
SUB_MS = 10000


class Telem:
    def __init__(self, app, port=PORT):
        self.app, self.port = app, port
        self.s = None
        self.sub = None                 # adresa laptopa
        self.t_sub = self.t_send = 0
        self.log_n = 0

    def poll(self):
        import state
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
        try:
            d, addr = self.s.recvfrom(64)
            if d.startswith(b"WATCH"):
                if self.sub != addr:
                    self.log_n = max(0, self.app.log_n - 10)     # poslednjih 10 redova odmah
                self.sub, self.t_sub = addr, ticks_ms()
        except OSError:
            pass
        now = ticks_ms()
        if self.sub is None:
            return
        if ticks_diff(now, self.t_sub) > SUB_MS:
            self.sub = None
            return
        if ticks_diff(now, self.t_send) < PERIOD_MS:
            return
        self.t_send = now
        try:
            self.s.sendto(json.dumps(self.snapshot()).encode(), self.sub)
        except OSError:
            pass

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
        first = a.log_n - len(a.log)
        new = [l for i, l in enumerate(a.log) if first + i >= self.log_n]
        self.log_n = a.log_n
        if new:
            m["log"] = new
        return m
