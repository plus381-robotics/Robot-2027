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
            s_early_age = s.link_age()
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
            return early, bad, push, run, frames, last, stop, nope, s_early_age
        finally:
            rec = await s.close()
            sim.command(("quit",))
            th.join(5)
    early, bad, push, run, frames, last, stop, nope, s_early_age = asyncio.run(go())
    assert early["frames"] == [] and s_early_age is not None
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


# ---------------- /ws/session (server.session_ws) ----------------

def _ws_run(path_fn, scenario):
    """Podigne aplikaciju u istoj petlji, otvori WebSocket na path_fn(base) i pozove scenario(ws)."""
    import pytest
    aiohttp = pytest.importorskip("aiohttp")
    from aiohttp.test_utils import TestServer
    from eurosim import server

    async def go():
        srv = TestServer(server.make_app())
        await srv.start_server()
        try:
            async with aiohttp.ClientSession() as cs:
                async with cs.ws_connect(path_fn("ws://127.0.0.1:%d" % srv.port)) as ws:
                    return await scenario(ws)
        finally:
            await srv.close()
    return asyncio.run(go())


def test_ws_session_hello_pa_podaci():
    async def scenario(ws):
        got = []
        t0 = time.time()
        while time.time() - t0 < 20:
            m = await ws.receive_json(timeout=10)
            got.append(m)
            if m["type"] == "data" and m["frames"]:
                break
        await ws.send_json(["quit"])
        while got[-1]["type"] not in ("end", "error"):
            got.append(await ws.receive_json(timeout=15))
        return got
    got = _ws_run(lambda b: b + "/ws/session?engine=sim&tactic=primer&side=zuta", scenario)
    h = got[0]
    assert h["type"] == "hello" and h["source"]["engine"] == "sim" and "parts" in h["source"]
    assert "pause" in h["capabilities"] and "stop" in h["capabilities"]
    data = [m for m in got if m["type"] == "data"]
    assert data and all(k in data[0] for k in ("frames", "events", "t", "meta", "final"))
    assert got[-1]["type"] == "end" and got[-1]["run"]["cols"]["t"]


def _robot_tihi(monkeypatch, calls):
    """RobotLink čija telemetrija ćuti (UDP nikad ne stiže), a cmd samo beleži poziv."""
    from eurosim import robotlink, server
    monkeypatch.setattr(server, "STALE_MS", 300)
    monkeypatch.setattr(server, "LOST_MS", 900)

    async def cmd(self, *args, data=b""):
        calls.append(args)
        return True, ["OK"]
    monkeypatch.setattr(robotlink.RobotLink, "cmd", cmd)
    return free_port(socket.SOCK_DGRAM)


def test_link_stale_pa_lost(monkeypatch):
    calls, datas_all = [], []
    tp = _robot_tihi(monkeypatch, calls)

    async def scenario(ws):
        states, datas, first = [], 0, None
        datas_all.clear()
        t0 = time.time()
        while time.time() - t0 < 10 and [s["link"] for s in states][-1:] != ["lost"]:
            m = await ws.receive_json(timeout=5)
            first = first or m
            if m["type"] == "state":
                states.append(m)
            elif m["type"] == "data":
                datas += 1
                datas_all.append(m)
        await asyncio.sleep(0.5)                       # sesija je još živa: nema end/error
        await ws.send_json(["quit"])
        last = None
        while last is None or last["type"] not in ("end", "error"):
            last = await ws.receive_json(timeout=5)
        return first, states, datas, last
    first, states, datas, last = _ws_run(
        lambda b: b + "/ws/session?engine=robot&host=127.0.0.1&password=pw&telem=%d" % tp, scenario)
    assert first["type"] == "hello" and first["source"]["engine"] == "robot"
    assert [s["link"] for s in states] == ["stale", "lost"] and states[0]["age"] > 300 and states[1]["age"] > 900
    assert datas > 3 and last["type"] == "end"
    assert all(m["age"] is None for m in datas_all)          # kao nekad: age je null dok ne stigne paket
    assert calls[0] == ("STAT",)


def test_stop_radi_i_kad_je_veza_izgubljena(monkeypatch):
    calls = []
    tp = _robot_tihi(monkeypatch, calls)

    async def scenario(ws):
        while True:
            m = await ws.receive_json(timeout=5)
            if m["type"] == "state" and m["link"] == "lost":
                break
        await ws.send_json(["stop"])
        while True:
            m = await ws.receive_json(timeout=5)
            if m["type"] == "reply" and m["cmd"] == "stop":
                break
        await ws.send_json(["quit"])
        return m
    m = _ws_run(lambda b: b + "/ws/robot?host=127.0.0.1&password=pw&telem=%d" % tp, scenario)
    assert m["ok"] is True and ("STOP",) in calls


