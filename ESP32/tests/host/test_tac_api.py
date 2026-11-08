# tac API (pregled logike L10, L11, L12, L15, L18-L20) i obnova posle restarta ESP-a u meču.
import protocol as P
from conftest import run


def write(app, name, src):
    (app.tactics_dir / (name + ".py")).write_text("from tac import *\n" + src)


def sent(stm, name):
    return [d for n, d in stm.sent if n == name]


def test_test_postavlja_start_pozu(app, stm):
    """L10: test kreće od START poze (ogledane po strani), kao meč."""
    from runner import run_tactic
    write(app, "t", "START = (300, 900, 90)\nlog('ok')\n")
    run(app, 300)
    app.side = "plava"
    run_tactic(app, "t")
    assert sent(stm, "SET_POSE")[-1] == {"x": 2700, "y": 900, "theta": 9000}
    app.st["test_start"] = False
    stm.sent.clear()
    run_tactic(app, "t")
    assert sent(stm, "SET_POSE") == []


def test_vreme_u_testu_i_faza_napada(app, stm):
    """L11, L12: u testu vreme teče od starta taktike; attack_phase od 85. s."""
    from runner import run_tactic
    write(app, "t", "log('pre %s %s %d' % (in_match(), attack_phase(), remaining()))\nwait(86)\n"
                    "log('posle %s %d' % (attack_phase(), remaining()))\n")
    run(app, 300)
    run_tactic(app, "t")
    assert "pre False False 100" in app.log
    assert any(l.startswith("posle True 1") for l in app.log)


def test_deadline_prekida_i_vozi_kuci(app, stm):
    """L12: deadline(s) zaustavi tekuću komandu i baci TimeUp; taktika ga hvata i ide kući."""
    from runner import run_tactic
    write(app, "t", "deadline(97)\ntry:\n    move(1000, speed=150)\n    log('ne sme')\n"
                    "except TimeUp as e:\n    log('vreme: %s' % e)\n    go_home()\n")
    stm.motion_ms = 10000
    run(app, 300)
    run_tactic(app, "t")
    assert "ne sme" not in app.log and any(l.startswith("vreme: ostalo") for l in app.log)
    names = [n for n, _ in stm.sent]
    assert "STOP" in names and "GOTO" in names[names.index("STOP"):]    # stao, pa vožnja kući
    g = sent(stm, "GOTO")[-1]
    assert (g["x"], g["y"]) == (250, 1000)                       # HOME žute (REF_SIDE)


def test_argumenti_ugao_tip_brzina(app, stm):
    """L18, L20: ugao svođenje, float -> int, brzina ograničena, 0 je greška."""
    from runner import run_tactic
    write(app, "t", "goto(600, 1000, deg=400, speed=3000)\nmove(150.4, speed=0.5 * 600)\n")
    run(app, 300)
    run_tactic(app, "t")
    g = sent(stm, "GOTO")[-1]
    assert g["theta"] == 4000 and g["max_speed"] == 1500
    m = sent(stm, "MOVE")[-1]
    assert m == {"dist": 150, "max_speed": 300, "flags": None}          # bez near: MOVE kao u v4
    write(app, "z", "move(100, speed=0)\n")
    run_tactic(app, "z")
    assert any("ValueError" in t for _, t in app.errors)


def test_turn_by_veliki_ugao_u_vise_okreta(app, stm):
    """L19: turn_by(270) ide u zadatom smeru (2 okreta), ne -90."""
    from runner import run_tactic
    write(app, "t", "turn_by(270)\n")
    run(app, 300)
    run_tactic(app, "t")
    assert [d["theta"] for d in sent(stm, "ROTATE")] == [13500, -9000]


def test_aktuator_bez_cekanja_ponovi_izgubljen_okvir(app, stm):
    """L15: actuator(wait=False) sačeka ACK pre sledeće komande, pa se izgubljen okvir ponovi."""
    from runner import run_tactic
    write(app, "t", "h = actuator('lift', 300, wait=False)\ngoto(700, 1000)\nlog('lift %s' % wait_done(h))\n")
    run(app, 300)
    stm.drop = 1
    run_tactic(app, "t")
    assert "ACTUATOR" in stm.executed and "lift True" in app.log


def test_restart_esp_u_mecu_pokrece_obnovu(app, stm):
    import compat
    write(app, "m", "START = (250, 1000, 0)\n")
    write(app, "m_obnova", "log('obnova %d' % remaining())\ngo_home()\n")
    app.select("m", "zuta")
    stm.state |= P.State.MATCH_RUNNING
    stm.match0 = compat.ticks_ms() - 40000                       # meč traje 40 s kad se ESP podigne
    run(app, 300)
    assert app.request == "m_obnova" and app.match.state == "MEC"
    from runner import run_tactic
    name, app.request = app.request, None
    run_tactic(app, name)
    assert any(l.startswith("obnova 59") for l in app.log)


def test_restart_esp_u_mecu_bez_obnove_stoji(app, stm):
    import compat
    write(app, "m", "START = (250, 1000, 0)\n")
    app.select("m", "zuta")
    stm.state |= P.State.MATCH_RUNNING
    stm.match0 = compat.ticks_ms() - 40000
    run(app, 300)
    assert app.request is None and app.ui.alarmed
