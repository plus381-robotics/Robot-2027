# Test dela → Lidar: međukoraci jednog kruga na laptopu (eurosim/lidarview.py) i njihovi endpoint-i.
import gzip
import json
import math

import pytest

from eurosim import lidarview, paths, profile as P

PROF = P.load(paths.DEFAULT_PROFILE)


def scan_of(pts, o=(0, 0, 300), near=None):
    flat = []
    for a, d in pts:
        flat += [a, d]
    return {"pts": flat, "o": list(o), "near": near, "hz": 10.0}


def raycast(boxes, walls=None):
    """Krug kao sa lidara u centru robota: za svaki stepen (0 = napred, + = levo) najbliži presek sa kutijama
    (x0, y0, x1, y1 u koordinatama robota) i, ako su date, ivicama stola (isto, pravougaonik oko robota)."""
    out = []
    for a in range(360):
        dx, dy = math.cos(math.radians(a)), math.sin(math.radians(a))
        best = math.inf
        for x0, y0, x1, y1 in boxes:              # slab metoda
            tmin, tmax = 0.0, math.inf
            for o0, o1, dd in ((x0, x1, dx), (y0, y1, dy)):
                if abs(dd) < 1e-12:
                    if not (o0 <= 0 <= o1):
                        tmin, tmax = 1, 0
                    continue
                t1, t2 = sorted((o0 / dd, o1 / dd))
                tmin, tmax = max(tmin, t1), min(tmax, t2)
            if tmin <= tmax and tmin > 0:
                best = min(best, tmin)
        if walls:
            x0, y0, x1, y1 = walls
            for t in ((x1 / dx) if dx > 1e-12 else math.inf, (x0 / dx) if dx < -1e-12 else math.inf,
                      (y1 / dy) if dy > 1e-12 else math.inf, (y0 / dy) if dy < -1e-12 else math.inf):
                if 0 < t < best:
                    best = t
        if best < math.inf:
            out.append((a, round(best)))
    return out


def test_tacke_van_stola_odbacene():
    s = lidarview.stages(scan_of([(0, 400), (180, 300)]), (2800, 1400, 0), PROF)
    assert [3200, 1400] in s["out"]
    assert [2500, 1400] in s["in"] and [3200, 1400] not in s["in"]
    assert s["frame"] == "sto" and s["by"] == "laptop"


def test_bez_poze_nema_stola():
    s = lidarview.stages(scan_of([(0, 500), (90, 300)]), None, PROF)
    assert s["in"] == [] and s["out"] == []
    assert s["raw"] == [[500, 0, -1], [0, 300, -1]]               # koordinate robota: x napred, y levo
    assert s["frame"] == "robot"


def test_grupa_protivnika():
    """Kocka 300×300 ispred robota, prednja strana na 420 mm; robot na sredini stola, lidar vidi i ivice stola."""
    pts = raycast([(420, -150, 720, 150)], walls=(-1500, -1000, 1500, 1000))
    s = lidarview.stages(scan_of(pts), (1500, 1000, 0), PROF)
    assert len(s["groups"]) == 1                                   # ivica stola nije grupa
    g = s["groups"][0]
    assert g["dist"] == pytest.approx(420, abs=30)
    assert g["angle"] == pytest.approx(0, abs=3) and g["n"] >= 3
    assert g["x"] == pytest.approx(1920, abs=30) and g["y"] == pytest.approx(1000, abs=30)
    assert s["nearest"] == g and not s["out"]


def test_grupa_levo_ugao_i_rotirana_poza():
    """Kocka levo-napred (30°) i robot okrenut ka +y: ugao ostaje u koordinatama robota, x/y na stolu."""
    c = (500 * math.cos(math.radians(30)), 500 * math.sin(math.radians(30)))
    pts = raycast([(c[0] - 60, c[1] - 60, c[0] + 60, c[1] + 60)])
    s = lidarview.stages(scan_of(pts), (1000, 800, 90), PROF)
    g = s["nearest"]
    assert g["angle"] == pytest.approx(30, abs=6)
    assert g["dist"] == pytest.approx(500 - 60, abs=40)
    # težište vidljivih strana (bliže robotu od centra kocke): sto x = 1000 - y robota, y = 800 + x robota
    assert g["x"] == pytest.approx(1000 - c[1], abs=60) and g["y"] == pytest.approx(800 + c[0], abs=60)


