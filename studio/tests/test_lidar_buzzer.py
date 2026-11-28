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
    bz = {e[2]["kind"]: e[2]["notes"] for e in r.of("buzzer")}
    assert "boot" in bz                                          # ESP pokrenut (kao main.py)
    assert [hz for hz, ms in bz["greska"] if hz] == [2349] * 3   # STOP: 3 kratka, note iz RTTTL-a
    # ploča S3 ima ekran montiran naopako (DISPLAY_ROT180): slika se okreće, a na robotu izgleda uspravno
    assert s.esp.fb.flip == 1
    assert all(e[2]["flip"] == 0 for e in r.of("screen"))


def test_editor_proverava_play():
    """Lažni tac u editoru (preview.py): play() prima ime ili RTTTL, loš tekst je greška taktike kao na robotu."""
    from eurosim import preview
    ok = preview.preview("from tac import *\nplay('kraj')\nplay('ja:d=8,o=6,b=180:c,e,g')\n")
    assert ok["error"] is None
    bad = preview.preview("from tac import *\nplay('ja:d=8,o=6,b=180:c,x,g')\n")
    assert bad["error"] and "losa nota" in bad["error"]["msg"] and bad["error"]["line"] == 2


def _world(scan):
    """Tačke jednog kruga ("lidar" događaj) u koordinatama stola (mm), kao web/view3d.js setLidar."""
    import math
    x, y, th = scan["pose"]
    ox, oy, _ = scan["o"]
    r = math.radians(th)
    lx, ly = x + ox * math.cos(r) - oy * math.sin(r), y + ox * math.sin(r) + oy * math.cos(r)
    p = scan["pts"]
    return [(lx + d * math.cos(r + math.radians(a)), ly + d * math.sin(r + math.radians(a))) for a, d in zip(p[::2], p[1::2])]


def test_snimak_kruga_lidara_tacke_na_preprekama():
    """Lidar test iz menija: događaji "lidar" (~10 Hz) sa onim što je ESP izmerio; tačke padaju na lice
    protivnika (x = 600) i na zid iza robota (x = 0), a najbliža tačka je zid iza (250 mm)."""
    s, _, _ = live([(300, ("btn", "back", 1)), (1100, ("btn", "back", 0))], obstacles=[OPP], speed=1000)
    idx = [it.label for it in s.app.ui.top.items].index("Lidar test")
    s, r, _ = live([(300, ("btn", "back", 1)), (1100, ("btn", "back", 0)), (1300, ("rot", idx)),
                    (1500, ("btn", "enc", 1)), (1600, ("btn", "enc", 0)), (3500, ("pause", False))],
                   obstacles=[OPP], speed=1000)
    scans = [e for e in r.of("lidar")]
    assert len(scans) >= 10                                     # ~1,5 s skeniranja na 10 Hz
    last = scans[-1][2]
    assert last["pose"][:2] == [250, 1000] and last["hz"] > 5
    pts = _world(last)
    face = [p for p in pts if abs(p[0] - 600) < 8 and abs(p[1] - 1000) < 150]
    back = [p for p in pts if abs(p[0]) < 8]
    assert len(face) >= 10 and len(back) >= 10
    assert last["near"][0] == pytest.approx(250, abs=3)
    assert all(-5 <= x <= 3005 and -5 <= y <= 2005 for x, y in pts)   # sve na stolu (zidovi), ništa van


def test_bez_lidara_nema_dogadjaja():
    s, r, _ = live([(300, ("pause", False))])
    assert not r.of("lidar")
