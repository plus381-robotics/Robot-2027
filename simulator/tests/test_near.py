# Prilaz elementu igre (plan S12, protokol v5): bez near IR vidi kamenolom i robot stane (BLOCKED); sa near
# stigne do kamenoloma; stari STM32 (v4) ne zna za near i staje kao ranije.
from eurosim import profile
from eurosim.sim import simulate

SRC = ("from tac import *\nSTART = (250, 1000, 0)\ngoto(750, 1538, deg=90)\n"
       "log('rez %s' % goto(750, 1770, deg=90, near={near}))\n")


def run(tmp_path, near, version=5):
    (tmp_path / "t.py").write_text(SRC.format(near=near))
    return simulate("t", tactics_dir=tmp_path, prof=profile.load(**{"link.protocol_version": version}))


def test_bez_near_ir_zaustavi_robota_ispred_kamenoloma(tmp_path):
    r = run(tmp_path, False)
    assert "rez False" in r.logs() and r.steps()[1][3] == "BLOCKED"


def test_near_stigne_do_kamenoloma_sporo(tmp_path):
    r = run(tmp_path, True)
    assert "rez True" in r.logs()
    assert abs(r.result["pose"][1] - 1770) < 15
    v = [abs(f["v"]) for f in r.frames if f["y"] > 1560]
    assert v and max(v) <= 0.2 + 0.03                              # najviše 200 mm/s u prilazu


def test_stari_stm32_v4_ne_zna_za_near(tmp_path):
    r = run(tmp_path, True, version=4)
    assert "rez False" in r.logs() and any("ne zna za prilaz" in l for l in r.logs())
