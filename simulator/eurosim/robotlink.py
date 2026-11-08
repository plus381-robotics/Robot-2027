# Veza sa pravim robotom (ili virtuelnim: sim.py robot) preko postojećeg ESP upload servera i telemetrije:
#   komande  TCP 8267 (tools/espnet.py: prijava izazovom, PUT, RUN, STOP, STAT, LOG)
#   stanje   UDP 8268 (ESP32/lib/telem.py: "WATCH" na 3 s, ESP šalje JSON 10 puta u sekundi)
# Telemetrija se pretvara u isti snimak kao simulacija (frame-ovi, koraci, dnevnik), pa isti prikaz radi
# za simulaciju i za robota, i može da se poredi.
import asyncio
import json
import socket
import sys
import time

from . import field, paths

TELEM_PORT = 8268
UPLOAD_PORT = 8267
MATCH_RUNNING = 4


def espnet():
    """tools/espnet.py iz repoa (ili iz paketa)."""
    p = str(paths.TOOLS)
    if p not in sys.path:
        sys.path.insert(0, p)
    import espnet as e
    return e


def default_password():
    """Lozinka iz ESP32/webrepl_cfg.py (kao tools/*.py), ako postoji."""
    import re
    f = paths.ESP / "webrepl_cfg.py"
    if f.exists():
        m = re.search(r"PASS\s*=\s*['\"](.*)['\"]", f.read_text())
        if m:
            return m.group(1)
    return ""


def command(host, pw, cmd, data=b"", port=UPLOAD_PORT, timeout=15):
    """Jedna komanda upload serveru. Vraća (ok, redovi). Ne baca izuzetke (espnet radi sys.exit)."""
    try:
        lines = espnet().query(host, pw, cmd, data, timeout=timeout, port=port, tries=2)
    except SystemExit as e:
        return False, [str(e)]
    except Exception as e:                       # noqa: BLE001
        return False, ["%s: %s" % (type(e).__name__, e)]
    return bool(lines) and lines[-1].startswith("OK"), lines


class TelemRecorder:
    """JSON telemetrije -> frame-ovi i događaji (isti oblik kao Sim.rec)."""

    def __init__(self, meta):
        self.meta = meta
        self.frames, self.events = [], []
        self.t_first = None
        self.cur = None              # (tac, i, step, to, nx, t)
        self.tac = None
        self.pending = []            # zatvoreni koraci koji čekaju red dnevnika sa ishodom
        self.recent = []             # (t, red) poslednji redovi dnevnika
        self.last_rx = None

    def feed(self, d, now_ms):
        if self.t_first is None:
            self.t_first = d.get("t", 0)
        t = d.get("t", 0) - self.t_first
        self.last_rx = now_ms
        for line in d.get("log", []):
            self.events.append([t, "log", line])
            self.recent = (self.recent + [(t, line)])[-30:]
        tac = d.get("tac")
        if tac and tac != self.tac:
            self.events.append([t, "tactic", [tac, d.get("side")]])
            self.meta.update(tactic=tac, side=d.get("side"), total=d.get("n"))
        self.tac = tac
        key = (tac, d.get("i"), d.get("step")) if tac and d.get("step") else None
        if self.cur and (key is None or key != self.cur[:3]):
            self._close(t)
        if key and (self.cur is None or key != self.cur[:3]):
            self.cur = key + (d.get("to"), d.get("nx"), t)
            self.events.append([t, "step", [d.get("i"), d.get("step"), d.get("to"), d.get("nx")]])
        self._resolve(t)
        if "x" in d:
            st = d.get("st", 0)
            self.frames.append({
                "t": t, "x": d["x"], "y": d["y"], "th": d["th"], "ox": d["x"], "oy": d["y"], "oth": d["th"],
                "v": d.get("sp", 0) / 1000, "w": None, "vl": None, "vr": None, "v_ref": None, "w_ref": None,
                "phase": "MOVING" if st & 1 else "IDLE", "reg": "", "ms": "", "stuck": False, "ir": 0,
                "match": d.get("mm") if st & (MATCH_RUNNING | 8) else None, "link": bool(d.get("ok")),
                "mec": d.get("mec"), "ok": d.get("ok"), "run": tac, "tac": tac, "i": d.get("i"), "n": d.get("n"),
                "step": d.get("step"), "el": d.get("el"), "to": d.get("to"), "st": st,
            })

    def _close(self, t):
        tac, i, name, to, nx, t0 = self.cur
        self.pending.append([i, name, t0, t])
        self.cur = None

    def _resolve(self, t, force=False):
        """Ishod koraka iz dnevnika (tac.py piše "<korak>: OK 1.3s" ili "<korak>: BLOCKED")."""
        keep = []
        for i, name, t0, t1 in self.pending:
            res = None
            for tl, line in self.recent:
                if tl >= t0 and line.startswith(name + ": "):
                    rest = line[len(name) + 2:]
                    res = (True, None) if rest.startswith("OK") or rest.startswith("kraj po STATUS") else \
                        (False, rest.split()[0] if rest else "FAIL")
            if res or force or t - t1 > 1500:
                ok, reason = res or (None, "?")
                self.events.append([t1, "step_end", [i, name, ok, reason, t1 - t0]])
            else:
                keep.append([i, name, t0, t1])
        self.pending = keep

    def finish(self):
        if self.cur:
            self._close(self.frames[-1]["t"] if self.frames else 0)
        self._resolve(0, force=True)


