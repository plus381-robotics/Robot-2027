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


def test_posle_kraja_taktike_mec_ostaje_zakljucan_do_100s(app, stm):
    """L8: taktika završena pre 100 s: meni, test, upload i naoružavanje zaključani dok meč traje."""
    odigraj_mec(app, stm)
    assert app.match.state == "KRAJ" and app.match.armed and app.busy()
    assert not app.match.arm("m", "zuta")
    run(app, 100500)
    assert not app.match.armed


def test_stari_mec_bez_nrst_odbija_naoruzavanje(app, stm):
    stm.version = 3                                              # stari STM32: nema komande RESET
    odigraj_mec(app, stm)
    app.stop()                                                   # STOP: meč namerno prekinut
    assert stm.state & P.State.MATCH_RUNNING                    # STM32 i dalje broji (BlackPill ne briše)
    n = len(stm.sent)
    assert not app.match.arm("m", "zuta")
    assert any("restartuj STM32" in t for _, t in app.errors)
    run(app, 1000)
    assert [x for x, _ in stm.sent[n:]] == []                   # ništa se ne šalje: robot ne kreće
    ok, items = app.check()
    assert ("ne", "STM32 mec", "restartuj STM32") in items


def test_stari_mec_v4_reset_komandom_pa_nov_cinc(app, stm):
    """Protokol v4: STM32 u starom meču se restartuje komandom RESET (bez NRST pina), pa se čeka nov činč."""
    odigraj_mec(app, stm)
    app.stop()
    assert stm.state & P.State.MATCH_RUNNING
    n = len(stm.sent)
    assert app.match.arm("m", "zuta")
    assert [x for x, _ in stm.sent[n:]] == ["RESET"]
    run(app, 500)
    assert app.match.state == "NAORUZAN" and not app.errors
    assert any("komanda RESET" in l for l in app.log) and any("restartovan (softver)" in l for l in app.log)
    assert not (stm.state & P.State.MATCH_RUNNING)              # STM32 krenuo ispočetka
    assert app.request is None                                  # robot čeka nov činč


def test_cinc_mora_biti_nov(app, stm):
    """Naoruzan bez STATUS-a, pa prvi STATUS već u meču: to nije nov činč (ranije: taktika krene odmah)."""
    stm.version = 3
    write(app, "m", "from tac import *\nSTART = (250, 1000, 0)\nmove(100)\n")
    stm.state |= P.State.MATCH_RUNNING
    stm.match0 = 0
    stm.on = False                                              # ESP još nema STATUS
    assert app.match.arm("m", "zuta")
    stm.on = True
    run(app, 500)
    assert app.request is None and app.match.state == "NEMA"
    assert any("restartuj STM32" in t for _, t in app.errors)


def _restart_u_mecu(app, stm, restart):
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
    assert app.match.stm_resets == 1


def test_restart_stm32_u_mecu_vraca_pozu(app, stm):
    """Stari STM32 (v3): restart se vidi po STATUS-u bez meča; obnova SET_POSE pa MATCH_START."""
    stm.version = 3

    def restart():                                              # STM32 se restartuje: meč i komanda nestaju
        stm.state = 0
        stm.match0 = None
        stm.motion = None
        stm.pose = [0, 0, 0]
        stm.last_seq = None
    _restart_u_mecu(app, stm, restart)
    poses = [d for n, d in stm.sent if n == "SET_POSE"]
    x, y, th = poses[-1]["x"], poses[-1]["y"], poses[-1]["theta"]
    assert th == 4500 and 600 <= x <= 610 and 900 <= y <= 910     # poslednja poza + 25 ms vožnje (v = 300)
    assert [n for n, _ in stm.sent].count("MATCH_START") >= 2   # simulirani činč + obnova


def test_restart_stm32_u_mecu_v4_resume(app, stm):
    """v4: restart se vidi po uptime-u; obnova jednom porukom RESUME, STM32 nastavlja sat meča."""
    _restart_u_mecu(app, stm, lambda: stm.reboot())
    res = [d for n, d in stm.sent if n == "RESUME"]
    assert len(res) == 1
    assert res[0]["theta"] == 4500 and 600 <= res[0]["x"] <= 610 and 900 <= res[0]["y"] <= 910
    assert 300 <= res[0]["elapsed_ms"] <= 1000                    # meč traje od činča, ne od obnove
    assert [n for n, _ in stm.sent].count("MATCH_START") == 1   # samo simulirani činč
    assert any("restartovan (watchdog)" in l for l in app.log)


