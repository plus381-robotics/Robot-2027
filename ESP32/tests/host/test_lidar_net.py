# Lidar preko WiFi-ja: krugovi u telemetriji (telem.py, binarni paket), više pretplatnika, LIDAR ON/OFF
# preko upload servera (upload.py), samo gašenje bez pretplatnika i kad se robot naoruža.
import json
import socket

import pytest

import compat
import config
import lidar
import telem
from fakelidar import FakeRplidar
from machine import PWM, UART
from conftest import run
from test_faza3 import server, q          # noqa: F401  (fixture upload servera)


@pytest.fixture
def board(monkeypatch):
    monkeypatch.setattr(lidar, "_dev", None)
    for k, v in dict(LIDAR_UART=2, LIDAR_TX=47, LIDAR_RX=21, LIDAR_MOTOCTL=48).items():
        monkeypatch.setattr(config, k, v, raising=False)
    dev = FakeRplidar(compat.ticks_ms, motor=lambda: bool(PWM.pins.get(48) and PWM.pins[48].duty_u16()))
    monkeypatch.setitem(UART.devices, 2, dev)
    return dev


@pytest.fixture
def tel(app, monkeypatch):
    import state
    monkeypatch.setattr(state, "MODE", "STA")
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    t = telem.Telem(app, port=port)
    t.poll()
    return t, port


def client(port):
    c = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    c.bind(("127.0.0.1", 0))
    c.settimeout(0.05)
    c.sendto(b"WATCH", ("127.0.0.1", port))
    return c


def drain(c):
    out = []
    while True:
        try:
            out.append(c.recv(4096))
        except (socket.timeout, BlockingIOError):
            return out


def pump(app, t, ms, step=10):
    for _ in range(ms // step):
        run(app, step)
        t.poll()


def test_paket_tam_i_nazad():
    class L:
        scans, hz, nearest = 7, 9.7, (233, -45)
        dist = [0] * 360
    L.dist[0], L.dist[90], L.dist[359] = 600, 400, 12000
    p = telem.parse_lidar(bytes(telem.lidar_packet(L, 123456)))
    assert p["t"] == 123456 and p["scan"] == 7 and p["hz"] == 9.7 and p["near"] == (233, -45)
    assert p["bins"][0] == 600 and p["bins"][90] == 400 and p["bins"][359] == 12000 and sum(p["bins"]) == 13000
    assert len(telem.lidar_packet(L, 0)) < 1400                          # jedan UDP paket bez fragmentacije
    assert telem.parse_lidar(b'{"t": 1}') is None


def test_dva_pretplatnika_oba_dobijaju_stanje(app, tel):
    t, port = tel
    a, b = client(port), client(port)
    pump(app, t, 300)
    for c in (a, b):
        got = [json.loads(x) for x in drain(c) if x[:1] == b"{"]
        assert got and "mec" in got[-1]


def test_krug_lidara_ide_pretplatniku(app, tel, board):
    t, port = tel
    c = client(port)
    app.ui.push(app.settings_menu())
    scr = app.lidar_screen()                                # Lidar test na robotu
    app.ui.push(scr)
    pump(app, t, 1000)
    pk = [telem.parse_lidar(x) for x in drain(c)]
    scans = [p for p in pk if p]
    assert len(scans) >= 5 and len({p["scan"] for p in scans}) == len(scans)     # svaki krug jednom
    assert abs(scans[-1]["bins"][0] - 600) <= 2 and scans[-1]["hz"] > 5
    assert all(p is None or p["ver"] == 1 for p in pk)


def test_lidar_on_preko_wifi_salje_krugove_pa_se_gasi(app, tel, board, server):
    t, port = tel
    c = client(port)
    assert q("LIDAR ON")[-1].startswith("OK")
    assert app.lidar_remote is not None and lidar._dev.state != "off"
    pump(app, t, 1000)                                      # telem čita lidar (nema ekrana Lidar test)
    scans = [p for p in (telem.parse_lidar(x) for x in drain(c)) if p]
    assert len(scans) >= 5
    c.close()                                               # laptop nestao: posle SUB_MS se lidar gasi sam
    pump(app, t, telem.SUB_MS + telem.REMOTE_GRACE_MS + 500, step=50)
    assert app.lidar_remote is None and lidar._dev.state == "off"
    assert PWM.pins[48].duty_u16() == 0                     # i motor


def test_lidar_off_i_naoruzavanje_gase(app, tel, board, server, stm):
    t, port = tel
    client(port)
    assert q("LIDAR ON")[-1].startswith("OK")
    pump(app, t, 300)
    assert q("LIDAR OFF")[-1] == "OK off"
    assert lidar._dev.state == "off"
    assert q("LIDAR ON")[-1].startswith("OK")
    (app.tactics_dir / "m.py").write_text("from tac import *\nSTART = (250, 1000, 0)\nmove(100)\n")
    pump(app, t, 300)
    assert app.match.arm("m", "zuta")                        # meč ima prednost
    pump(app, t, 100)
    assert app.lidar_remote is None and lidar._dev.state == "off"
    assert q("LIDAR ON")[-1].startswith("ERR")              # naoružan: odbija


def test_lidar_on_bez_lidara(app, server, monkeypatch):
    monkeypatch.setattr(lidar, "_dev", None)
    monkeypatch.setattr(config, "LIDAR_UART", None, raising=False)
    assert q("LIDAR ON")[-1] == "ERR nema lidara na ploci"
