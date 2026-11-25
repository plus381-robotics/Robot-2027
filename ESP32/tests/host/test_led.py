# RGB LED (lib/led.py): boja po stanju robota, svetlina iz podešavanja, upis samo na promenu.
import protocol as P
import led
from conftest import run


def make(app):
    import config
    return led.Led(app, getattr(config, "NEOPIXEL", None) or 38)


def test_provera_ne_prolazi_crveno_pa_zeleno_kad_prolazi(app, stm, tmp_path):
    app.st["led"] = 255
    l = make(app)
    run(app, 300)
    assert l.color() == led.RED                         # nije izabrana taktika ni strana
    (app.tactics_dir / "m.py").write_text("from tac import *\nSTART = (250, 1000, 0)\nmove(100)\n")
    app.st["sel_tactic"], app.st["sel_side"] = "m", "zuta"
    run(app, 1100)                                      # PROVERA se kešira do 1 s
    assert l.color() == led.GREEN


def test_naoruzan_zuto_i_svetlina(app, stm):
    (app.tactics_dir / "m.py").write_text("from tac import *\nSTART = (250, 1000, 0)\nmove(100)\n")
    run(app, 300)
    assert app.match.arm("m", "zuta")
    run(app, 100)
    app.st["led"] = 255
    l = make(app)
    assert l.color() == led.YELLOW
    app.st["led"] = 0
    assert l.color() == (0, 0, 0)


def test_alarm_trepce_crveno(app, stm):
    app.st["led"] = 255
    l = make(app)
    app.ui.alarm("STOP", "taster STOP")
    on, off = l.color(now=0), l.color(now=led.BLINK_FAST)
    assert on == led.RED and off == (0, 0, 0)


def test_blokiran_u_testu_zuto_trepce(app, stm):
    app.st["led"] = 255
    run(app, 300)
    app.running = "m"
    stm.state |= P.State.BLOCKED
    run(app, 100)
    assert led.pick(app, lambda: True) == (led.YELLOW, led.BLINK_FAST)
    stm.state &= ~P.State.BLOCKED
    run(app, 100)
    assert led.pick(app, lambda: True) == (led.BLUE, led.BREATHE)


def test_upis_samo_na_promenu(app, stm):
    app.st["led"] = 255
    l = make(app)
    run(app, 300)
    for _ in range(20):
        l.tick()
    assert l.np.writes == 1


def test_disanje_ostaje_u_opsegu():
    vals = [led.level(led.BREATHE, t) for t in range(0, 4000, 37)]
    assert min(vals) >= 16 and max(vals) <= 255 and len(set(vals)) > 10
