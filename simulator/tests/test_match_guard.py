# Zaštita toka meča (pregled logike L1, L2, L7): nov činč, NRST sa ESP-a, restart STM32 u meču,
# ESP sat meča, restart ESP-a u meču. Sve kroz pravi ESP kod (match.py, tac.py) nad simuliranim STM32.
import math

from eurosim import profile
from eurosim.sim import Sim

DUGO = ("from tac import *\nSTART = (250, 1000, 0)\n"
        "while True:\n    log('rez %s' % goto(1200, 1000, speed=300))\n    log('rez %s' % goto(400, 1000, speed=300))\n")


class Plan:
    def __init__(self, sim, plan):
        self.sim, self.plan = sim, sorted(plan, key=lambda p: p[0])

    def __call__(self):
        out = []
        while self.plan and self.sim.t() >= self.plan[0][0]:
            item = self.plan.pop(0)[1]
            out.extend(item(self.sim) if callable(item) else [item])
        return out


def live(plan, tmp_path, src=DUGO, nrst=True, end_ms=None):
    (tmp_path / "t.py").write_text(src)
    prof = profile.load(**({} if nrst else {"link.nrst": []}))
    s = Sim("t", mode="live", tactics_dir=tmp_path, prof=prof)
    last = max(t for t, _ in plan)
    s.control = Plan(s, plan + [(end_ms or last + 3000, ("quit",))])
    s.speed = 1000
    return s, s.run()


def moved(r, t0, t1):
    f = [x for x in r.frames if t0 <= x["t"] <= t1]
    return max(math.hypot(a["x"] - f[0]["x"], a["y"] - f[0]["y"]) for a in f)


def test_ponovno_naoruzavanje_posle_meca_resetuje_stm_preko_nrst_i_ceka_nov_cinc(tmp_path):
    s, r = live([(300, ("arm", "t", "zuta")), (1000, ("cord",)), (3000, ("stop",)),
                 (4000, ("arm", "t", "zuta")),            # STM32 i dalje broji stari meč
                 (9000, ("cord",))], tmp_path, end_ms=12000)
    logs = r.logs()
    assert any("reset STM32 (NRST)" in l for l in logs)
    assert any("STM32 resetovan" in l for l in logs)
    assert moved(r, 4200, 8900) < 3                          # do novog činča robot stoji (ranije: krene odmah)
    assert moved(r, 9000, 12000) > 100                        # posle činča vozi
    assert any(e[2]["text"].startswith("STM32 reset (NRST") for e in r.of("sim"))


def test_bez_nrst_naoruzavanje_starog_meca_se_odbija(tmp_path):
    s, r = live([(300, ("arm", "t", "zuta")), (1000, ("cord",)), (3000, ("stop",)),
                 (4000, ("arm", "t", "zuta"))], tmp_path, nrst=False, end_ms=8000)
    assert any("STM32 vec u mecu: restartuj STM32" in l for l in r.logs())
    assert moved(r, 4100, 8000) < 3
    assert not s.app.match.armed                                # odbijeno (stanje ostaje KRAJ od prvog meča)


def test_restart_stm32_u_mecu_vraca_pozu_i_taktika_nastavlja(tmp_path):
    s, r = live([(300, ("arm", "t", "zuta")), (1000, ("cord",)), (3500, ("stm_reset",))], tmp_path,
                end_ms=12000)
    logs = r.logs()
    assert any("STM32 restart u mecu" in l for l in logs) and any("STM32 obnovljen" in l for l in logs)
    assert any(x[3] == "RESTART" for x in r.steps())          # prekinuti korak vraća False
    assert s.app.match.stm_resets == 1                         # jedan restart = jedan prekinut korak
    f = r.frames[-1]
    assert math.hypot(f["x"] - f["ox"], f["y"] - f["oy"]) < 15   # odometrija = stvarna poza (nije 0,0,0)
    assert moved(r, 5000, 12000) > 100                         # taktika vozi dalje


def test_zaglavljen_stm32_u_mecu_nrst_pa_obnova(tmp_path):
    s, r = live([(300, ("arm", "t", "zuta")), (1000, ("cord",)), (3500, ("stm_hang",))], tmp_path, end_ms=12000)
    logs = r.logs()
    assert any("se ne javlja u mecu: reset (NRST)" in l for l in logs)
    assert any("STM32 obnovljen" in l for l in logs)
    # zaglavljen STM32 drži motore (u simulaciji voze dalje) dok ga NRST ne resetuje (~1.5 s): ESP ne može da
    # zna koliko je robot prešao, pa je greška poze najviše toliki put (300 mm/s * 1.5 s)
    f = r.frames[-1]
    assert math.hypot(f["x"] - f["ox"], f["y"] - f["oy"]) < 300 * 1.7


def test_esp_sat_zaustavlja_posle_100s_i_kad_stm32_broji_ispocetka(tmp_path):
    s, r = live([(300, ("arm", "t", "zuta")), (1000, ("cord",)), (50000, ("stm_reset",))], tmp_path,
                end_ms=110000)
    assert any("kraj meca" in l.lower() for l in r.logs())
    cord = 1000
    assert moved(r, cord + 100500, 110000) < 3                 # posle 100 s od činča robot stoji
    assert not s.stm.match_over                                 # a STM32 (restartovan na 50 s) misli da meč traje


def test_restart_esp_u_mecu_robot_stoji_i_javlja(tmp_path):
    (tmp_path / "t.py").write_text(DUGO)
    s = Sim("t", mode="live", tactics_dir=tmp_path)
    s.stm.match_start_now()                                     # STM32 već broji meč kad se ESP podigne
    s.control = Plan(s, [(4000, ("quit",))])
    s.speed = 1000
    r = s.run()
    assert any("MEC U TOKU posle restarta ESP-a" in l for l in r.logs())
    assert moved(r, 0, 4000) < 3
