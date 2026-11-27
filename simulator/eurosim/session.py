# Sesija: simulacija, pravi robot i snimak iza istog oblika (Source), da ih server služi na istom WebSocket-u.
# poll() je adapter nad postojećim "push" stilom: svaki izvor skuplja šta je stiglo od prošlog poll()-a.
# Bez aiohttp (čist asyncio + postojeći moduli), pa se testira bez servera.
import asyncio
import multiprocessing as mp
import time

from . import paths, tactics as tacmod
from .record import Recording

CAPS = frozenset({"pause", "speed", "esp_screen", "esp_buttons", "arm", "cord", "test", "push", "run", "stop",
                  "opponents", "lidar", "manual", "seek"})

UNSUPPORTED = ["nepodržano"]


class Buffer:
    """Skuplja podatke oblika {"frames", "events", "meta", "t", ...} između dva poll()-a."""

    def __init__(self):
        self.t, self.extra = None, {}          # zadnje stanje preživljava prazne poll()-ove
        self.reset()

    def reset(self):
        self.frames, self.events, self.meta = [], [], None

    def add(self, d):
        self.frames += d.get("frames") or []
        self.events += d.get("events") or []
        if d.get("meta"):                      # novija slika meta podataka pobeđuje
            self.meta = d["meta"]
        self.t = d.get("t", self.t)
        for k, v in d.items():
            if k not in ("frames", "events", "meta", "t", "age"):
                self.extra[k] = v

    def take(self, age, final=False):
        out = {**self.extra, "frames": self.frames, "events": self.events, "meta": self.meta,
               "t": self.t if self.t is not None else 0, "age": age, "final": final}
        self.reset()
        return out


class Source:
    kind = ""
    capabilities = frozenset()

    async def start(self):
        pass

    async def poll(self):
        return {"frames": [], "events": [], "meta": None, "t": 0, "age": None, "final": False}

    async def command(self, c):
        return self.unsupported(c)

    async def close(self):
        return {}

    @staticmethod
    def unsupported(c):
        return {"cmd": str(c[0]) if c else "", "ok": False, "lines": list(UNSUPPORTED)}

    @staticmethod
    def reply(c, ok=True, lines=()):
        return {"cmd": c[0], "ok": ok, "lines": list(lines)}


# ---------------- simulacija ----------------

SIM_CMD_CAP = {"btn": "esp_buttons", "rot": "esp_buttons", "cord": "cord", "arm": "arm", "test": "test",
               "stop": "stop", "pause": "pause", "speed": "speed", "obstacles": "opponents", "place": "opponents",
               "elements": "test", "ir_mask": "test", "side": "test", "stm_reset": "test", "stm_hang": "test"}


class SimSource(Source):
    """Live simulacija u posebnom procesu (api/runs.py _live_worker). kw kao u server.live()."""
    kind = "sim"

    def __init__(self, kw):
        self.kw = dict(kw)
        caps = {"pause", "speed", "esp_screen", "esp_buttons", "arm", "cord", "test", "stop", "opponents", "lidar"}
        if str(self.kw.get("lidar_spec") or "").startswith("robot"):      # pravi lidar: ×1, bez pauze
            caps -= {"pause", "speed"}
        self.capabilities = frozenset(caps)
        self.buf = Buffer()
        self.proc = self.conn = None
        self.rec = None              # završni snimak ("end")
        self.error = None
        self.done = False

    async def start(self):
        from .api.runs import _live_worker           # lazy: api/ uvozi aiohttp
        ctx = mp.get_context("spawn")
        self.conn, child = ctx.Pipe()
        self.proc = ctx.Process(target=_live_worker, args=(child, self.kw), daemon=True)
        self.proc.start()
        child.close()

    def _drain(self):
        while not self.done:
            try:
                if not self.conn.poll(0):
                    if not self.proc.is_alive() and not self.conn.poll(0):
                        self.error = self.error or "proces simulacije je stao"
                        self.done = True
                    return
                kind, d = self.conn.recv()
            except (EOFError, OSError):
                self.error = self.error or "proces simulacije je stao"
                self.done = True
                return
            if kind == "data":
                self.buf.add(d)
            elif kind == "end":
                self.rec, self.done = d, True
            else:
                self.error, self.done = d, True

    async def poll(self):
        self._drain()
        out = self.buf.take(None, final=self.done)
        if self.error:
            out["error"] = self.error
        return out

    async def command(self, c):
        k = c[0] if c else ""
        if SIM_CMD_CAP.get(k) not in self.capabilities or self.done:
            return self.unsupported(c)
        try:
            self.conn.send(tuple(c))
        except (OSError, BrokenPipeError):
            return self.reply(c, False, ["proces simulacije je stao"])
        return self.reply(c)

    async def close(self):
        if self.proc is None:
            return self.rec or {}
        loop = asyncio.get_running_loop()

        def finish():
            if not self.done:
                try:
                    self.conn.send(("quit",))
                except (OSError, BrokenPipeError):
                    pass
                try:
                    while self.conn.poll(5):
                        kind, d = self.conn.recv()
                        if kind == "end":
                            self.rec = d
                            break
                        if kind == "err":
                            break
                except (EOFError, OSError):
                    pass
            self.proc.join(1)
            if self.proc.is_alive():
                self.proc.kill()
                self.proc.join(1)
            self.conn.close()
        await loop.run_in_executor(None, finish)
        self.done = True
        return self.rec or {}


