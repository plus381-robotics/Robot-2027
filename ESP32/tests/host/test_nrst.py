# NRST pin (lib/nrst.py): direktno (open-drain, 0 = reset) i preko MOSFET-a na ESP32_Main (1 = reset).
from types import SimpleNamespace

from machine import Pin
from nrst import Nrst


def test_direktno_nula_je_reset():
    n = Nrst(SimpleNamespace(STM_NRST=90))
    assert Pin.levels[90] == 1
    n.hold(True)
    assert Pin.levels[90] == 0
    n.hold(False)
    assert Pin.levels[90] == 1


def test_obrnut_preko_mosfeta_jedan_je_reset():
    n = Nrst(SimpleNamespace(STM_NRST=91, STM_NRST_INV=True))
    assert Pin.levels[91] == 0                  # u mirovanju STM32 radi
    n.hold(True)
    assert Pin.levels[91] == 1
    n.hold(False)
    assert Pin.levels[91] == 0
