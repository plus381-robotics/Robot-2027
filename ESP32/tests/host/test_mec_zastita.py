# Zaštita toka meča (docs/esp-pregled-logike.md L1, L2, L7): nov činč, stari meč na STM32, restart STM32.
import protocol as P
from conftest import run


def write(app, name, src):
    (app.tactics_dir / (name + ".py")).write_text(src)


def odigraj_mec(app, stm):
    from runner import run_tactic
    write(app, "m", "from tac import *\nSTART = (250, 1000, 0)\nmove(100)\n")
    run(app, 300)
    assert app.match.arm("m", "zuta")
    run(app, 100)
    app.match.simulate_cord()
    for _ in range(200):
        app.pump()
        if app.request:
            name, app.request = app.request, None
            run_tactic(app, name)
            break
    run(app, 200)


def test_stari_mec_bez_nrst_odbija_naoruzavanje(app, stm):
    odigraj_mec(app, stm)
    assert stm.state & P.State.MATCH_RUNNING                    # STM32 i dalje broji (BlackPill ne briše)
    n = len(stm.sent)
    assert not app.match.arm("m", "zuta")
    assert any("restartuj STM32" in t for _, t in app.errors)
    run(app, 1000)
    assert [x for x, _ in stm.sent[n:]] == []                   # ništa se ne šalje: robot ne kreće
    ok, items = app.check()
    assert ("ne", "STM32 mec", "restartuj STM32") in items


def test_cinc_mora_biti_nov(app, stm):
    """Naoruzan bez STATUS-a, pa prvi STATUS već u meču: to nije nov činč (ranije: taktika krene odmah)."""
    write(app, "m", "from tac import *\nSTART = (250, 1000, 0)\nmove(100)\n")
    stm.state |= P.State.MATCH_RUNNING
    stm.match0 = 0
    stm.on = False                                              # ESP još nema STATUS
    assert app.match.arm("m", "zuta")
    stm.on = True
    run(app, 500)
    assert app.request is None and app.match.state == "NEMA"
    assert any("restartuj STM32" in t for _, t in app.errors)


def test_restart_stm32_u_mecu_vraca_pozu(app, stm):
    from runner import run_tactic
    write(app, "m", "from tac import *\nSTART = (250, 1000, 0)\nlog('rez %s' % move(300))\nmove(100)\n")
    stm.motion_ms = 2000
    run(app, 300)
    assert app.match.arm("m", "zuta")
    run(app, 100)
    app.match.simulate_cord()
    while not app.request:
        app.pump()
    name, app.request = app.request, None
    stm.pose = [600, 900, 4500]                                 # FakeSTM ne vozi: poza "tokom vožnje"
    import compat

    def restart():                                              # STM32 se restartuje: meč i komanda nestaju
        stm.state = 0
        stm.match0 = None
        stm.motion = None
        stm.pose = [0, 0, 0]
        stm.last_seq = None
    t_restart = compat.ticks_ms() + 400
    orig = app.loop.services[0][1]

    done = []

    def svc():
        if not done and compat.ticks_ms() >= t_restart:
            done.append(1)
            restart()
        orig()
    app.loop.services[0] = ("robot", svc)
    run_tactic(app, name)
    assert "rez False" in app.log                               # prekinut korak: RESTART
    poses = [d for n, d in stm.sent if n == "SET_POSE"]
    x, y, th = poses[-1]["x"], poses[-1]["y"], poses[-1]["theta"]
    assert th == 4500 and 600 <= x <= 610 and 900 <= y <= 910     # poslednja poza + 25 ms vožnje (v = 300)
    assert [n for n, _ in stm.sent].count("MATCH_START") >= 2   # simulirani činč + obnova
    assert app.match.stm_resets == 1