def test_bez_poze_grupe_oko_robota_i_esp_najbliza():
    pts = raycast([(420, -150, 720, 150)])
    s = lidarview.stages(scan_of(pts, near=[420, 0]), None, PROF)
    assert len(s["groups"]) == 1 and s["groups"][0]["dist"] == pytest.approx(420, abs=30)
    assert s["esp_near"] == {"dist": 420, "angle": 0}              # „robot“ (ESP _closest), ne laptop


def test_grupa_preko_nule_jedna_i_sum_nije_grupa():
    pts = raycast([(400, -100, 600, 100)]) + [(180, 700)]           # kocka na 0° (i 359°) + jedna tačka iza
    s = lidarview.stages(scan_of(sorted(pts)), None, PROF)
    assert len(s["groups"]) == 1 and s["groups"][0]["angle"] == pytest.approx(0, abs=3)


def test_pomeraj_lidara_iz_kruga_pa_iz_profila():
    s = lidarview.stages(scan_of([(0, 100)], o=(50, 20, 300)), None, PROF)
    assert s["raw"] == [[150, 20, -1]]
    s = lidarview.stages({"pts": [0, 100]}, None, {"lidar": {"x": -30, "y": 0}})
    assert s["raw"] == [[70, 0, -1]]


# ---------------- endpoint-i ----------------

aiohttp = pytest.importorskip("aiohttp")


def _write(path, scans, meta=None):
    with gzip.open(path, "wt", encoding="utf-8") as f:
        f.write(json.dumps({"meta": meta or {"source": "test"}}) + "\n")
        for s in scans:
            f.write(json.dumps(s) + "\n")


def _bins(**at):
    b = [0] * 360
    for k, v in at.items():
        b[int(k[1:])] = v
    return b


def _client(go):
    import asyncio
    from aiohttp.test_utils import TestClient, TestServer
    from eurosim import server

    async def main():
        async with TestClient(TestServer(server.make_app(PROF))) as c:
            return await go(c)
    return asyncio.run(main())


def test_endpoint_stages(tmp_path):
    async def go(c):
        ok = await c.post("/api/lidar/stages", json={"scan": scan_of([(0, 400)]), "pose": [2800, 1400, 0]})
        nopose = await c.post("/api/lidar/stages", json={"scan": scan_of([(0, 400)]), "pose": None})
        bad = await c.post("/api/lidar/stages", json={"scan": {"pts": "x"}, "pose": None})
        bad2 = await c.post("/api/lidar/stages", json={"scan": scan_of([(0, 400)]), "pose": [1, 2]})
        return ok.status, await ok.json(), (await nopose.json())["frame"], bad.status, bad2.status
    st, d, frame, bad, bad2 = _client(go)
    assert st == 200 and d["out"] == [[3200, 1400]] and d["by"] == "laptop"
    assert frame == "robot" and bad == 400 and bad2 == 400


def test_endpoint_snimci_lidara(tmp_path, monkeypatch):
    from eurosim import lidarsrc
    monkeypatch.setattr(lidarsrc, "lidar_dir", lambda: tmp_path)
    _write(tmp_path / "a.jsonl.gz", [{"t": 5000 + 100 * i, "bins": _bins(a0=500 + i, a90=300), "hz": 9.5,
                                      "near": [300, 90]} for i in range(10)])
    _write(tmp_path / "p.jsonl.gz", [{"t": 0, "bins": _bins(a0=400), "hz": 10, "near": None, "pose": [2800, 1400, 0]}])
    (tmp_path / "x.jsonl.gz").write_bytes(b"nije gzip")
    (tmp_path.parent / "van.jsonl.gz").write_bytes(b"")
    monkeypatch.setattr("eurosim.api.lidar.MAX_SCANS", 4)

    async def go(c):
        lst = await (await c.get("/api/lidar/files")).json()
        a = await (await c.get("/api/lidar/files/a.jsonl.gz")).json()
        a3 = await (await c.get("/api/lidar/files/a?every=3")).json()
        p = await (await c.get("/api/lidar/files/p.jsonl.gz")).json()
        codes = {}
        for n in ("x.jsonl.gz", "nema.jsonl.gz", "..%2Fvan.jsonl.gz", "%2Ftmp%2Fvan.jsonl.gz", "..", ".a.jsonl.gz"):
            codes[n] = (await c.get("/api/lidar/files/" + n)).status
        return lst, a, a3, p, codes
    lst, a, a3, p, codes = _client(go)
    assert [f["name"] for f in lst["files"]] == ["a.jsonl.gz", "p.jsonl.gz", "x.jsonl.gz"]
    assert a["total"] == 10 and len(a["scans"]) == 4 and a["truncated"] is True    # najviše MAX_SCANS krugova
    s0 = a["scans"][0]
    assert s0["t"] == 0 and a["scans"][1]["t"] == 100 and s0["pts"][:2] == [0, 500] and [90, 300] == s0["pts"][2:4]
    assert s0["pose"] is None and s0["near"] == [300, 90] and s0["hz"] == 9.5 and len(s0["o"]) == 3
    assert [s["t"] for s in a3["scans"]] == [0, 300, 600, 900] and a3["every"] == 3
    assert p["scans"][0]["pose"] == [2800, 1400, 0]
    assert codes["x.jsonl.gz"] == 422 and codes["nema.jsonl.gz"] == 404
    assert codes["..%2Fvan.jsonl.gz"] in (400, 404) and codes["%2Ftmp%2Fvan.jsonl.gz"] in (400, 404)
    assert codes[".."] in (400, 404) and codes[".a.jsonl.gz"] == 400


