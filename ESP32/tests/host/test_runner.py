# Glavna petlja: greška u jednom servisu ne ruši ostale (PING ka STM32 mora da ide dalje).
import pytest

import compat
from runner import Loop


def test_greska_u_servisu_ne_zaustavlja_ostale():
    calls, reported = [], []

    def lose():
        raise ValueError("pokvaren ekran")

    loop = Loop([("ekran", lose), ("robot", lambda: calls.append(1))], compat.sleep_ms,
                on_error=lambda faza, tekst: reported.append((faza, tekst)))
    for _ in range(5):
        loop.step()
    assert len(calls) == 5                                   # "robot" radi u svakom krugu
    assert loop.errors["ekran"] == 5
    assert reported == [("ekran", "ValueError pokvaren ekran")]    # ista greška se javlja jednom


def test_nova_greska_se_ponovo_javlja():
    n, reported = [0], []

    def lose():
        n[0] += 1
        raise KeyError(n[0] // 3)

    loop = Loop([("x", lose)], compat.sleep_ms, on_error=lambda f, t: reported.append(t))
    for _ in range(6):
        loop.step()
    assert len(reported) == 3                                # KeyError 0, 1, 2


def test_ctrl_c_i_reset_prolaze():
    def ctrl_c():
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        Loop([("x", ctrl_c)], compat.sleep_ms).step()

    def reset():
        raise SystemExit("machine.reset()")

    with pytest.raises(SystemExit):
        Loop([("x", reset)], compat.sleep_ms).step()


def test_greska_u_servisu_tokom_taktike_ne_prekida_taktiku(app, stm):
    from runner import run_tactic
    (app.tactics_dir / "t.py").write_text("from tac import *\nok = move(200)\nlog('rez %s' % ok)\n")
    app.loop.on_error = lambda f, t: app.error("%s: %s" % (f, t))
    app.loop.services.append(("pukne", lambda: 1 / 0))
    run_tactic(app, "t")
    assert "rez True" in app.log
    assert any("pukne: ZeroDivisionError" in t for _, t in app.errors)
