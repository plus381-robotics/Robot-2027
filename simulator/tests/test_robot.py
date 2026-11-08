# F4/F5: virtuelni robot (pravi upload.py i telem.py nad simulacijom), veza preko espnet i UDP telemetrije,
# snimak iz telemetrije, profil iz interfejsa, samostalni režim (putanje).
import json
import shutil
import socket
import threading
import time

from eurosim import paths, profile as P, robotlink
from eurosim.sim import Sim


def free_port(kind=socket.SOCK_STREAM):
    s = socket.socket(socket.AF_INET, kind)
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def test_virtuelni_robot_push_run_telemetrija():
    up, tp = free_port(), free_port(socket.SOCK_DGRAM)
    sim = Sim("primer", mode="live", net={"upload": up, "telem": tp, "password": "pw"})
    sim.speed = 3.0
    th = threading.Thread(target=sim.run, daemon=True)
    th.start()
    time.sleep(1.0)
    rec = robotlink.TelemRecorder({})
    u = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    u.settimeout(0.2)
    u.sendto(b"WATCH", ("127.0.0.1", tp))
    src = (paths.TACTICS / "primer.py").read_bytes()
    ok, lines = robotlink.command("127.0.0.1", "pw", "PUT /tactics/primer.py %d" % len(src), src, port=up)
    assert ok, lines
    ok, lines = robotlink.command("127.0.0.1", "pw", "RUN primer zuta", port=up)
    assert ok, lines
    assert not robotlink.command("127.0.0.1", "pogresna", "STAT", port=up)[0]       # prijava izazovom
    t0 = time.time()
    while time.time() - t0 < 6:
        try:
            rec.feed(json.loads(u.recv(4096)), 0)
        except socket.timeout:
            pass
    sim.command(("quit",))
    th.join(5)
    rec.finish()
    names = [e[2][1] for e in rec.events if e[1] == "step"]
    assert "GOTO 600,1000" in names and "MOVE -200" in names
    ends = [e[2] for e in rec.events if e[1] == "step_end"]
    assert all(x[2] is True for x in ends if x[1] in ("GOTO 600,1000", "OKRET na 90"))
    assert rec.meta["tactic"] == "primer" and rec.meta["side"] == "zuta"
    assert abs(rec.frames[-1]["x"] - 2400) < 30                                     # žuta: ogledano


def test_telemetrija_neuspeli_korak_iz_dnevnika():
    r = robotlink.TelemRecorder({})
    r.feed({"t": 0, "ok": 1, "x": 0, "y": 0, "th": 0, "sp": 0, "st": 0, "tac": "t", "i": 1, "step": "GOTO 1,2",
            "to": 3000, "side": "plava", "mec": "NEMA"}, 0)
    r.feed({"t": 500, "ok": 1, "x": 0, "y": 0, "th": 0, "sp": 0, "st": 0, "tac": "t", "i": 2, "step": "MOVE 5",
            "log": ["GOTO 1,2: BLOCKED"]}, 500)
    end = [e[2] for e in r.events if e[1] == "step_end"][0]
    assert end[:4] == [1, "GOTO 1,2", False, "BLOCKED"]


def test_profil_iz_interfejsa_cuva_komentare(tmp_path):
    f = tmp_path / "p.toml"
    shutil.copy(paths.DEFAULT_PROFILE, f)
    before = f.read_text(encoding="utf-8")
    P.update_file(f, {"drive.wheel_track": 180, "ir.see_walls": True})
    after = f.read_text(encoding="utf-8")
    assert P.load(f)["drive"]["wheel_track"] == 180 and P.load(f)["ir"]["see_walls"] is True
    assert after.count("#") == before.count("#")                                   # komentari ostaju
    sec = {s["name"]: s for s in P.describe(f)}
    assert any("(P)" in i["comment"] for i in sec["drive"]["items"])


def test_samostalni_rezim_pravi_home(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "find_repo", lambda: None)
    monkeypatch.delenv("EUROSIM_ROOT", raising=False)
    try:
        paths.configure(home=tmp_path / "Eurosim")
        assert paths.MODE == "standalone"
        assert (tmp_path / "Eurosim" / "tactics" / "primer.py").exists()
        assert paths.DEFAULT_PROFILE.parent == tmp_path / "Eurosim" / "profiles"
    finally:
        monkeypatch.delenv("EUROSIM_HOME", raising=False)
        monkeypatch.undo()
        paths.configure()
    assert paths.MODE == "repo"
