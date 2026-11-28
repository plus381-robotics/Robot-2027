# Hibridna simulacija, izvori lidara (eurosim/lidarsrc.py): pravi lidar sa robota preko WiFi-ja (ovde virtuelni
# robot sa pravim telem.py/upload.py), snimak i ponavljanje snimka, krugovi kroz drajver simuliranog ESP-a,
# brzina ×1 sa pravim uređajem, Robot panel crta krugove robota.
import gzip
import json
import socket
import threading
import time

import pytest

from eurosim import lidarsrc, robotlink
from eurosim.sim import Sim
from test_live import live, Remote
from test_robot import free_port


def write_rec(path, scans):
    with gzip.open(path, "wt", encoding="utf-8") as f:
        f.write(json.dumps({"meta": {"source": "test"}}) + "\n")
        for t, bins in scans:
            f.write(json.dumps({"t": t, "bins": bins, "hz": 10.0, "near": None}) + "\n")


def bins_with(**at):
    b = [0] * 360
    for k, v in at.items():
        b[int(k[1:])] = v
    return b


def test_snimak_po_vremenu_i_u_krug(tmp_path):
    p = tmp_path / "r.jsonl.gz"
    write_rec(p, [(1000, bins_with(a0=500)), (1100, bins_with(a0=510)), (1200, bins_with(a0=520))])
    f = lidarsrc.FileLidar(p)
    assert [s["bins"][0] for s in f.poll(5000)] == [500]          # vreme od prvog poll-a
    assert f.poll(5050) == []
    assert [s["bins"][0] for s in f.poll(5200)] == [510, 520]
    assert [s["bins"][0] for s in f.poll(5300)] == [500]          # posle kraja (period 300 ms) ispočetka
    assert f.describe() == "snimak r.jsonl.gz"


def test_izvor_iz_specifikacije(tmp_path, monkeypatch):
    monkeypatch.setattr(lidarsrc, "lidar_dir", lambda: tmp_path)
    write_rec(tmp_path / "a.jsonl.gz", [(0, bins_with(a0=1))])
    assert lidarsrc.open_source("sim") is None and lidarsrc.open_source(None) is None
    assert isinstance(lidarsrc.open_source("file:a.jsonl.gz"), lidarsrc.FileLidar)
    assert lidarsrc.recordings() == ["a.jsonl.gz"]
    with pytest.raises(ValueError):
        lidarsrc.open_source("kamera:1")


def open_lidar_test(**kw):
    """Live: dugi NAZAD -> meni, okret do "Lidar test", klik; posle 2 s kraj. Vraća (sim, snimak)."""
    s, _, _ = live([(300, ("btn", "back", 1)), (1100, ("btn", "back", 0))], **kw)
    idx = [it.label for it in s.app.ui.top.items].index("Lidar test")
    return live([(300, ("btn", "back", 1)), (1100, ("btn", "back", 0)), (1300, ("rot", idx)),
                 (1500, ("btn", "enc", 1)), (1600, ("btn", "enc", 0)), (3500, ("pause", False))], **kw)[:2]


def test_snimak_kroz_drajver_simuliranog_esp(tmp_path):
    """Krugovi iz snimka idu lažnim RPLIDAR-om do pravog drajvera (lib/lidar.py) simuliranog ESP-a: isti binovi."""
    p = tmp_path / "r.jsonl.gz"
    write_rec(p, [(i * 100, bins_with(a0=777, a90=444, a200=1234)) for i in range(30)])
    s, r = open_lidar_test(lidar=lidarsrc.FileLidar(p))
    L = s.app.ui.top.lidar
    assert L.scanning and L.dist[0] == 777 and L.dist[90] == 444 and L.dist[200] == 1234
    assert sum(1 for d in L.dist if d) == 3                          # ništa od simuliranog stola
    ev = r.of("lidar")[-1][2]
    assert dict(zip(ev["pts"][::2], ev["pts"][1::2])) == {0: 777, 90: 444, 200: 1234}
    assert r.meta["lidar_source"] == "snimak r.jsonl.gz" and r.meta["realtime"] is False


class FakeRobotSrc:
    kind = "robot"
    error = None
    received = 0

    def __init__(self):
        self.closed = False

    def describe(self):
        return "robot test"

    def poll(self, t):
        return []

    def close(self):
        self.closed = True


def test_pravi_uredjaj_brzina_x1_bez_pauze():
    src = FakeRobotSrc()
    s = Sim("primer", mode="live", lidar=src)
    s.control = Remote(s, [(100, ("speed", 5)), (200, ("pause", True)), (400, ("quit",))])
    r = s.run()
    assert s.speed == 1.0 and not s.paused and s.realtime
    assert r.meta["realtime"] is True and src.closed
    with pytest.raises(ValueError):
        Sim("primer", mode="mec", lidar=FakeRobotSrc())               # brza simulacija: ne


def test_robot_preko_wifi_lidar_on_krugovi_i_snimak(tmp_path, monkeypatch):
    """Virtuelni robot (pravi ESP kod: upload.py, telem.py, lidar.py sa lažnim lidarom na stolu): RobotLidar pošalje
    LIDAR ON, prima krugove (UDP, lidarpkt), snima ih; LIDAR OFF na kraju."""
    monkeypatch.setattr(lidarsrc, "lidar_dir", lambda: tmp_path)
    up, tp = free_port(), free_port(socket.SOCK_DGRAM)
    robot = Sim("primer", mode="live", net={"upload": up, "telem": tp, "password": "pw"},
                obstacles=[{"x": 750, "y": 1000, "w": 300, "h": 300, "z": 350}])
    th = threading.Thread(target=robot.run, daemon=True)
    th.start()
    time.sleep(1.0)
    src = lidarsrc.RobotLidar("127.0.0.1", "pw", up, tp)
    assert src.error is None and src.state not in (None, "off")
    got = []
    t0 = time.time()
    while time.time() - t0 < 4 and len(got) < 8:
        got += src.poll(0)
        time.sleep(0.1)
    src.close()
    lid = robot.app.lidar_remote, __import__("sys").modules["lidar"]._dev.state
    robot.command(("quit",))
    th.join(5)
    assert len(got) >= 8
    assert got[-1]["bins"][0] == pytest.approx(350, abs=3)          # protivnik ispred robota (x 600 - 250)
    assert got[-1]["bins"][180] == pytest.approx(250, abs=3)        # zid iza
    assert lid == (None, "off")                                     # LIDAR OFF ugasio lidar na robotu
    rec = lidarsrc.FileLidar(src.file)                              # snimak se pušta dalje
    assert len(rec.scans) >= 8 and rec.scans[-1]["bins"][0] == got[-1]["bins"][0]


def test_robot_panel_crta_krugove():
    """Robot panel (TelemRecorder): krug iz telemetrije -> događaj "lidar" oko poze robota."""
    r = robotlink.TelemRecorder({})
    r.feed({"t": 1000, "ok": 1, "x": 250, "y": 1000, "th": 0, "sp": 0, "st": 0, "mec": "NEMA"}, 0)
    r.feed_lidar({"t": 1100, "bins": bins_with(a0=350), "hz": 9.7, "near": (350, 0)}, (0, 0, 300))
    ev = [e for e in r.events if e[1] == "lidar"]
    assert ev and ev[0][0] == 100 and ev[0][2]["pose"] == [250, 1000, 0] and ev[0][2]["pts"] == [0, 350]
