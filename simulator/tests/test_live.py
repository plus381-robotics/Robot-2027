# F3: live režim (komande, tasteri preko pravog inputs.py, ekran), protivnik koji se pomera.
import threading
import time

from eurosim.sim import Sim, simulate


class Remote:
    """Komande u zadatom virtuelnom trenutku (ms), kao da ih šalje UI."""

    def __init__(self, sim, plan):
        self.sim, self.plan = sim, sorted(plan, key=lambda p: p[0])

    def __call__(self):
        out = []
        while self.plan and self.sim.t() >= self.plan[0][0]:
            out.append(self.plan.pop(0)[1])
        return out


def live(plan, speed=1000, **kw):
    emitted = []
    s = Sim(kw.pop("name", "primer"), mode="live", emit=emitted.append, **kw)
    s.control = Remote(s, plan + [(plan[-1][0] + 3000, ("quit",))] if plan else [(500, ("quit",))])
    s.speed = speed
    return s, s.run(), emitted


def test_ekran_se_snima_u_brzoj_simulaciji():
    r = simulate("primer", mode="mec")
    sc = r.of("screen")
    assert sc and len(sc[0][2]["b"]) > 1000          # 1024 B u base64


def test_live_arm_cinc_taktika():
    s, r, em = live([(300, ("arm", "primer", "zuta")), (1000, ("cord",)), (6000, ("pause", False))])
    assert r.result["ok"] and [x[1] for x in r.steps()] == ["GOTO 600,1000", "OKRET na 90", "MOVE -200"]
    assert r.meta["tactic"] == "primer" and r.meta["side"] == "zuta"
    assert em and all("frames" in e for e in em) and em[-1]["t"] >= 6000


def test_live_tasteri_pravi_inputs_dugi_back_otvara_meni():
    s, r, _ = live([(300, ("btn", "back", 1)), (1100, ("btn", "back", 0))])
    assert len(s.app.ui.stack) > 1                    # meni je otvoren (dugi NAZAD, kao na robotu)


def test_live_stop_taster_prekida_taktiku():
    s, r, _ = live([(300, ("test", "primer", "plava")), (1200, ("btn", "stop", 1)), (1300, ("btn", "stop", 0))])
    assert r.result["how"] == "STOP"
    assert any(e[2]["name"] == "STOP" for e in r.of("rx"))


def test_live_enkoder_pomera_izbor_na_pocetnom_ekranu():
    s0, _, _ = live([(300, ("pause", False))])
    s, _, _ = live([(300, ("rot", 1))])
    assert s.app.pages.list[0].sel == s0.app.pages.list[0].sel + 1     # pravi pages.py: okret = sledeća opcija


def test_live_protivnik_postavljen_tokom_voznje_blokira():
    s, r, _ = live([(300, ("test", "primer", "plava")),
                    (1300, ("obstacles", [{"x": 800, "y": 1000, "w": 300, "h": 300}]))])
    assert r.steps()[0][3] == "BLOCKED"              # GOTO (START pozu u testu postavlja runner, nije korak)
    assert r.of("obstacles")


def test_live_ritam_prati_stvarno_vreme():
    t0 = time.time()
    s, r, _ = live([(1500, ("pause", False))], speed=2.0)
    wall = time.time() - t0
    assert 2.0 < wall < 4.5                           # 1.5 s + 3 s do quit, ×2 = ~2.25 s
