# Lidar (lib/lidar.py) sa lažnim RPLIDAR-om (sim/fakelidar.py): tok INFO/HEALTH/SCAN, parser tačaka,
# resync posle smeća, nema odgovora, ekran Meni -> Lidar test (lib/lidar_test.py).
import pytest

import compat
import config
import fakelidar
import lidar
from fakelidar import FakeRplidar, node, descriptor
from lidar import Lidar
from machine import PWM, UART


class Motor:
    def __init__(self):
        self.d = 0

    def duty_u16(self, d=None):
        if d is None:
            return self.d
        self.d = d


def spin(L, ms, step=10):
    for _ in range(ms // step):
        L.poll()
        compat.sleep_ms(step)


@pytest.fixture
def dev():
    return FakeRplidar(compat.ticks_ms)


def test_tok_do_skeniranja(dev):
    m = Motor()
    L = Lidar(dev, m, motor_duty=60)
    L.start()
    assert m.d == 60 * 65535 // 100                     # motor odmah
    spin(L, 1000)
    assert dev.cmds[:4] == [lidar.CMD_STOP, lidar.CMD_INFO, lidar.CMD_HEALTH, lidar.CMD_SCAN]
    assert L.info["model"] == 0x28 and L.info["fw"] == "1.29"
    assert L.health == (0, 0)
    assert L.scanning and L.bad == 0
    assert abs(L.hz - fakelidar.HZ) < 0.5
    assert L.points == fakelidar.RATE // fakelidar.HZ


def test_udaljenosti_i_uglovi_robota(dev):
    """Soba 1200 x 800 (robot u sredini): napred 600, levo/desno 400. Ugao robota: + = levo."""
    L = Lidar(dev)
    L.start()
    spin(L, 600)
    assert abs(L.dist[0] - 600) <= 2 and abs(L.dist[180] - 600) <= 2
    assert abs(L.dist[90] - 400) <= 2 and abs(L.dist[270] - 400) <= 2
    # protivnik (krug r 100) na 500 napred, 300 levo: ~ 31° levo, ~ 483 mm
    assert abs(L.dist[31] - 483) <= 10


def test_ugao_montaze(dev):
    """Lidar okrenut unazad (0° lidara gleda u 180° robota): prepreka desno od lidara (90°) je levo od robota."""
    dev.ranges = lambda a: 1000 if abs(a - 90) < 1 else 0          # samo jedna prepreka: 90° lidara (desno)
    L = Lidar(dev, mount_deg=180)
    L.start()
    spin(L, 600)
    hit = [k for k in range(360) if L.dist[k]]
    assert hit and all(abs(k - 90) <= 1 for k in hit)              # 180 - 90 = 90° robota (levo)


def test_najbliza_tacka(dev):
    dev.ranges = lambda a: 300 if 350 <= a or a <= 2 else 2000      # blizu, malo desno od napred
    L = Lidar(dev)
    L.start()
    spin(L, 600)
    d, a = L.nearest
    assert d == 300 and -2 <= a <= 10


def test_resync_posle_smeca():
    clock = compat.ticks_ms
    dev = FakeRplidar(clock)
    L = Lidar(dev)
    L.start()
    spin(L, 400)
    assert L.scanning
    bad0 = L.bad
    dev.out += b"\x00\x13\x37\xff\xa5"                   # smeće usred toka tačaka
    spin(L, 500)
    assert L.bad > bad0
    assert L.scanning and L.points >= 190                  # krugovi posle toga su opet celi


def test_parser_tacaka_po_bajt():
    """Tačke stižu deo po deo (UART), krug počinje bitom S."""
    class Dev:
        def __init__(self):
            self.out = bytearray()
        def write(self, b):
            return len(b)
        def any(self):
            return min(3, len(self.out))                    # najviše 3 bajta po krugu petlje
        def read(self, n):
            d = bytes(self.out[:n]); del self.out[:n]; return d
    d = Dev()
    L = Lidar(d)
    L.state, L._cmd = "scanwait", lidar.CMD_SCAN
    L._t = compat.ticks_ms()
    d.out += descriptor(5, 0x81, 1)
    for rev in range(3):
        for k in range(4):
            d.out += node(k * 90, 1000 + k, start=(k == 0))
    d.out += node(0, 500, start=True)                      # počinje 4. krug: 3. se zatvara
    for _ in range(200):
        L.poll()
    assert L.scans == 3 and L.points == 4
    assert [L.dist[a] for a in (0, 270, 180, 90)] == [1000, 1001, 1002, 1003]   # 90° lidara = desno = 270° robota


def test_nema_odgovora(dev):
    dev.mute = True
    m = Motor()
    L = Lidar(dev, m)
    L.start()
    spin(L, 3000)
    assert L.state == "greska" and L.why == "nema odgovora"
    assert dev.cmds.count(lidar.CMD_INFO) == lidar.TRIES
    assert m.d == 0                                         # motor ugašen


def test_zdravlje_greska(dev):
    dev.health = (2, 0x8001)
    L = Lidar(dev)
    L.start()
    spin(L, 500)
    assert L.state == "greska" and "32769" in L.why


def test_motor_stoji_pa_ponovo(dev):
    on = [True]
    dev.motor = lambda: on[0]
    L = Lidar(dev)
    L.start()
    spin(L, 500)
    assert L.scanning
    on[0] = False
    spin(L, lidar.STALL_MS + 200)
    assert L.restarts == 1 and not L.scanning
    on[0] = True
    spin(L, 800)
    assert L.scanning


def test_stop_gasi_motor_i_skeniranje(dev):
    m = Motor()
    L = Lidar(dev, m)
    L.start()
    spin(L, 400)
    L.stop()
    assert m.d == 0 and L.state == "off" and not dev.scanning
    spin(L, 300)
    assert not dev.out                                      # bafer se prazni i kad je isključen


# ---------------- ekran Meni -> Lidar test ----------------

@pytest.fixture
def board(monkeypatch):
    """Lažni lidar na UART-u lidara (kao simulator), motor na lažnom PWM-u."""
    monkeypatch.setattr(lidar, "_dev", None)
    for k, v in dict(LIDAR_UART=2, LIDAR_TX=47, LIDAR_RX=21, LIDAR_MOTOCTL=48).items():
        monkeypatch.setattr(config, k, v, raising=False)
    pin = 48
    dev = FakeRplidar(compat.ticks_ms, motor=lambda: bool(PWM.pins.get(pin) and PWM.pins[pin].duty_u16()))
    monkeypatch.setitem(UART.devices, 2, dev)
    return dev


def test_ekran_pali_i_gasi_lidar(app, board):
    import ssd1306
    from conftest import run
    app.ui.fb = app.fb = ssd1306.SSD1306_I2C(128, 64)
    app.ui.push(app.settings_menu())
    scr = app.lidar_screen()
    app.ui.push(scr)
    run(app, 800)
    L = scr.lidar
    assert L.scanning and PWM.pins[48].duty_u16() > 0
    px = app.fb.frames[-1]
    assert sum(map(sum, px[17:])) > 50                      # mapa: tačke ispod naslova
    scr.ok(app.ui)
    run(app, 200)
    app.ui.input("back")                                    # izlaz: motor staje
    assert L.state == "off" and PWM.pins[48].duty_u16() == 0


def test_taktika_krene_lidar_se_gasi(app, board):
    app.ui.push(app.settings_menu())
    scr = app.lidar_screen()
    app.ui.push(scr)
    from conftest import run
    run(app, 500)
    app.show_page("TAKTIKA")                                # isto što radi početak taktike (ui.home)
    assert scr.lidar.state == "off"


def test_ploca_bez_lidara(app, monkeypatch):
    monkeypatch.setattr(lidar, "_dev", None)
    monkeypatch.setattr(config, "LIDAR_UART", None, raising=False)
    scr = app.lidar_screen()
    assert scr.lidar is None and scr.err == "nema na ploci"
    app.ui.push(scr)
    app.ui.draw()
