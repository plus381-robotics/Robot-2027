# Protokol v5: IR senzori F1..F4 (napred) i B1..B4 (nazad); taktika ih pali i gasi (ir_off/ir_on), čita (ir_sees).
import protocol as P
from conftest import run


def _run(app, src, side="zuta"):
    from runner import run_tactic
    (app.tactics_dir / "t.py").write_text("from gambit import *\n" + src)
    run(app, 300)
    app.side = side
    run_tactic(app, "t")


def masks(stm):
    return [d["mask"] for n, d in stm.sent if n == "IR_MASK"]


def test_ir_off_on_i_na_kraju_svi_ukljuceni(app, stm):
    _run(app, "ir_off('F')\nir_on('F2')\nir_off('B1', 'B4')\nir_on()\nir_off('B')\n")
    F, B = 0x0F, 0xF0
    assert masks(stm) == [0xFF & ~F, 0xFF & ~F | P.Ir.F2, (0xFF & ~F | P.Ir.F2) & ~(P.Ir.B1 | P.Ir.B4), 0xFF,
                          0xFF & ~B, 0xFF]                                    # poslednja: kraj taktike, svi
    assert stm.ir_mask == 0xFF and any("IR iskljuceni: B1 B2 B3 B4" in l for l in app.log)


def test_plava_strana_levo_desno_zamenjeno(app, stm):
    from runner import run_tactic
    (app.tactics_dir / "t.py").write_text("from gambit import *\nir_off('F1')\nlog('vidi %s' % ir_sees('F4'))\n")
    run(app, 300)
    stm.ir_raw = P.Ir.F1                                                      # na terenu vidi F1 (levi)
    run(app, 100)
    app.side = "plava"
    run_tactic(app, "t")
    assert masks(stm)[0] == 0xFF & ~P.Ir.F4                                  # žuti F1 = plavi F4
    assert "vidi True" in app.log                                             # ir_sees('F4') na plavoj = F1


def test_stop_ukljucuje_sve_pre_stopa(app, stm):
    run(app, 300)                                                             # veza: STM32 v5
    app.ir_want = 0xF0
    app.stop("test")
    names = [n for n, _ in stm.sent]
    assert names[-2:] == ["IR_MASK", "STOP"]                                 # STOP je poslednji (on se ponavlja)
    assert app.ir_want == 0xFF


def test_stari_stm32_bez_ir_maske(app, stm):
    stm.version = 4
    _run(app, "log('ok %s' % ir_off('F'))\n")
    assert masks(stm) == [] and "ok False" in app.log and any("ne zna za IR" in l for l in app.log)
