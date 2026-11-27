# Izvori sesije (eurosim/session.py): simulacija, robot i snimak iza istog Source oblika.
import asyncio
import socket
import threading
import time

from eurosim import paths, profile as P, record
from eurosim.session import CAPS, ReplaySource, RobotSource, SimSource
from eurosim.sim import Sim

from test_robot import free_port


def test_nepodrzana_komanda():
    async def go():
        s = ReplaySource("nema.json.gz")
        return await s.command(["arm"])
    r = asyncio.run(go())
    assert r["ok"] is False and r["lines"] == ["nepodržano"] and r["cmd"] == "arm"


def test_sposobnosti_su_podskup_CAPS():
    assert ReplaySource("x").capabilities == frozenset({"seek"})
    assert RobotSource("h", "pw", P.load(paths.DEFAULT_PROFILE)).capabilities == {"push", "run", "stop", "lidar"}
    assert SimSource({"name": "primer"}).capabilities <= CAPS
    real = SimSource({"name": "primer", "lidar_spec": "robot:h"})
    assert "pause" not in real.capabilities and "speed" not in real.capabilities
    assert "pause" in SimSource({"name": "primer"}).capabilities


def test_sim_source_sposobnosti_i_podaci():
    async def go():
        s = SimSource({"name": "primer", "side": "zuta"})
        await s.start()
        try:
            await asyncio.sleep(1.0)
            d = await s.poll()
            bad = await s.command(["push", "x", None])
            ok = await s.command(["pause", True])
            return s, d, bad, ok
        finally:
            rec = await s.close()
    s, d, bad, ok = asyncio.run(go())
    assert "pause" in s.capabilities and d["frames"] and d["age"] is None and d["final"] is False
    assert bad["ok"] is False and bad["lines"] == ["nepodržano"]
    assert ok["ok"] is True


def test_sim_source_close_vraca_snimak_v2():
    async def go():
        s = SimSource({"name": "primer"})
        await s.start()
        await asyncio.sleep(0.5)
        return await s.close()
    rec = asyncio.run(go())
    assert rec["version"] == 2 and rec["meta"]["origin"]["engine"] == "sim" and rec["frames"]


def test_replay_source_vraca_ceo_snimak_jednom(tmp_path):
    r = record.Recording({"origin": {"engine": "sim", "parts": {}}})
    r.frames = [{"t": 0, "x": 1}, {"t": 20, "x": 2}]
    r.events = [[0, "log", "a"]]
    f = tmp_path / "r.json.gz"
    r.save(f)

    async def go():
        s = ReplaySource(f)
        await s.start()
        return await s.poll(), await s.poll(), await s.close()
    a, b, c = asyncio.run(go())
    assert a["final"] is True and len(a["frames"]) == 2 and a["events"] and a["meta"]["origin"]["engine"] == "sim"
    assert a["age"] is None and b["frames"] == [] and b["meta"] is None
    assert c["version"] == 2 and len(c["frames"]) == 2


def test_robot_source_preko_virtuelnog_robota():
    up, tp = free_port(), free_port(socket.SOCK_DGRAM)
    sim = Sim("primer", mode="live", net={"upload": up, "telem": tp, "password": "pw"})
    sim.speed = 3.0
    th = threading.Thread(target=sim.run, daemon=True)
    th.start()
    time.sleep(1.0)

    async def go():
        s = RobotSource("127.0.0.1", "pw", P.load(paths.DEFAULT_PROFILE), upload_port=up, telem_port=tp)
        await s.start()
        try:
            early = await s.poll()
            bad = await s.command(["push", "../x", None])
            push = await s.command(["push", "primer", None])
            run = await s.command(["run", "primer", "zuta"])
            frames = []
            t0 = time.time()
            while time.time() - t0 < 5 and len(frames) < 3:
                await asyncio.sleep(0.2)
                d = await s.poll()
                frames += d["frames"]
            last = await s.poll()
            stop = await s.command(["stop"])
            nope = await s.command(["arm"])
            return early, bad, push, run, frames, last, stop, nope
        finally:
            rec = await s.close()
            sim.command(("quit",))
            th.join(5)
    early, bad, push, run, frames, last, stop, nope = asyncio.run(go())
    assert early["age"] is not None and early["frames"] == []
    assert bad["ok"] is False and push["ok"] is True and run["ok"] is True and stop["ok"] is True
    assert nope["ok"] is False and nope["lines"] == ["nepodržano"]
    assert frames and last["age"] is not None and last["age"] < 3000
    assert not th.is_alive()


def test_buffer_prazan_poll_cuva_stanje():
    from eurosim.session import Buffer
    b = Buffer()
    b.add({"frames": [{"t": 690}], "events": [[1, "log", "a"]], "meta": {"side": "zuta"}, "t": 690,
           "paused": False, "speed": 1.0, "running": "primer", "mec": "NEMA"})
    first = b.take(None)
    again = b.take(None)
    assert first["t"] == 690 and first["paused"] is False and first["meta"] == {"side": "zuta"}
    for k in ("t", "paused", "speed", "running", "mec"):
        assert again[k] == first[k]
    assert again["frames"] == [] and again["events"] == [] and again["meta"] is None


def test_buffer_novija_meta_pobedjuje():
    from eurosim.session import Buffer
    b = Buffer()
    b.add({"frames": [], "events": [], "meta": {"side": "zuta"}, "t": 1})
    b.add({"frames": [], "events": [], "meta": {"side": "plava"}, "t": 2})
    b.add({"frames": [], "events": [], "meta": None, "t": 3})
    assert b.take(None)["meta"] == {"side": "plava"}


def test_sim_source_pad_procesa_postavlja_error():
    class Dead:
        def poll(self, t=0):
            return True

        def recv(self):
            raise EOFError

    async def go():
        s = SimSource({"name": "primer"})
        s.conn = Dead()
        s.proc = type("P", (), {"is_alive": lambda self: False})()
        return await s.poll()
    d = asyncio.run(go())
    assert d["final"] is True and d["error"] == "proces simulacije je stao"
