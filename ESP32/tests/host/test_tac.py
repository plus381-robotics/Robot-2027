import protocol as P
from conftest import run


def write(app, name, src):
    (app.tactics_dir / (name + ".py")).write_text(src)


def test_taktika_vozi_i_zavrsi(app, stm):
    from runner import run_tactic
    from tactic import tracker
    write(app, "t", "from tac import *\npose(0, 0)\nassert goto(500, 0)\nassert rotate(90)\n")
    run(app, 300)
    run_tactic(app, "t")
    assert stm.executed[-3:] == ["SET_POSE", "GOTO", "ROTATE"]
    assert [h[2] for h in tracker.history] == [True, True, True]
    assert app.running is None and app.log[-1].startswith("KRAJ")


def test_stop_brise_izabranu_taktiku(app):
    """K-1: taktika izabrana pa STOP: ne sme da krene posle."""
    app.start_tactic("x100")
    app.stop()
    assert app.request is None


def test_izbor_dok_radi_se_ignorise(app):
    app.running = "a"
    app.start_tactic("b")
    assert app.request is None


def test_kretanje_bez_odgovora_salje_stop(app, stm):
    """P-3: GOTO bez ACK-a posle 3 pokušaja -> STOP, a taktika dobije False."""
    from runner import run_tactic
    write(app, "t", "from tac import *\nok = goto(500, 0)\nlog('rezultat %s' % ok)\n")
    run(app, 300)
    stm.drop = 3
    run_tactic(app, "t")
    assert "GOTO" not in stm.executed and stm.executed[-1] == "STOP"
    assert "rezultat False" in app.log


def test_greska_u_taktici_ne_gasi_program(app, stm):
    """R-1: i SystemExit iz taktike se hvata; robot dobije STOP."""
    from runner import run_tactic
    write(app, "t", "import sys\nsys.exit('kraj')\n")
    run(app, 300)
    run_tactic(app, "t")
    assert stm.executed[-1] == "STOP" and app.running is None
    assert any(l.startswith("GRESKA") for l in app.log)


def test_auto_poza_samo_van_meca(app, stm):
    """R-3: posle (re)starta ESP-a usred meča nema SET_POSE."""
    stm.state = P.State.MATCH_RUNNING
    run(app, 500)
    assert "SET_POSE" not in stm.executed
    from robot import Robot
    from app import App
    app2 = App(Robot(stm), app.st, None)
    stm.state = 0
    for _ in range(100):
        app2.update()
        import compat
        compat.sleep_ms(5)
    assert stm.executed.count("SET_POSE") == 1