def test_robot_upali_lidar_i_snimi_krugove(tmp_path, monkeypatch):
    """RobotSource preko virtuelnog robota (pravi ESP kod: upload.py LIDAR ON, telem.py krugovi): ["lidar", "on"],
    ["lidar", "rec", True/False] -> snimak u lidar_dir() koji FileLidar pušta, sa pozom iz telemetrije."""
    import asyncio
    import socket
    import threading
    import time
    from eurosim import lidarsrc
    from eurosim.session import RobotSource, SimSource
    from eurosim.sim import Sim
    from test_robot import free_port
    monkeypatch.setattr(lidarsrc, "lidar_dir", lambda: tmp_path)
    up, tp = free_port(), free_port(socket.SOCK_DGRAM)
    sim = Sim("primer", mode="live", net={"upload": up, "telem": tp, "password": "pw"},
              obstacles=[{"x": 750, "y": 1000, "w": 300, "h": 300, "z": 350}])
    th = threading.Thread(target=sim.run, daemon=True)
    th.start()
    time.sleep(1.0)

    async def go():
        s = RobotSource("127.0.0.1", "pw", PROF, upload_port=up, telem_port=tp)
        await s.start()
        try:
            await s.command(["lidar", "rec", True])
            empty_stop = await s.command(["lidar", "rec", False])
            on = await s.command(["lidar", "on"])
            rec = await s.command(["lidar", "rec", True])
            ev = []
            t0 = time.time()
            while time.time() - t0 < 5 and len(ev) < 6:
                await asyncio.sleep(0.2)
                ev += [e for e in (await s.poll())["events"] if e[1] == "lidar"]
            stop = await s.command(["lidar", "rec", False])
            off = await s.command(["lidar", "off"])
            bad = await s.command(["lidar", "x"])
            return empty_stop, on, rec, ev, stop, off, bad
        finally:
            await s.close()
            sim.command(("quit",))
            th.join(5)
    empty_stop, on, rec, ev, stop, off, bad = asyncio.run(go())
    assert empty_stop["lidar"]["saved"] is None and "ništa" in empty_stop["lines"][-1]
    assert on["ok"] and on["cmd"] == "lidar" and on["lidar"]["on"] is True and on["lidar"]["state"] not in (None, "off")
    assert rec["ok"] and rec["lidar"]["rec"].endswith(".jsonl.gz")
    assert len(ev) >= 6
    assert stop["lidar"]["rec"] is None and stop["lidar"]["n"] >= 1 and stop["lidar"]["saved"] == rec["lidar"]["rec"]
    assert off["ok"] and off["lidar"]["on"] is False
    assert bad["ok"] is False
    assert [p.name for p in tmp_path.iterdir()] == [stop["lidar"]["saved"]]      # prazan snimak ne ostaje
    f = lidarsrc.FileLidar(tmp_path / stop["lidar"]["saved"])
    assert len(f.scans) == stop["lidar"]["n"] and f.scans[-1]["bins"][0] == pytest.approx(350, abs=5)
    assert f.scans[-1]["pose"] is not None and len(f.scans[-1]["pose"]) == 3
    assert (asyncio.run(SimSource({"name": "primer"}).command(["lidar", "on"])))["lines"] == ["nepodržano"]
