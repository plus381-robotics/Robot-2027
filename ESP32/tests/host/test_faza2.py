import compat
import protocol as P
import tac
from conftest import run


def write(app, name, src):
    (app.tactics_dir / (name + ".py")).write_text(src)


def last(stm, name):
    return [d for n, d in stm.sent if n == name][-1]


def test_strana_ogleda_koordinate(app, stm):
    """K-3: taktika pisana za žutu (REF_SIDE); na plavoj x -> 3000 - x, ugao -> 180 - ugao."""
    from runner import run_tactic
    write(app, "t", "from tac import *\npose(250, 1000, 0)\ngoto(600, 800, deg=90)\nturn_to(30)\n")
    run(app, 300)
    app.side = "plava"
    run_tactic(app, "t")
    assert last(stm, "SET_POSE") == {"x": 2750, "y": 1000, "theta": 18000}
    g = last(stm, "GOTO")
    assert (g["x"], g["y"], g["theta"]) == (2400, 800, 9000)
    assert last(stm, "ROTATE")["theta"] == 15000


def test_relativni_okret_menja_smer_na_drugoj_strani(app, stm):
    from runner import run_tactic
    write(app, "t", "from tac import *\npose(250, 1000, 0)\nwait(0.2)\nturn_by(45)\n")
    run(app, 300)
    app.side = "plava"
    run_tactic(app, "t")
    assert last(stm, "ROTATE")["theta"] == 13500     # 180 - 45: na terenu udesno


def test_kraj_kretanja_bez_done(app, stm):
    """P-2: DONE izgubljen; kraj se zaključi iz STATUS-a (MOVING pa 3 puta bez MOVING)."""
    from runner import run_tactic
    write(app, "t", "from tac import *\nok = move(200)\nlog('rez %s' % ok)\n")
    run(app, 300)
    stm.drop_done = 1
    t0 = compat.ticks_ms()
    run_tactic(app, "t")
    assert "rez True" in app.log and any("DONE nije stigao" in l for l in app.log)
    assert compat.ticks_ms() - t0 < 2000                 # ne čeka ceo timeout


def test_timeout_iz_duzine_puta(app, stm):
    from runner import run_tactic
    write(app, "t", "from tac import *\npose(0, 0)\nwait(0.2)\nok = goto(3000, 0, speed=300)\nlog('rez %s' % ok)\n")
    run(app, 300)
    stm.motion_ms = 12000                                # duže od starih 10 s, kraće od procene
    run_tactic(app, "t")
    assert "rez True" in app.log


def test_tok_meca_sa_simuliranim_cincem(app, stm):
    """K-4: naoružaj -> činč -> SET_POSE startne poze izabrane strane -> taktika."""
    import machine
    write(app, "m", "from tac import *\nSTART = (250, 1000, 0)\nTOTAL = 1\nmove(100)\n")
    run(app, 300)
    assert app.match.arm("m", "plava")
    run(app, 300)
    assert app.match.state == "NAORUZAN" and app.busy()
    n0 = len(stm.sent)
    app.match.simulate_cord()
    for _ in range(200):
        app.pump()
        if app.request:
            from runner import run_tactic
            name, app.request = app.request, None
            run_tactic(app, name)
            break
    names = [n for n, _ in stm.sent[n0:]]
    assert names[:3] == ["MATCH_START", "SET_POSE", "MOVE"]
    assert stm.sent[n0 + 1][1] == {"x": 2750, "y": 1000, "theta": 18000}
    assert machine.WDT.fed > 0                           # watchdog radi od NAORUZAN
    run(app, 100)
    assert app.match.state == "KRAJ"


def test_stop_otkazuje_naoruzan_mec(app):
    (app.tactics_dir / "m.py").write_text("from tac import *\n")
    app.match.arm("m", "plava")
    app.stop()
    assert app.match.state == "NEMA" and not app.busy()


def test_aktuator_ceka_done(app, stm):
    """K-6: ACTUATOR -> ACK -> (posle act_ms) DONE."""
    from runner import run_tactic
    write(app, "t", "from tac import *\nok = actuator('hvataljka', 1)\nlog('rez %s' % ok)\n")
    run(app, 300)
    run_tactic(app, "t")
    assert "rez True" in app.log and last(stm, "ACTUATOR") == {"id": 1, "value": 1}


def test_aktuator_odbijen_kao_na_blackpillu(app, stm):
    from runner import run_tactic
    write(app, "t", "from tac import *\nok = actuator('lift', 5)\nlog('rez %s' % ok)\n")
    run(app, 300)
    stm.act_fail = P.Reason.INVALID
    run_tactic(app, "t")
    assert "rez False" in app.log


def test_aktuator_paralelno_sa_voznjom_i_ogledanje(app, stm):
    from runner import run_tactic
    write(app, "t", "from tac import *\nh = actuator('ruka_l', 7, wait=False)\n"
                    "move(100)\nlog('rez %s %s' % (done(h), wait_done(h)))\n")
    run(app, 300)
    app.side = "plava"
    run_tactic(app, "t")
    assert last(stm, "ACTUATOR") == {"id": 4, "value": 7}       # na plavoj (druga strana) ruka_l -> ruka_r
    assert [n for n, _ in stm.sent[-2:]] == ["ACTUATOR", "MOVE"]
    assert "rez True True" in app.log


def test_except_exception_ne_guta_stop(app, stm):
    """K-5: taktika sa try/except Exception ipak staje na STOP."""
    from runner import run_tactic
    write(app, "t", "from tac import *\nn = 0\nwhile True:\n    try:\n        wait(0.1)\n"
                    "        n += 1\n        if n == 3:\n            import tac\n            tac.app.stop()\n"
                    "    except Exception:\n        pass\n")
    run(app, 300)
    run_tactic(app, "t")
    assert app.running is None and any(l.startswith("PREKID") for l in app.log)
