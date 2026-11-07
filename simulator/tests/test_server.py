# Server (API) u posebnoj niti na slobodnom portu; simulacije idu u posebne procese kao u radu.
import asyncio
import json
import socket
import threading
import urllib.request

import pytest

aiohttp = pytest.importorskip("aiohttp")
from aiohttp import web  # noqa: E402

from eurosim import server  # noqa: E402


@pytest.fixture(scope="module")
def base(tmp_path_factory):
    server.RUNS = tmp_path_factory.mktemp("runs")
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    loop = asyncio.new_event_loop()
    runner = web.AppRunner(server.make_app())

    def go():
        asyncio.set_event_loop(loop)
        loop.run_until_complete(runner.setup())
        loop.run_until_complete(web.TCPSite(runner, "127.0.0.1", port).start())
        loop.run_forever()

    threading.Thread(target=go, daemon=True).start()
    url = "http://127.0.0.1:%d" % port
    for _ in range(100):
        try:
            urllib.request.urlopen(url + "/api/info", timeout=1)
            break
        except OSError:
            import time
            time.sleep(0.05)
    yield url
    loop.call_soon_threadsafe(loop.stop)


def get(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.load(r)


def post(url, body):
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, json.load(e)


def test_info(base):
    d = get(base + "/api/info")
    assert "primer" in d["tactics"] and d["field"]["w"] == 3000
    assert d["profile"]["drive"]["wheel_track"] == 166


def test_index_i_staticki_fajlovi(base):
    with urllib.request.urlopen(base + "/", timeout=5) as r:
        assert b"Eurosim" in r.read()
    with urllib.request.urlopen(base + "/app.js", timeout=5) as r:
        assert r.status == 200


def test_run_vraca_kolone_i_rezultat(base):
    st, d = post(base + "/api/run", {"tactic": "primer", "side": "zuta", "mode": "mec",
                                     "obstacles": [{"x": 2200, "y": 1000}]})
    assert st == 200
    assert set(("t", "x", "y", "th", "ox", "v_ref")) <= set(d["cols"])
    assert len(d["cols"]["t"]) == len(d["cols"]["x"]) > 10
    assert d["result"]["fail"][2] == "BLOCKED"           # protivnik na putu (žuta: GOTO na 2400)


def test_nepoznata_taktika_400(base):
    st, d = post(base + "/api/run", {"tactic": "../nema"})
    assert st == 400 and "error" in d


def test_cuvanje_i_ucitavanje(base):
    post(base + "/api/run", {"tactic": "provera", "mode": "test"})
    st, d = post(base + "/api/runs/save", {"name": "moj test/../x"})
    assert st == 200 and d["saved"] == "moj_test_.._x"
    assert d["saved"] in get(base + "/api/runs")
    r = get(base + "/api/runs/" + d["saved"])
    assert r["meta"]["tactic"] == "provera" and "cols" in r


def test_beskonacna_petlja_bez_cekanja_se_prekida(tmp_path, monkeypatch):
    from eurosim import paths
    (tmp_path / "zauvek.py").write_text("from tac import *\nwhile True:\n    pass\n")
    kind, msg = server.run_in_process(dict(name="zauvek", mode="test", tactics_dir=str(tmp_path)), timeout=3)
    assert kind == "err" and "nije završila" in msg


def test_live_websocket(base):
    import asyncio
    import aiohttp as ah

    async def go():
        async with ah.ClientSession() as cs:
            async with cs.ws_connect(base.replace("http", "ws") + "/ws/live?tactic=primer&side=zuta") as ws:
                got = []
                await ws.send_json(["speed", 50])
                await ws.send_json(["test", "primer", "zuta"])
                t0 = asyncio.get_running_loop().time()
                while True:
                    m = await ws.receive_json(timeout=20)
                    got.append(m["type"])
                    if m["type"] == "data" and m["t"] > 6000 and "quit" not in got:
                        got.append("quit")
                        await ws.send_json(["quit"])
                    if m["type"] in ("end", "error") or asyncio.get_running_loop().time() - t0 > 30:
                        return m, got

    m, got = asyncio.run(go())
    assert m["type"] == "end", m
    assert m["run"]["meta"]["tactic"] == "primer" and len(m["run"]["cols"]["t"]) > 100
    assert any(e[1] == "screen" for e in m["run"]["events"])
