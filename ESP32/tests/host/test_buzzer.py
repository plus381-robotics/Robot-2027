# Buzzer (lib/buzzer.py) i RTTTL (lib/rtttl.py): parser, raspored nota bez blokiranja, podešavanje "zvuk",
# pravila u meču, prioritet, zvuci na događaje (start, kraj, gotovo) i tac.play().
import pytest

import buzzer
import compat
import config
import rtttl
from machine import PWM
from conftest import run

PIN = 13


def make(app):
    b = buzzer.Buzzer(app, PIN)
    app.buzzer = b
    app.loop.services.append(("zvuk", b.tick))
    return b


def trace(app, ms, step=5):
    """Frekvencija koja svira (0 = tišina) svakih step ms."""
    out = []
    for _ in range(ms // step):
        app.pump()
        p = PWM.pins[PIN]
        out.append(p.freq() if p.duty_u16() else 0)
    return out


def runs(seq):
    """[a, a, 0, b] -> [(a, 2), (0, 1), (b, 1)]"""
    out = []
    for v in seq:
        if out and out[-1][0] == v:
            out[-1][1] += 1
        else:
            out.append([v, 1])
    return [tuple(x) for x in out]


# ---------------- RTTTL ----------------

def test_rtttl_note_trajanje_oktava_tacka():
    n = rtttl.parse("x:d=4,o=5,b=120:a,8c#6.,p,2a4,16h")
    whole = 240000 // 120                                  # 2000 ms
    assert n == [(880, whole // 4), (1109, whole // 8 * 3 // 2), (0, whole // 4), (440, whole // 2), (988, whole // 16)]


def test_rtttl_bez_imena_i_podesavanja():
    assert rtttl.parse("c,e") == [(1047, 240000 // 63 // 4), (1319, 240000 // 63 // 4)]   # d=4, o=6, b=63
    assert rtttl.parse(":b=100:4c7") == [(2093, 600)]


def test_rtttl_tacka_posle_oktave_i_razmaci():
    assert rtttl.parse("x:d=8,o=6,b=100: e7. , 16p ") == [(2637, 450), (0, 150)]     # cela nota 2400 ms


@pytest.mark.parametrize("bad", ["", "x:d=4:", "x:d=3:c", "x:d=4,o=6,b=63:z", "x:q=1:c", "x:d=4:c9",
                                 "x:d=4:64c", "a:b:c:d", "x:d=a:c", "x:d=4:c$"])
def test_rtttl_los_tekst(bad):
    with pytest.raises(ValueError):
        rtttl.parse(bad)


def test_check_ime_ili_rtttl():
    rtttl.check("kraj", {"kraj"})
    rtttl.check("ja:d=8:c,e", {"kraj"})
    with pytest.raises(ValueError, match="nema zvuka"):
        rtttl.check("krajj", {"kraj"})


def test_svi_zvuci_se_parsiraju():
    for name, text in list(buzzer.DEFAULT_SOUNDS.items()) + list(config.SOUNDS.items()):
        assert rtttl.parse(text), name
    assert set(buzzer.MENU) <= set(buzzer.sounds())


def test_tonovi_imaju_pauzu_izmedju_nota():
    t = list(buzzer.tones([(1000, 100), (1000, 100), (0, 50), (2000, 10)]))
    assert t == [(1000, 88), (0, 12), (1000, 88), (0, 12), (0, 50), (2000, 10)]


# ---------------- puštanje ----------------

def test_melodija_svira_prave_note_i_ugasi_se(app):
    b = make(app)
    assert b.play("boot")                                  # c, e, g, 8c7 (o=6)
    r = runs(trace(app, 1000))
    assert [hz for hz, n in r if hz] == [1047, 1319, 1568, 2093]
    assert r[-1][0] == 0 and b.kind is None


def test_greska_tri_tona(app):
    b = make(app)
    assert b.play("greska")
    tones = [hz for hz, n in runs(trace(app, 1000)) if hz]
    assert tones == [2349] * 3                             # D7, blizu rezonancije buzzera (2,4 kHz)


def test_ok_ne_blokira_petlju(app):
    b = make(app)
    t0 = compat.ticks_ms()
    app.beep("ok")
    assert compat.ticks_ms() == t0                          # play() ne čeka
    assert b.sounding
    run(app, 200)
    assert not b.sounding


def test_zastoj_petlje_ne_pomera_ritam(app):
    """Petlja zastane 300 ms: note koje su prošle se preskaču, kraj melodije je na vreme."""
    b = make(app)
    b.play("start")
    total = sum(ms for _, ms in b.notes)
    compat.sleep_ms(300)
    b.tick()
    assert b.kind == "start"
    compat.sleep_ms(total - 300)
    b.tick()
    assert b.kind is None and not b.sounding


def test_podesavanje_zvuk():
    a = buzzer.allowed
    assert not a("greska", buzzer.OFF, False)
    assert a("greska", buzzer.ERRORS, False) and a("baterija", buzzer.ERRORS, False)
    assert not a("ok", buzzer.ERRORS, False) and not a("start", buzzer.ERRORS, False)
    assert a("ok", buzzer.ALL, False) and a("boot", buzzer.ALL, False)
    for k in ("greska", "start", "kraj", "takt"):              # u meču
        assert a(k, buzzer.ALL, True), k
    for k in ("ok", "upoz", "gotovo", "boot", "baterija"):
        assert not a(k, buzzer.ALL, True), k


def test_iskljucen_ali_test_iz_menija_svira(app):
    b = make(app)
    app.st["sound"] = 0
    app.beep("greska")
    assert not b.sounding
    app.beep("upoz", force=True)                            # Meni -> test zvuka
    assert b.sounding


def test_vazniji_zvuk_prekida_manje_vazan_obrnuto_ne(app):
    b = make(app)
    app.beep("gotovo")
    app.beep("greska")
    assert b.kind == "greska"
    app.beep("ok")
    assert b.kind == "greska"


def test_los_zvuk_u_configu_ne_rusi(app, monkeypatch):
    b = make(app)
    b.sounds = dict(b.sounds, ok="ok:d=4:zz")
    assert not app.beep("ok")                               # samo poruka u konzoli
    assert not b.sounding


def test_meni_test_zvuka_ima_sve_zvuke(app):
    make(app)
    m = app.sound_menu()
    labels = [it.label for it in m.items]
    assert labels[:len(buzzer.MENU)] == list(buzzer.MENU)
    m.items[labels.index("kraj")].activate(app.ui, m)
    assert app.buzzer.kind == "kraj"


# ---------------- događaji ----------------

def test_u_mecu_samo_greska(app, stm):
    b = make(app)
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


def _match(app, stm, src):
    from runner import run_tactic
    (app.tactics_dir / "m.py").write_text(src)
    run(app, 300)
    assert app.match.arm("m", "zuta")
    run(app, 300)
    app.match.simulate_cord()
    for _ in range(200):
        app.pump()
        if app.request:
            name, app.request = app.request, None
            run_tactic(app, name)
            break


def test_cinc_start_pa_kraj_na_100_s(app, stm):
    b = make(app)
    _match(app, stm, "from tac import *\nSTART = (250, 1000, 0)\nmove(100)\n")
    assert "start" in b.played
    assert "gotovo" not in b.played                         # taktika gotova u meču: tišina do kraja
    run(app, 100500)
    assert b.played[-1] == "kraj" and b.played.count("kraj") == 1
    run(app, 2000)
    assert b.played.count("kraj") == 1                     # jednom po meču


def test_test_taktika_gotova_svira_gotovo(app, stm):
    from runner import run_tactic
    b = make(app)
    (app.tactics_dir / "t.py").write_text("from tac import *\nmove(100)\n")
    run(app, 300)
    run_tactic(app, "t")
    assert b.played[-1] == "gotovo"


def test_tac_play_ime_i_rtttl(app, stm):
    from runner import run_tactic
    b = make(app)
    (app.tactics_dir / "t.py").write_text("from tac import *\nlog('a %s' % play('kraj'))\n"
                                          "log('b %s' % play('ja:d=8,o=6,b=180:c,e,g'))\n")
    run(app, 300)
    run_tactic(app, "t")
    assert "a True" in app.log and "b True" in app.log
    assert b.played[:2] == ["takt", "takt"]


def test_tac_play_los_tekst_je_greska_taktike(app, stm):
    from runner import run_tactic
    make(app)
    (app.tactics_dir / "t.py").write_text("from tac import *\nplay('krajj')\n")
    run(app, 300)
    run_tactic(app, "t")
    assert app.report["how"] and "ValueError" in app.report["how"]


def test_bez_buzzera_beep_ne_radi_nista(app, stm):
    from runner import run_tactic
    assert app.buzzer is None
    app.beep("greska")                                      # WROOM-32 nema buzzer: bez greške
    (app.tactics_dir / "t.py").write_text("from tac import *\nlog('p %s' % play('kraj'))\n")
    run(app, 300)
    run_tactic(app, "t")
    assert "p False" in app.log


def test_duga_melodija_se_cita_nota_po_nota(app, monkeypatch):
    """Paganini (~430 nota): play() ne parsira ceo tekst unapred, note se čitaju dok svira."""
    calls = []
    real = rtttl.note
    monkeypatch.setattr(rtttl, "note", lambda *a: calls.append(1) or real(*a))
    b = make(app)
    assert b.play("paganini", force=True)
    assert len(calls) == 1                                 # samo prva nota
    run(app, 1000)
    assert 3 < len(calls) < 40 and b.kind == "paganini"
    b.stop()
    assert b.kind is None and not b.sounding


def test_losa_nota_u_sred_melodije_prekida(app):
    b = make(app)
    b.sounds = dict(b.sounds, ok="ok:d=16,o=7,b=200:d,e,zz,f")
    assert app.beep("ok")
    run(app, 500)
    assert b.kind is None and not b.sounding
