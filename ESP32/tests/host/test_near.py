# Protokol v5: near=True u goto/move (prilaz elementu igre: IR ne zaustavlja robota, najviše 200 mm/s).
import protocol as P
from conftest import run


def _run(app, src):
    from runner import run_tactic
    (app.tactics_dir / "t.py").write_text("from tac import *\n" + src)
    run(app, 300)
    run_tactic(app, "t")


def test_near_salje_zastavicu_i_ogranicava_brzinu(app, stm):
    _run(app, "goto(750, 1770, deg=90, speed=600, near=True)\nmove(-100, near=True)\nmove(-50)\n")
    g = [d for n, d in stm.sent if n == "GOTO"][-1]
    assert g["flags"] & P.GotoFlags.NEAR and g["max_speed"] == 200
    mv = [d for n, d in stm.sent if n == "MOVE"]
    assert mv[0]["flags"] == P.GotoFlags.NEAR and mv[0]["max_speed"] == 200
    assert mv[1]["flags"] is None                                # bez near: poruka kao u v4


def test_stari_stm32_bez_near_salje_bez_zastavice_i_javlja(app, stm):
    stm.version = 4
    _run(app, "goto(750, 1770, near=True)\nmove(-100, near=True)\n")
    g = [d for n, d in stm.sent if n == "GOTO"][-1]
    assert not g["flags"] & P.GotoFlags.NEAR
    assert [d for n, d in stm.sent if n == "MOVE"][-1]["flags"] is None
    assert any("ne zna za prilaz" in l for l in app.log)