class _Udp(asyncio.DatagramProtocol):
    def __init__(self, on):
        self.on = on

    def datagram_received(self, data, addr):
        try:
            self.on(json.loads(data))
        except ValueError:
            pass


class RobotLink:
    """Jedna veza (jedan browser tab). emit(dict) dobija nove podatke ~10 puta u sekundi."""

    def __init__(self, host, pw, emit, prof, upload_port=UPLOAD_PORT, telem_port=TELEM_PORT):
        self.host, self.pw, self.emit = host, pw, emit
        self.upload_port, self.telem_port = upload_port, telem_port
        self.rec = TelemRecorder({"tactic": None, "side": None, "mode": "robot", "host": host,
                                  "profile": prof.get("name"), "body": prof["body"], "drive": prof["drive"],
                                  "field": field.describe(), "obstacles": [], "frame_ms": 100})
        self.sent = (0, 0)
        self.transport = None
        self.addr = None
        self.t0 = time.monotonic()
        self.packets = 0

    def now(self):
        return int((time.monotonic() - self.t0) * 1000)

    def _on(self, d):
        self.packets += 1
        self.rec.feed(d, self.now())

    async def start(self):
        loop = asyncio.get_running_loop()
        info = await loop.getaddrinfo(self.host, self.telem_port, family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.addr = info[0][4]
        self.transport, _ = await loop.create_datagram_endpoint(lambda: _Udp(self._on), local_addr=("0.0.0.0", 0))

    async def run(self):
        """Pretplata na telemetriju i slanje novih podataka dok se ne otkaže."""
        t_sub = 0
        while True:
            if time.monotonic() - t_sub > 3:
                t_sub = time.monotonic()
                try:
                    self.transport.sendto(b"WATCH", self.addr)
                except OSError:
                    pass
            await asyncio.sleep(0.1)
            await self.flush()

    async def flush(self):
        r = self.rec
        nf, ne = self.sent
        age = None if r.last_rx is None else self.now() - r.last_rx
        await self.emit({"frames": r.frames[nf:], "events": r.events[ne:], "meta": r.meta if nf == 0 else None,
                         "t": r.frames[-1]["t"] if r.frames else 0, "age": age, "packets": self.packets,
                         "running": r.tac, "mec": r.frames[-1]["mec"] if r.frames else None})
        self.sent = (len(r.frames), len(r.events))

    async def cmd(self, *args, data=b""):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: command(self.host, self.pw, " ".join(str(a) for a in args),
                                                                data, self.upload_port))

    def close(self):
        if self.transport:
            self.transport.close()
        self.rec.finish()

    def recording(self):
        r = self.rec
        return {"version": 1, "meta": r.meta, "frames": r.frames, "events": r.events,
                "result": {"ok": None, "robot": True, "sim_ms": r.frames[-1]["t"] if r.frames else 0}}
