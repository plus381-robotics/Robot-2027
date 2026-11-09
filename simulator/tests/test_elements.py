# Elementi igre (plan E3): izmenjen sto (manje kamenova, uklonjen kamenolom), guranje, snimanje promena.
from eurosim import field
from eurosim.sim import simulate

PUSH = ("from gambit import *\nSTART = (1093, 1500, 0)\nir_off('FD')\n"   # donji prednji bi ga videli i stali
        "log('rez %s' % move(500, speed=300, timeout=8))\n")      # u srednji kamenolom (1500, 1500), okrenut 90°


def write(tmp_path, src):
    (tmp_path / "t.py").write_text(src)
    return tmp_path


def test_robot_gura_kamenolom_i_promena_se_snima(tmp_path):
    r = simulate("t", tactics_dir=write(tmp_path, PUSH), mode="test")
    ev = [e for e in r.events if e[1] == "elements"]
    assert ev, "nema događaja elements"
    q9 = [e for e in ev[-1][2] if e["name"] == "kamenolom 9"][0]
    assert q9["x"] > 1500 + 150                                           # pomeren u smeru guranja
    assert abs(q9["y"] - 1500) < 5                                        # pravo, bez skretanja
    assert r.meta["elements"][8]["x"] == 1500                             # početno stanje ostaje u meta


def test_bez_guranja_robot_se_zaglavi(tmp_path):
    from eurosim import profile
    r = simulate("t", tactics_dir=write(tmp_path, PUSH), mode="test",
                 prof=profile.load(**{"elements.pushable": False}))
    assert "rez False" in r.logs() and not [e for e in r.events if e[1] == "elements"]


def test_kamenolom_uz_ivicu_ne_ide_kroz_zid(tmp_path):
    src = "from gambit import *\nSTART = (750, 1700, 90)\nlog('rez %s' % move(300, timeout=6))\n"
    r = simulate("t", tactics_dir=write(tmp_path, src), mode="test")
    assert "rez False" in r.logs()                                        # kamenolom je uz ivicu: ne može dalje
    for e in [e for e in r.events if e[1] == "elements"]:
        for q in e[2]:
            assert q["y"] + q["h"] / 2 <= 2000 + 1


def test_izmenjen_sto_bez_kamenoloma_i_manje_kamenova(tmp_path):
    el = field.elements()
    el[8]["stones"] = 0                                                   # srednji kamenolom uklonjen
    r = simulate("t", tactics_dir=write(tmp_path, PUSH), mode="test", elements=el)
    assert "rez True" in r.logs() and len(r.meta["elements"]) == 9        # put je slobodan
    el = field.elements()
    el[8]["stones"] = 1
    assert field.element(el[8])["z"] == 110
