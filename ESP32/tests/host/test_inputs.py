import config as cfg
from machine import Pin
import inputs

CW = [(0, 1), (0, 0), (1, 0), (1, 1)]


def turn(states):
    for a, b in states:
        Pin.levels[cfg.ENC_A], Pin.levels[cfg.ENC_B] = a, b
        Pin.handlers[cfg.ENC_A](None)


def test_enkoder():
    Pin.levels[cfg.ENC_A] = Pin.levels[cfg.ENC_B] = 1
    e = inputs.Encoder(cfg.ENC_A, cfg.ENC_B, 4)
    assert e.hard                                       # U-1: hard IRQ
    turn(CW + CW)
    assert e.take() == 2
    turn([(1, 0), (0, 0), (0, 1), (1, 1)])
    assert e.take() == -1
    turn([(0, 1), (1, 1), (0, 1), (1, 1)])               # odskakanje
    assert e.take() == 0
    turn([(0, 1), (1, 0), (1, 1)])                       # izgubljen prelaz
    assert e.take() == 1