# ---------------- pravi (ili virtuelni) robot ----------------

class RobotSource(Source):
    """robotlink.RobotLink iza Source oblika. Komande kao /ws/robot: push, run, stop."""
    kind = "robot"
    capabilities = frozenset({"push", "run", "stop", "lidar"})

    def __init__(self, host, pw, prof, upload_port=None, telem_port=None):
        from . import robotlink
        self.link = robotlink.RobotLink(host, pw, self._emit, prof,
                                        upload_port=upload_port or robotlink.UPLOAD_PORT,
                                        telem_port=telem_port or robotlink.TELEM_PORT)
        self.buf = Buffer()
        self.pump = None
        self.t_start = None

    async def _emit(self, d):
        self.buf.add(d)

    async def start(self):
        await self.link.start()                       # OSError ako se ime ne može naći
        self.t_start = time.monotonic()
        self.pump = asyncio.create_task(self.link.run())

    async def poll(self):
        r = self.link.rec
        if r.last_rx is not None:
            age = self.link.now() - r.last_rx
        else:
            age = int((time.monotonic() - self.t_start) * 1000)
        return self.buf.take(age)

    async def command(self, c):
        k = c[0] if c else ""
        if k not in self.capabilities or k == "lidar":
            return self.unsupported(c)
        if k == "push":                               # ["push", ime, tekst ili None = fajl iz ESP32/tactics]
            name, src = (c[1] if len(c) > 1 else None), (c[2] if len(c) > 2 else None)
            if not tacmod.NAME_RE.match(name or ""):
                return self.reply(c, False, ["neispravno ime"])
            if src is None:
                try:
                    src = (paths.TACTICS / (name + ".py")).read_text(encoding="utf-8")
                except OSError as e:
                    return self.reply(c, False, [str(e)])
            data = src.encode("utf-8")
            ok, lines = await self.link.cmd("PUT", "/tactics/%s.py" % name, len(data), data=data)
        elif k == "run":
            if len(c) < 2:
                return self.reply(c, False, ["nema imena taktike"])
            ok, lines = await self.link.cmd("RUN", c[1], c[2] if len(c) > 2 else "")
        else:
            ok, lines = await self.link.cmd("STOP")
        return self.reply(c, ok, lines)

    async def close(self):
        if self.pump:
            self.pump.cancel()
            try:
                await self.pump
            except asyncio.CancelledError:
                pass
        self.link.close()
        return self.link.recording()


# ---------------- snimak ----------------

class ReplaySource(Source):
    kind = "replay"
    capabilities = frozenset({"seek"})

    def __init__(self, path):
        self.path = path
        self.rec = None
        self.sent = False

    async def start(self):
        self.rec = await asyncio.get_running_loop().run_in_executor(None, Recording.load, self.path)

    async def poll(self):
        if self.rec is None or self.sent:
            return {"frames": [], "events": [], "meta": None, "t": 0, "age": None, "final": True}
        self.sent = True
        r = self.rec
        return {"frames": r.frames, "events": r.events, "meta": r.meta,
                "t": r.frames[-1]["t"] if r.frames else 0, "age": None, "final": True}

    async def command(self, c):
        if c and c[0] == "stop":
            return self.reply(c)
        return self.unsupported(c)

    async def close(self):
        return self.rec.to_dict() if self.rec else {}
