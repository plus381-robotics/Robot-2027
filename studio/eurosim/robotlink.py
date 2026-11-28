# Veza sa pravim robotom (ili virtuelnim: sim.py robot) preko postojećeg ESP upload servera i telemetrije:
#   komande  TCP 8267 (tools/espnet.py: prijava izazovom, PUT, RUN, STOP, STAT, LOG)
#   stanje   UDP 8268 (ESP32/lib/telem.py: "WATCH" na 3 s, ESP šalje JSON 10 puta u sekundi)
# Telemetrija se pretvara u isti snimak kao simulacija (frame-ovi, koraci, dnevnik), pa isti prikaz radi
# za simulaciju i za robota, i može da se poredi.
import asyncio
import gzip
import json
import socket
import sys
import time

from . import field, paths
from .record import Recording

TELEM_PORT = 8268
UPLOAD_PORT = 8267
MATCH_RUNNING = 4
# Izvori pravog (ili virtuelnog) robota: sve pravo (Izvori d). Isto u snimku (meta.origin.parts) i u hello sesije
# (session.RobotSource.parts), da Snimci / replay pokažu isto što i sesija.
PARTS = {"pogon": "pravi", "lidar": "pravi", "ir": "pravi", "mehanizmi": "pravi", "protivnici": "pravi"}


def espnet():
    """tools/espnet.py iz repoa (ili iz paketa)."""
    p = str(paths.TOOLS)
    if p not in sys.path:
        sys.path.insert(0, p)
    import espnet as e
    return e


