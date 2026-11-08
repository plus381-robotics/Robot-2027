# Veza i podešavanja (pregled logike L17, L23, L27).
import compat
from conftest import run


def write(app, name, src):
    (app.tactics_dir / (name + ".py")).write_text("from tac import *\n" + src)


def test_pad_veze_usred_komande_odmah_false(app, stm):
    """L17: veza pukne tokom vožnje: korak posle ~300 ms vraća False "VEZA" (ne čeka timeout, ne pogađa)."""
    from runner import run_tactic
    write(app, "t", "log('rez %s' % move(500, timeout=8))\n")
    stm.motion_ms = 5000
    run(app, 300)
    t_off = compat.ticks_ms() + 400
    orig = app.loop.services[0][1]

    def svc():
        if compat.ticks_ms() >= t_off:
            stm.on = False
        orig()
    app.loop.services[0] = ("robot", svc)
    t0 = compat.ticks_ms()
    run_tactic(app, "t")
    assert "rez False" in app.log and any("nema veze sa STM32" in l for l in app.log)
    assert compat.ticks_ms() - t0 < 2000
    assert app.report["steps_list"][-1][3] == "VEZA"


def test_u_mecu_ceka_povratak_veze_i_nastavlja(app, stm):
    """L17: u meču sledeća komanda čeka povratak veze (labav konektor) i taktika nastavlja."""
    from runner import run_tactic
    write(app, "m", "START = (250, 1000, 0)\nwait(0.5)\nlog('a %s' % move(100))\nlog('b %s' % move(100))\n")
    run(app, 300)
    assert app.match.arm("m", "zuta")
    run(app, 100)
    app.match.simulate_cord()
    while not app.request:
        app.pump()
    name, app.request = app.request, None
    t0 = compat.ticks_ms()
    orig = app.loop.services[0][1]

    def svc():                                                # veza nema od 0.2 s do 4 s
        dt = compat.ticks_ms() - t0
        stm.on = not (200 <= dt < 4000)
        orig()
    app.loop.services[0] = ("robot", svc)
    run_tactic(app, name)
    # prva komanda je otišla u prekinutu vezu (False), druga sačeka povratak veze i uspe; taktika nije prekinuta
    assert "a False" in app.log and "b True" in app.log
    assert any("cekam" in l for l in app.log) and any("nastavljam" in l for l in app.log)
    assert app.report["how"] is None


def test_provera_vidi_pogresno_ime_aktuatora(app):
    """L23: pogrešno ime aktuatora je crveno u PROVERA, ne pada tek u meču."""
    write(app, "t", "START = (250, 1000, 0)\nactuator('hvatljka', 1)\n")
    app.select("t", "zuta")
    assert app.tactic_ok() == (False, "akt. hvatljka")
    write(app, "u", "START = (250, 1000, 0)\nactuator('hvataljka', 1)\nactuator( \"ruka_l\", 0)\n")
    app.select("u", "zuta")
    assert app.tactic_ok() == (True, "")


def test_auto_poza_posle_restarta_stm32_i_ogledana(app, stm):
    """L27 + PROBLEMI 5: auto poza pri svakom povezivanju STM32, ogledana po izabranoj strani."""
    app.side = "plava"
    stm.sent.clear()
    stm.on = False
    run(app, 800)                                             # pad veze (STM32 restart / flešovanje)
    stm.on = True
    run(app, 500)
    poses = [d for n, d in stm.sent if n == "SET_POSE"]
    assert poses and poses[-1] == {"x": 2750, "y": 1000, "theta": 18000}
