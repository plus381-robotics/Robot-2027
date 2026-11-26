# Buzzer (lib/buzzer.py): raspored tonova bez blokiranja, podešavanje "zvuk", tišina u meču, prioritet.
import buzzer
import compat
from machine import PWM
from conftest import run

PIN = 13


def make(app):
    b = buzzer.Buzzer(app, PIN, 2700)
    app.buzzer = b
    app.loop.services.append(("zvuk", b.tick))
    return b


def trace(app, ms, step=5):
    """Stanje PWM-a (1 = svira) svakih step ms."""
    out = []
    for _ in range(ms // step):
        app.pump()
        out.append(1 if PWM.pins[PIN].duty_u16() else 0)
    return out


def runs(seq):
    """[1,1,0,0,1] -> [(1, 2), (0, 2), (1, 1)]"""
    out = []
    for v in seq:
        if out and out[-1][0] == v:
            out[-1][1] += 1
        else:
            out.append([v, 1])
    return [tuple(x) for x in out]


def test_greska_tri_tona_i_ugasi_se(app):
    b = make(app)
    assert b.play("greska")
    r = runs(trace(app, 1000))
    tones = [n for v, n in r if v == 1]
    assert len(tones) == 3                                  # tri kratka
    assert r[-1][0] == 0 and b.kind is None                 # na kraju tišina
    assert PWM.pins[PIN].freq() == 2700


def test_ok_jedan_kratak_ne_blokira_petlju(app):
    b = make(app)
    t0 = compat.ticks_ms()
    app.beep("ok")
    assert compat.ticks_ms() == t0                          # play() ne čeka
    assert b.sounding
    run(app, 200)
    assert not b.sounding


def test_podesavanje_zvuk():
    a = buzzer.allowed
    assert not a("greska", buzzer.OFF, False)
    assert a("greska", buzzer.ERRORS, False) and a("baterija", buzzer.ERRORS, False)
    assert not a("ok", buzzer.ERRORS, False) and not a("upoz", buzzer.ERRORS, False)
    assert a("ok", buzzer.ALL, False)
    assert a("greska", buzzer.ALL, True) and not a("ok", buzzer.ALL, True) and not a("upoz", buzzer.ALL, True)


def test_iskljucen_ali_test_iz_menija_svira(app):
    b = make(app)
    app.st["sound"] = 0
    app.beep("greska")
    assert not b.sounding
    app.beep("upoz", force=True)                            # Meni -> test zvuka
    assert b.sounding


def test_vazniji_zvuk_prekida_manje_vazan_obrnuto_ne(app):
    b = make(app)
    app.beep("ok")
    app.beep("greska")
    assert b.kind == "greska"
    app.beep("ok")
    assert b.kind == "greska"


def test_u_mecu_samo_greska(app, stm):
    b = make(app)
    (app.tactics_dir / "m.py").write_text("from tac import *\nSTART = (250, 1000, 0)\nmove(100)\n")
    run(app, 300)
    app.match.state = "MEC"
    app.error("nesto")                                      # van meča bi bilo "upoz"
    assert not b.sounding
    app.ui.alarm("VEZA", "STM32 ne odgovara")
    assert b.kind == "greska"


def test_alarm_i_naoruzavanje_zvuce(app, stm):
    b = make(app)
    app.stop()                                              # STOP preko celog ekrana
    assert b.played[-1] == "greska"
    run(app, 1000)
    app.ui.input("ok")
    (app.tactics_dir / "m.py").write_text("from tac import *\nSTART = (250, 1000, 0)\nmove(100)\n")
    app.select("m", "zuta")
    run(app, 300)
    app.arm()
    assert app.match.armed and b.played[-1] == "ok"


def test_bez_buzzera_beep_ne_radi_nista(app):
    assert app.buzzer is None
    app.beep("greska")                                      # WROOM-32 nema buzzer: bez greške