def test_ws_robot_nepoznat_host_daje_error():
    async def scenario(ws):
        return await ws.receive_json(timeout=10)
    m = _ws_run(lambda b: b + "/ws/robot?host=nema-takvog-hosta.invalid", scenario)
    assert m["type"] == "error" and "ne mogu da nađem nema-takvog-hosta.invalid" in m["error"]


def test_ws_replay_snimak(tmp_path):
    from eurosim import server
    r = record.Recording({"origin": {"engine": "sim", "parts": {"pogon": "sim"}}})
    r.frames = [{"t": 0, "x": 1}, {"t": 20, "x": 2}]
    server.RUNS = tmp_path
    try:
        r.save(tmp_path / "snimak1.json.gz")

        async def scenario(ws):
            return [await ws.receive_json(timeout=10) for _ in range(3)]
        got = _ws_run(lambda b: b + "/ws/session?engine=replay&run=snimak1", scenario)
    finally:
        server.RUNS = None
    assert [m["type"] for m in got] == ["hello", "data", "end"]
    assert got[0]["source"]["engine"] == "replay" and got[0]["source"]["parts"] == {"pogon": "sim"}
    assert len(got[1]["frames"]) == 2 and got[2]["run"]["cols"]["t"] == [0, 20]


def test_komanda_posle_kraja_ima_razlog():
    async def go():
        s = SimSource({"name": "primer"})
        s.done = True
        r1 = await s.command(["pause", True])
        rb = RobotSource("h", "pw", P.load(paths.DEFAULT_PROFILE))
        await rb.close()
        r2 = await rb.command(["stop"])
        return r1, r2
    r1, r2 = asyncio.run(go())
    assert r1["ok"] is False and r1["lines"] == ["sesija je završena"]
    assert r2["ok"] is False and r2["lines"] == ["sesija je završena"]


def test_hibrid_lidar_iz_snimka_kroz_sesiju(tmp_path):
    """Izvori b (hibrid): engine=sim, lidar=file:<snimak> -> hello.source.parts.lidar == "snimak", a kad ESP upali
    lidar (Meni -> Lidar test, tasterima preko sesije) stižu događaji "lidar" sa krugovima iz snimka.
    Simulacija radi u posebnom procesu (spawn), pa monkeypatch lidar_dir() tamo ne važi: snimak se daje punom putanjom
    (FileLidar prima i nju), pa ništa ne ostaje u simulator/lidar/."""
    from urllib.parse import quote
    from test_lidar_sources import bins_with, write_rec
    from test_live import live
    rec = tmp_path / "hib.jsonl.gz"
    write_rec(rec, [(i * 100, bins_with(a0=777, a90=444, a200=1234)) for i in range(30)])
    s, _, _ = live([(300, ("btn", "back", 1)), (1100, ("btn", "back", 0))])   # gde je „Lidar test“ u meniju (pravi ESP kod)
    idx = [it.label for it in s.app.ui.top.items].index("Lidar test")

    async def scenario(ws):
        hello = await ws.receive_json(timeout=15)
        t, lidar, t0 = 0, [], time.time()

        async def until(ms):                                   # čekaj vreme simulacije ms (poruke data nose t)
            nonlocal t
            while t < ms and time.time() - t0 < 40:
                m = await ws.receive_json(timeout=15)
                if m["type"] == "data":
                    t = m["t"] or t
                    lidar.extend(e for e in m["events"] if e[1] == "lidar")
        await ws.send_json(["speed", 5])
        await until(300)
        plan = [(800, ["btn", "back", 1]), (200, ["btn", "back", 0]), (200, ["rot", idx]), (100, ["btn", "enc", 1]),
                (100, ["btn", "enc", 0])]
        for wait, c in plan:                                   # dugi NAZAD -> meni, okret do „Lidar test“, klik
            await ws.send_json(c)
            await until(t + wait)
        while not lidar and time.time() - t0 < 40:
            await until(t + 200)
        await ws.send_json(["quit"])
        last = None
        while last is None or last["type"] not in ("end", "error"):
            last = await ws.receive_json(timeout=15)
        return hello, lidar, last
    hello, lidar, last = _ws_run(lambda b: b + "/ws/session?engine=sim&tactic=primer&side=zuta&lidar=" +
                                 quote("file:" + str(rec), safe=""), scenario)
    assert hello["type"] == "hello" and hello["source"]["engine"] == "sim"
    assert hello["source"]["parts"]["lidar"] == "snimak" and hello["source"]["parts"]["pogon"] == "sim"
    assert lidar, "nijedan događaj lidar"
    ev = lidar[-1][2]
    assert dict(zip(ev["pts"][::2], ev["pts"][1::2])) == {0: 777, 90: 444, 200: 1234}     # krugovi iz snimka
    assert last["type"] == "end" and last["run"]["meta"]["lidar_source"] == "snimak hib.jsonl.gz"