def default_password():
    """Lozinka iz ESP32/webrepl_cfg.py (isto traženje kao tools/espnet.py), ili "" ako je nema."""
    try:
        return espnet().password()
    except (SystemExit, ImportError):            # espnet.password() izlazi kad nema lozinke
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
        self.ended = set()           # (i, ime) koraka čiji je step_end već zabeležen (do sledećeg pokretanja tog koraka)
        self.last_rx = None
        self.esp_mec = None          # stanje meča iz poslednjeg paketa (i bez STM32-a, kad frame-ova nema)
        self.lidar_state = None      # stanje lidara na ESP-u (telem.py "lidar"; nema ključa = ugašen)
        self.lidar_seen = False      # telemetrija je bar jednom javila stanje lidara (stariji firmver ga ne šalje)

    def feed(self, d, now_ms):
        if self.t_first is None:
            self.t_first = d.get("t", 0)
        t = d.get("t", 0) - self.t_first
        self.last_rx = now_ms
        self.esp_mec = d.get("mec", self.esp_mec)
        self.lidar_state = d.get("lidar")
        self.lidar_seen = self.lidar_seen or "lidar" in d
        for line in d.get("log", []):
            self.events.append([t, "log", line])
            self.recent = (self.recent + [(t, line)])[-30:]
        tac = d.get("tac")
        if tac and tac != self.tac:
            self.events.append([t, "tactic", [tac, d.get("side")]])
            self.meta.update(tactic=tac, side=d.get("side"), total=d.get("n"))
            self.ended.clear()
        self.tac = tac
        se = d.get("step_end")       # noviji firmver šalje ishod koraka; dnevnik je samo za stari
        if se and (se[0], se[1]) not in self.ended:
            k = (se[0], se[1])
            self.pending = [p for p in self.pending if (p[0], p[1]) != k]
            self.ended.add(k)
            self.events.append([t, "step_end", list(se)])
        key = (tac, d.get("i"), d.get("step")) if tac and d.get("step") else None
        if self.cur and (key is None or key != self.cur[:3]):
            self._close(t)
        if key and (self.cur is None or key != self.cur[:3]):
            self.cur = key + (d.get("to"), d.get("nx"), t)
            self.ended.discard((key[1], key[2]))
            self.events.append([t, "step", [d.get("i"), d.get("step"), d.get("to"), d.get("nx")]])
        self._resolve(t)
        if "x" in d:
            st = d.get("st", 0)
            self.frames.append({
                "t": t, "x": d["x"], "y": d["y"], "th": d["th"],
                "v": d.get("sp", 0) / 1000, "phase": "MOVING" if st & 1 else "IDLE",
                "match": d.get("mm") if st & (MATCH_RUNNING | 8) else None, "link": bool(d.get("ok")),
                "mec": d.get("mec"), "ok": d.get("ok"), "run": tac, "tac": tac, "i": d.get("i"), "n": d.get("n"),
                "step": d.get("step"), "el": d.get("el"), "to": d.get("to"), "st": st,
            })

    def feed_lidar(self, s, offset):
        """Krug lidara sa robota (telemetrija, ESP32/lib/lidarpkt.py) -> događaj "lidar" kao u simulaciji: tačke
        oko poslednje poze iz telemetrije (odometrija robota). offset: (x, y, z) lidara na robotu, mm."""
        if self.t_first is None:
            self.t_first = s["t"]                 # krug stigao pre prvog JSON paketa: vremenska osnova iz kruga
        pts = []
        for a, d in enumerate(s["bins"]):
            if d:
                pts += (a, d)
        ev = {"pose": None, "o": list(offset), "pts": pts, "near": list(s["near"]) if s["near"] else None,
              "hz": s["hz"]}
        if self.frames:
            f = self.frames[-1]
            ev["pose"] = [f["x"], f["y"], f["th"]]
        else:                                     # nema poze (STM32 nije povezan): centar startne zone
            x0, y0, x1, y1 = field.START_ZONES["zuta"]
            ev["pose"] = [(x0 + x1) // 2, (y0 + y1) // 2, 0]
            ev["nopose"] = True
        self.events.append([s["t"] - self.t_first, "lidar", ev])

    def _close(self, t):
        tac, i, name, to, nx, t0 = self.cur
        if (i, name) not in self.ended:          # ishod je već stigao u telemetriji
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
                self.ended.add((i, name))
            else:
                keep.append([i, name, t0, t1])
        self.pending = keep

    def finish(self):
        if self.cur:
            self._close(self.frames[-1]["t"] if self.frames else 0)
        self._resolve(0, force=True)


class _Udp(asyncio.DatagramProtocol):
    def __init__(self, on, on_lidar=None):
        self.on, self.on_lidar = on, on_lidar

    def datagram_received(self, data, addr):
        if data[:4] == b"LIDR":                   # krug lidara (binarni paket, ESP32/lib/lidarpkt.py)
            if self.on_lidar:
                from .lidarsrc import pkt
                s = pkt().parse_lidar(data)
                if s:
                    self.on_lidar(s)
            return
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
                                  "field": field.describe(), "obstacles": [], "elements": field.elements(),
                                  "frame_ms": 100,
                                  "origin": {"engine": "robot", "parts": dict(PARTS)},
                                  "tactic_sha": None, "scenario": None})
        self.sent = (0, 0)
        self.transport = None
        self.addr = None
        self.t0 = time.monotonic()
        self.packets = 0
        lp = prof.get("lidar", {})
        self.lidar_offset = (lp.get("x", 0), lp.get("y", 0), lp.get("z", 300))
        self.lrec = None                         # „Snimi krugove“ (Test dela → Lidar): {"f", "file", "n"} dok snima

    def now(self):
        return int((time.monotonic() - self.t0) * 1000)

    def _on(self, d):
        self.packets += 1
        self.rec.feed(d, self.now())

    async def start(self):
        loop = asyncio.get_running_loop()
        info = await loop.getaddrinfo(self.host, self.telem_port, family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.addr = info[0][4]
        self.transport, _ = await loop.create_datagram_endpoint(
            lambda: _Udp(self._on, self._on_lidar), local_addr=("0.0.0.0", 0))

    def _on_lidar(self, s):
        self.rec.feed_lidar(s, self.lidar_offset)
        r = self.lrec
        if r:                                     # isti red kao RobotLidar (FileLidar ga čita) + poza iz telemetrije
            ev = self.rec.events[-1][2]
            r["f"].write(json.dumps({"t": s["t"], "bins": s["bins"], "hz": s["hz"],
                                     "near": list(s["near"]) if s["near"] else None,
                                     "pose": None if ev.get("nopose") else ev["pose"]}) + "\n")
            r["n"] += 1

    def record_lidar(self, on):
        """„Snimi krugove“: krugovi lidara sa robota u studio/lidar/<vreme>.jsonl.gz (format lidarsrc.FileLidar,
        uz pozu robota ili null). Vraća (ok, redovi, stanje {"rec": ime | None, "n": krugova})."""
        from . import lidarsrc
        r = self.lrec
        if on:
            if r:
                return True, ["već snima: %s" % r["file"].name], {"rec": r["file"].name, "n": r["n"]}
            d = lidarsrc.lidar_dir()
            d.mkdir(parents=True, exist_ok=True)
            base = time.strftime("%Y%m%d-%H%M%S")
            f, k = d / (base + ".jsonl.gz"), 1
            while f.exists():
                k += 1
                f = d / ("%s-%d.jsonl.gz" % (base, k))
            fh = gzip.open(f, "wt", encoding="utf-8")
            fh.write(json.dumps({"meta": {"source": "robot", "host": self.host, "start": time.time(),
                                          "o": list(self.lidar_offset)}}) + "\n")
            self.lrec = {"f": fh, "file": f, "n": 0}
            return True, ["snima krugove: %s" % f.name], {"rec": f.name, "n": 0}
        if not r:
            return True, ["ne snima"], {"rec": None, "n": 0}
        self.lrec = None
        r["f"].close()
        if not r["n"]:                            # prazan snimak ne ostaje (FileLidar ga ne bi pustio)
            r["file"].unlink(missing_ok=True)
            return True, ["nijedan krug nije stigao: ništa nije snimljeno"], {"rec": None, "n": 0, "saved": None}
        return True, ["sačuvano: %s (%d krugova)" % (r["file"].name, r["n"])], \
            {"rec": None, "n": r["n"], "saved": r["file"].name}

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
                         "running": r.tac, "mec": r.frames[-1]["mec"] if r.frames else None,
                         "esp_mec": r.esp_mec, "lidar_state": r.lidar_state, "lidar_seen": r.lidar_seen})
        self.sent = (len(r.frames), len(r.events))

    async def cmd(self, *args, data=b""):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: command(self.host, self.pw, " ".join(str(a) for a in args),
                                                                data, self.upload_port))

    def close(self):
        if self.transport:
            self.transport.close()
        self.record_lidar(False)
        self.rec.finish()

    def recording(self):
        r = self.rec
        rec = Recording(r.meta)
        rec.frames, rec.events = r.frames, r.events
        rec.result = {"ok": None, "robot": True, "sim_ms": r.frames[-1]["t"] if r.frames else 0}
        return rec.to_dict()
