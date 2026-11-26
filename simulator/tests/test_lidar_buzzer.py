# Lažni lidar u simulatoru (ESP32/sim/fakelidar.py + Sim.lidar_range) i buzzer: ESP kod ih vidi kao pravi hardver.
import pytest

from eurosim.sim import Sim
from test_live import live

OPP = {"x": 750, "y": 1000, "w": 300, "h": 300, "z": 350, "name": "protivnik"}


def test_zrak_vidi_ivicu_prepreke_i_zid():
    s = Sim("primer", side="zuta", obstacles=[OPP])            # robot na (250, 1000), gleda u +x
    assert s.lidar is not None
    assert s.lidar_range(0) == pytest.approx(350, abs=2)        # prednja ivica protivnika na x = 600
    assert s.lidar_range(180) == pytest.approx(250, abs=2)      # zid iza (x = 0)
    assert s.lidar_range(90) == pytest.approx(1000, abs=2)      # 90° lidara = desno = zid y = 0
    assert s.lidar_range(270) == pytest.approx(1000, abs=2)


def test_nizak_predmet_se_ne_vidi():
    s = Sim("primer", side="zuta", obstacles=[dict(OPP, z=100)], elements=False)
    assert s.lidar_range(0) == pytest.approx(2750, abs=2)       # PAMI/niska kutija ispod ravni lidara: zid x = 3000


def test_meni_lidar_test_preko_tastera():
    """Dugi NAZAD -> meni, okret do "Lidar test", klik: ESP otvara UART lidara i vidi protivnika napred."""
    s, r, _ = live([(300, ("btn", "back", 1)), (1100, ("btn", "back", 0))], obstacles=[OPP], speed=1000)
    names = [it.label for it in s.app.ui.top.items]
    idx = names.index("Lidar test")
    s, r, _ = live([(300, ("btn", "back", 1)), (1100, ("btn", "back", 0)), (1300, ("rot", idx)),
                    (1500, ("btn", "enc", 1)), (1600, ("btn", "enc", 0)), (3500, ("pause", False))],
                   obstacles=[OPP], speed=1000)
    scr = s.app.ui.top
    L = scr.lidar
    assert type(scr).__name__ == "LidarScreen" and L.scanning
    assert L.info["fw"] == "1.29" and L.bad == 0
    assert L.dist[0] == pytest.approx(350, abs=3) and L.dist[180] == pytest.approx(250, abs=3)
    assert L.nearest[0] == pytest.approx(250, abs=3)


def test_buzzer_i_okrenut_ekran():
    s, r, _ = live([(300, ("btn", "stop", 1)), (400, ("btn", "stop", 0))])
    bz = r.of("buzzer")
    assert bz and bz[0][2]["kind"] == "greska" and len(bz[0][2]["tones"]) == 5
    # ploča S3 ima ekran montiran naopako (DISPLAY_ROT180): slika se okreće, a na robotu izgleda uspravno
    assert s.esp.fb.flip == 1
    assert all(e[2]["flip"] == 0 for e in r.of("screen"))
