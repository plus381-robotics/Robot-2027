# Host testovi ESP koda na laptopu (CPython): python -m pytest ESP32/tests/host
# Koriste lažni machine/framebuf/ssd1306 i lažni STM32 iz ESP32/sim/.
import pathlib
import sys

import pytest

ESP = pathlib.Path(__file__).resolve().parents[2]
for p in (ESP / "sim", ESP, ESP / "lib"):
    sys.path.insert(0, str(p))


@pytest.fixture(autouse=True)
def fake_clock():
    import compat
    compat.fake = [100000]
    yield compat.fake
    compat.fake = None


@pytest.fixture
def stm():
    from fakestm import FakeSTM
    return FakeSTM()


@pytest.fixture
def app(stm, tmp_path, monkeypatch):
    """App bez ekrana, sa lažnim STM32 i petljom kao u main.py (bez WiFi-ja i ulaza)."""
    import tactic
    import tac
    from robot import Robot
    from settings import Settings
    from app import App
    from runner import Loop
    import compat
    tactic.tracker.__init__()
    monkeypatch.setattr(tactic, "TACTICS_DIR", str(tmp_path))
    a = App(Robot(stm), Settings(str(tmp_path / "settings.json")), None)
    a.loop = Loop([("robot", a.update), ("ekran", a.ui.tick)], compat.sleep_ms)
    a.pump = a.loop.step
    tac.app = a
    a.tactics_dir = tmp_path
    return a


def run(app, ms):
    import compat
    end = compat.ticks_ms() + ms
    while compat.ticks_ms() < end:
        app.pump()
