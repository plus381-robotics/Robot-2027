# Cela simulacija: prava taktika + pravi ESP kod (tac, robot, runner, match, app) + SimSTM.
import pytest

from eurosim.sim import Sim, simulate


def write(tmp_path, name, src):
    (tmp_path / (name + ".py")).write_text("from tac import *\n" + src)
    return tmp_path


def test_primer_mec_zuta_svi_koraci_ok():
    r = simulate("primer", side="zuta", mode="mec")        # zuta = REF_SIDE: bez ogledanja
    assert r.result["ok"] and r.result["start_in_zone"]       # START (250, 1000) je u žutoj zoni (pravila 2027)
    assert [s[1] for s in r.steps()] == ["GOTO 600,1000", "OKRET na 90", "MOVE -200"]
    x, y, th = r.result["pose"]
    assert abs(x - 600) < 20 and abs(y - 800) < 25 and abs(th - 90) < 2
    logs = r.logs()
    assert logs[0].startswith("NAORUZAN") and "CINC: start" in logs


@pytest.mark.parametrize("mode", ["mec", "test"])
def test_zuta_strana_je_ogledalo_plave(mode):
    a = simulate("primer", side="plava", mode=mode)
    b = simulate("primer", side="zuta", mode=mode)
    (xa, ya, tha), (xb, yb, thb) = a.result["pose"], b.result["pose"]
    assert abs((3000 - xa) - xb) < 2 and abs(ya - yb) < 2 and abs((180 - tha) - thb) < 1


def test_deterministicno():
    a = simulate("primer", side="zuta", mode="test")
    b = simulate("primer", side="zuta", mode="test")
    assert a.frames == b.frames and a.events == b.events


def test_protivnik_ispred_blocked_i_taktika_dobija_false(tmp_path):
    d = write(tmp_path, "t", "START = (250, 1000, 0)\nok = goto(1500, 1000, speed=600)\nlog('rez %s' % ok)\n")
    r = simulate("t", tactics_dir=d, mode="mec", obstacles=[dict(x=900, y=1000, w=300, h=300)])
    assert "rez False" in r.logs()
    assert r.steps()[0][2] is False and r.steps()[0][3] == "BLOCKED"
    assert r.result["pose"][0] < 900 - 150 - 82                 # stao pre protivnika
    hits = [f["irh"] for f in r.frames if f.get("irh")]           # plan S6: udaljenosti po senzoru za prikaz zraka
    assert hits and len(hits[0]) == 8 and all(0 <= h <= 250 for h in hits[0][:4] if h >= 0)
    assert all(h == -1 for h in hits[0][4:])                       # zadnji senzori ne vide protivnika ispred


def test_zid_blocked(tmp_path):
    d = write(tmp_path, "t", "START = (250, 1000, 0)\nlog('rez %s' % move(-400))\n")
    r = simulate("t", tactics_dir=d, mode="mec")
    assert "rez False" in r.logs() and r.steps()[0][3] == "BLOCKED"


def test_100s_prekida_taktiku(tmp_path):
    d = write(tmp_path, "t", "START = (250, 1000, 0)\nwhile True:\n    move(300)\n    move(-300)\n")
    r = simulate("t", tactics_dir=d, mode="mec")
    assert r.result["match_over"]
    assert any("kraj meca" in l.lower() for l in r.logs())
    assert 100000 < r.result["sim_ms"] < 106000


def test_stop_taster_prekida(tmp_path):
    d = write(tmp_path, "t", "START = (250, 1000, 0)\ngoto(2000, 1000, speed=300)\nlog('ne sme')\n")
    sim = Sim("t", tactics_dir=d, mode="mec", schedule=[(2.0, lambda s: setattr(s, "stop_requested", True))])
    r = sim.run()
    assert "ne sme" not in r.logs()
    assert r.result["how"] == "STOP"
    assert any(e[2]["name"] == "STOP" for e in r.of("rx"))


def test_aktuator_paralelno_sa_voznjom(tmp_path):
    d = write(tmp_path, "t", "START = (250, 1000, 0)\nh = actuator('lift', 300, wait=False)\n"
                             "goto(700, 1000)\nlog('lift %s' % wait_done(h))\n")
    r = simulate("t", tactics_dir=d, mode="test")
    assert "lift True" in r.logs()
    assert r.frames[-1]["act"] == {"2": 300}


