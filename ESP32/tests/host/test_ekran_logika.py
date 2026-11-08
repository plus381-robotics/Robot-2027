# Ekran i natpisi (pregled logike L13, L22, L25, L28).
import compat
import tekst as T
import ui
from conftest import run


def test_drzanje_ok_na_ugasenom_ekranu_ne_potvrdjuje(app):
    """L13: ekran spava sa otvorenom potvrdom: držanje OK ga samo pali; potvrda se zatvara pri gašenju."""
    fired = []
    u = app.ui
    u.push(ui.Confirm("Test", ["x"], lambda u2: fired.append(1)))
    app.st["sleep_s"] = 60
    compat.fake[0] += 61000
    u.tick()
    assert u.asleep and not isinstance(u.top, ui.Confirm)        # ugašen ekran je zatvorio potvrdu
    u.push(ui.Confirm("Test", ["x"], lambda u2: fired.append(1)))
    u.asleep = True
    for ms in (0, 300, 900, 1500):
        u.hold(ms)
    assert fired == [] and not u.asleep                           # samo upaljen
    u.hold(0)
    for ms in (300, 900):
        u.hold(ms)
    assert fired == [1]                                           # novo držanje (budan ekran) potvrđuje


def test_potvrda_se_sama_zatvara(app):
    u = app.ui
    u.push(ui.Confirm("Test", ["x"], lambda u2: None))
    compat.fake[0] += 11000
    u.tick()
    assert not isinstance(u.top, ui.Confirm)


def test_greska_van_taktike_bez_vremena_i_isto_ime(app, stm):
    """L25: greška van taktike nema "t+<uptime>"; traka i dnevnik pišu isto ime komande."""
    app.error("nesto")
    assert app.errors[-1] == (None, "nesto")
    stm.act_fail = 1                                              # INVALID
    run(app, 300)
    app.robot.send("ACTUATOR", id=1, value=1)
    run(app, 300)
    assert any(t == "ACTUATOR: odbijeno" for _, t in app.errors)


def test_poruka_o_verziji(app):
    """L28: stariji STM32 -> flešuj STM32; noviji -> ESP je star."""
    assert T.version_msg(1, 3) == "STM32 v1, flesuj"
    assert T.version_msg(4, 3) == "ESP star: STM v4"
    assert T.version_msg(None, 3) == "STM32 nema verz."


def test_izvestaj_poza_nase_strane(app, stm):
    """L22: izveštaj pokazuje pozu naše strane (kao dnevnik), teren posebno."""
    from runner import run_tactic
    (app.tactics_dir / "t.py").write_text("from tac import *\nSTART = (300, 900, 0)\nwait(0.2)\n")
    run(app, 300)
    app.side = "plava"
    run_tactic(app, "t")
    assert app.report["pose"] == [300, 900, 0] and app.report["pose_field"] == [2700, 900, 180]