def test_start_dva_broja_i_slicna_imena(app, stm):
    """L3: START bez ugla radi (ugao 0); START_ZONA/TOTAL_MS se ne mešaju; nečitljiv START je crven."""
    import match
    write(app, "a", "from tac import *\nSTART = (250, 1000)\nSTART_ZONA = (0, 500)\nTOTAL = 2\nTOTAL_MS = 9\n")
    assert match.read_meta("a") == {"START": [250.0, 1000.0, 0.0], "TOTAL": 2}
    write(app, "b", "from tac import *\nSTART = (X0, 1000)\n")
    assert match.read_meta("b")["greska"] == "START necitljiv"
    app.select("b", "zuta")
    ok, items = app.check()
    assert not ok and ("ne", "taktika", "START necitljiv") in items
    assert not app.match.arm("b", "zuta")
    run(app, 300)
    assert app.match.arm("a", "zuta")
    run(app, 100)
    app.match.simulate_cord()
    for _ in range(100):
        app.pump()
        if app.request:
            break
    assert app.request == "a"                                    # ranije: ValueError u svakoj petlji
    assert [d for n, d in stm.sent if n == "SET_POSE"][-1] == {"x": 250, "y": 1000, "theta": 0}


def test_provera_vidi_novu_verziju_fajla(app, stm):
    """L5: posle izmene fajla (PUT/esp_push) PROVERA prevodi ponovo."""
    import compat
    import os
    write(app, "t", "from tac import *\nSTART = (250, 1000, 0)\n")
    app.select("t", "zuta")
    assert app.tactic_ok() == (True, "")
    write(app, "t", "from tac import *\nif True\n")
    p = str(app.tactics_dir / "t.py")
    os.utime(p, (1, 2))                                          # druga vremena izmene
    compat.fake[0] += 1500
    assert app.tactic_ok() == (False, "SyntaxError")


def test_cinc_bez_naoruzavanja_alarm(app, stm):
    """L4: meč otkazan (ili nije naoružan), a činč izvučen: robot stoji, ali to se vidi."""
    run(app, 300)
    app.robot.send("MATCH_START")
    run(app, 300)
    assert app.ui.alarmed and any("cinc bez naoruzavanja" in t for _, t in app.errors)
    assert app.request is None


def test_kraj_meca_nije_prekid(app, stm):
    """L9: taktika koja radi do 100 s: izveštaj MEC GOTOV, bez alarma i grešaka."""
    from runner import run_tactic
    write(app, "m", "from tac import *\nSTART = (250, 1000, 0)\nwhile True:\n    move(100)\n    move(-100)\n")
    stm.motion_ms = 2000
    run(app, 300)
    assert app.match.arm("m", "zuta")
    run(app, 100)
    app.match.simulate_cord()
    while not app.request:
        app.pump()
    name, app.request = app.request, None
    run_tactic(app, name)
    rp = app.report
    assert rp["ok"] and rp["match_end"] and rp["how"] is None
    assert not app.ui.alarmed and app.unseen == 0


def _do_cinca(app, stm):
    write(app, "m", "from tac import *\nSTART = (250, 1000, 0)\nwait(0.2)\n")
    run(app, 300)
    assert app.match.arm("m", "zuta")
    run(app, 100)
    n0 = len(stm.sent)
    app.match.simulate_cord()
    while not app.request:
        app.pump()
    return n0


def test_odbijena_start_poza_stop_pa_ponovo(app, stm):
    """L14: STM32 odbije SET_POSE na činč (npr. još "vozi"): STOP pa ponovo; ovde drugi put uspe."""
    stm.motion = (99, 10 ** 9)
    n0 = _do_cinca(app, stm)
    names = [n for n, _ in stm.sent[n0:]]
    assert names[:4] == ["MATCH_START", "SET_POSE", "STOP", "SET_POSE"]
    assert not any("START poza" in t for _, t in app.errors)


def test_stalno_odbijena_start_poza_3_puta_pa_greska_ostaje(app, stm):
    from runner import run_tactic
    frame = stm._frame

    def odbij(t, seq, pl):                                       # STM32 uvek odbija SET_POSE
        name, d = P.decode(t, pl)
        if name == "SET_POSE" and seq != stm.last_seq:
            stm.last_seq = seq
            stm.sent.append((name, d))
            stm._send("FAIL", seq, reason=P.Reason.INVALID)
            return
        frame(t, seq, pl)
    stm._frame = odbij
    n0 = _do_cinca(app, stm)
    assert [n for n, _ in stm.sent[n0:]].count("SET_POSE") == 3
    name, app.request = app.request, None
    run_tactic(app, name)
    assert any("START poza nije postavljena" in t for _, t in app.errors)   # ne briše se na start taktike