def test_greska_u_taktici_ne_rusi_simulaciju(tmp_path):
    d = write(tmp_path, "t", "START = (250, 1000, 0)\n1 / 0\n")
    r = simulate("t", tactics_dir=d, mode="test")
    assert not r.result["ok"]
    assert any("ZeroDivisionError" in l for l in r.logs())


def test_snimak_se_cuva_i_ucitava(tmp_path):
    from eurosim.record import Recording
    r = simulate("primer", mode="test")
    r.save(tmp_path / "x.json.gz")
    q = Recording.load(tmp_path / "x.json.gz")
    assert q.meta["tactic"] == "primer" and len(q.frames) == len(r.frames) and q.result["ok"]


def test_esp_moduli_citaju_utf8_i_na_windowsu():
    """ESP kod otvara taktike sa open(path) (na ESP-u uvek UTF-8); na Windows-u CPython bi uzeo cp1252."""
    import sys
    from eurosim.esp import _open_utf8
    Sim("primer", mode="test")
    for n in ("runner", "match", "app", "settings"):
        assert sys.modules[n].open is _open_utf8


def test_elementi_igre_2027():
    """Pravila 2027: 10 kamenoloma po 3 kamena (320x110x110), simetrično po x; zone bedema."""
    from eurosim import field
    el = field.elements()
    assert len(el) == 10 and sum(e["stones"] for e in el) == 30
    xs = sorted((e["x"], e["y"]) for e in el)
    assert xs == sorted((3000 - x, y) for x, y in xs)                     # plava = ogledalo žute
    kinds = [z["kind"] for z in field.ZONES]
    assert kinds.count("kula") == 8 and kinds.count("zid") == 4 and kinds.count("kapija") == 2


def test_kamenolom_na_putu_blocked_a_bez_elemenata_stize(tmp_path):
    # donji IR (D, 40 mm) vidi kamenolom i staje ispred; gornji (U, 340 > 330 mm) ga ne vide. Sa ir_off("FD") robot
    # vozi u kamenolom i zaglavi se (BLOCKED); bez elemenata stiže
    src = "START = (250, 1000, 0)\n{off}log('rez %s' % goto(750, 1830, speed=400))\n"
    d = write(tmp_path, "t", src.format(off=""))
    r = simulate("t", tactics_dir=d, mode="mec")
    assert "rez False" in r.logs() and r.steps()[0][3] == "BLOCKED"       # kamenolom (750, 1945)
    seen = [f["irh"] for f in r.frames if f.get("irh")]                  # po senzoru FLD FLU FRD FRU BLD ...
    assert seen and all(max(h[0], h[2]) >= 0 and h[1] < 0 and h[3] < 0 for h in seen)  # samo donji prednji
    assert r.result["pose"][1] < 1890 - 82 - 20                           # stao pre kamenoloma
    d = write(tmp_path, "t", src.format(off="ir_off('FD')\n"))
    r1 = simulate("t", tactics_dir=d, mode="mec")
    assert "rez False" in r1.logs() and r1.result["pose"][1] > r.result["pose"][1]   # vozio do sudara
    assert len(r.meta["elements"]) == 10 and r.meta["obstacles"] == []
    r2 = simulate("t", tactics_dir=d, mode="mec", elements=False)
    assert "rez True" in r2.logs()


def test_ir_off_prednji_ne_zaustavljaju(tmp_path):
    """Protokol v5: ir_off('F') -> prednji senzori ne zaustavljaju robota (i dalje mere), pa udari u protivnika."""
    opp = [dict(x=900, y=1000, w=300, h=300)]
    src = "START = (250, 1000, 0)\n{off}log('rez %s' % goto(1500, 1000, speed=400))\n"
    on = simulate("t", tactics_dir=write(tmp_path, "t", src.format(off="")), mode="mec", obstacles=opp)
    off = simulate("t", tactics_dir=write(tmp_path, "t", src.format(off="ir_off('F')\n")), mode="mec", obstacles=opp)
    assert on.steps()[0][3] == "BLOCKED" and off.steps()[-1][3] == "BLOCKED"
    x_on, x_off = on.result["pose"][0], off.result["pose"][0]
    assert x_on < 900 - 150 - 82 - 100 < x_off                       # sa IR stao ranije; bez IR tek na sudaru
    f = [f for f in off.frames if f.get("irh")]
    assert any(x["irm"] == 0xF0 for x in f)                         # mereno i kad je isključen; maska u snimku
    assert off.frames[-1]["irm"] == 0xFF                           # na kraju taktike svi ponovo uključeni
