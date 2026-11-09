# Protokol v5: IR senzori u uglovima, donji D i gornji U (FLD FLU FRD FRU BLD BLU BRD BRU); taktika ih pali i gasi (ir_off/ir_on), čita (ir_sees).
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
    _run(app, "ir_off('F')\nir_on('FLU')\nir_off('BLD', 'brd')\nir_on()\nir_off('D')\nir_off('BU')\n")
    F = P.Ir.FLD | P.Ir.FLU | P.Ir.FRD | P.Ir.FRU
    D = P.Ir.FLD | P.Ir.FRD | P.Ir.BLD | P.Ir.BRD
    m2 = 0xFF & ~F | P.Ir.FLU
    assert masks(stm) == [0xFF & ~F, m2, m2 & ~(P.Ir.BLD | P.Ir.BRD), 0xFF,
                          0xFF & ~D, 0xFF & ~D & ~(P.Ir.BLU | P.Ir.BRU), 0xFF]   # poslednja: kraj taktike, svi
    assert stm.ir_mask == 0xFF and any("IR iskljuceni: FLD FRD BLD BRD" in l for l in app.log)


def test_nepoznat_senzor(app, stm):
    _run(app, "ir_off('F1')\n")
    assert any("nepoznat IR senzor F1" in l for l in app.log)


def test_mala_slova_i_grupa_bez_senzora(app, stm):
    _run(app, "ir_off('f')\nir_off('fb')\nlog('posle')\n")
    assert masks(stm)[0] == 0xF0                                              # 'f' = sva 4 prednja
    assert any("IR grupa FB ne pogadja nijedan senzor" in l for l in app.log) and "posle" not in app.log


def test_plava_strana_levo_desno_zamenjeno(app, stm):
    from runner import run_tactic
    (app.tactics_dir / "t.py").write_text("from gambit import *\nir_off('FL')\nlog('vidi %s' % ir_sees('FRU'))\n")
    run(app, 300)
    stm.ir_raw = P.Ir.FLU                                                     # na terenu vidi FLU (levi gornji)
    run(app, 100)
    app.side = "plava"
    run_tactic(app, "t")
    assert masks(stm)[0] == 0xFF & ~(P.Ir.FRD | P.Ir.FRU)                    # žuti FL = plavi FR
    assert "vidi True" in app.log                                             # ir_sees('FRU') na plavoj = FLU


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
