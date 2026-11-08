# Protivnik sa svojom taktikom (plan E4): veliki robot i PAMI-ji. Taktika je fajl istim jezikom kao naše
# (Gambit Micro: goto, move, turn_to, wait, wait_until, match_time...), pisan za žutu stranu; simulator ga sam
# ogleda na protivnikovu stranu. Izvršava se unapred (lažni tac iz preview.py, idealno kretanje), pa protivnik
# u simulaciji ide po tako izračunatoj putanji u vremenu meča. Kad bi udario u naš robot (ili drugog protivnika)
# stoji i čeka; kamenolome gura (plant.push).
#
# Taktike: simulator/opponents/*.py (u repou; bez repoa ~/Eurosim/opponents).
import math
import random

from . import field, paths, preview
from .plant import poly_hit, rect_corners


def available():
    d = paths.OPPONENTS
    return sorted(p.stem for p in d.glob("*.py")) if d.exists() else []


def _other(side):
    return "plava" if side == "zuta" else "zuta"


class OppRunner:
    def __init__(self, obstacle, name, our_side, ref_side="zuta"):
        self.o = obstacle
        self.side = _other(our_side)                         # protivnik je na drugoj strani
        src = (paths.OPPONENTS / (name + ".py")).read_text(encoding="utf-8")
        mir = self.side != ref_side
        # početak: gde je postavljen na stolu (u koordinatama njegove taktike), osim ako taktika ima START
        start = (field.W - obstacle.x if mir else obstacle.x, obstacle.y,
                 (180 - (obstacle.th or 0)) if mir else (obstacle.th or 0))
        state = random.getstate()
        random.seed(obstacle.extra.get("seed", 1))           # "nasumično" je ponovljivo (isti sto = isti meč)
        try:
            p = preview.preview(src, self.side, ref_side, field.W, "mec", start=start, timed=True)
        finally:
            random.setstate(state)
        self.name, self.error = name, p["error"]
        self.cmds = [c for c in p["cmds"] if c["t1"] > c["t0"] or (c["x0"], c["y0"]) != (c["x1"], c["y1"])]
        sx, sy, sth = p["start"] or (obstacle.x, obstacle.y, obstacle.th or 0)
        self.home = (sx, sy, sth)
        self.tau = 0.0                                       # vreme u planu (s); stoji dok ga nešto blokira
        self.waiting = False

    def pose_at(self, tau):
        """(x, y, ugao) na terenu u trenutku tau plana: linearno duž komande, ugao = smer vožnje."""
        x, y, th = self.home
        for c in self.cmds:
            if tau < c["t0"]:
                break
            if tau >= c["t1"]:
                x, y, th = c["x1"], c["y1"], c["th"]
                continue
            k = (tau - c["t0"]) / (c["t1"] - c["t0"])
            if (c["x0"], c["y0"]) != (c["x1"], c["y1"]):
                th = math.degrees(math.atan2(c["y1"] - c["y0"], c["x1"] - c["x0"]))
                if c["kind"] == "move" and abs(((th - c["th"] + 180) % 360) - 180) > 90:
                    th = c["th"]                             # move unazad: telo ostaje okrenuto napred
            else:
                d = ((c["th"] - th + 180) % 360) - 180
                th = th + d * k
            return c["x0"] + (c["x1"] - c["x0"]) * k, c["y0"] + (c["y1"] - c["y0"]) * k, th
        return x, y, th

    def step(self, dt, plant, robot_poly):
        """Pomeri protivnika za dt (s) po planu, ako ne udara u naš robot; gurne kamenolome ispred sebe."""
        o = self.o
        nx, ny, nth = self.pose_at(self.tau + dt)
        poly = rect_corners(nx / 1000, ny / 1000, math.radians(nth), o.w / 1000, o.h / 1000)
        if poly_hit(poly, robot_poly):
            self.waiting = True
            return
        wall, objs = plant.hits(poly, ignore=[o])
        if objs:
            if not all(b.pushable for b in objs) or not plant.push(objs, (nx - o.x) / 1000, (ny - o.y) / 1000):
                self.waiting = True                          # drugi protivnik ili kamenolom koji ne može dalje
                return
        self.waiting = False
        o.x, o.y, o.th = nx, ny, nth
        self.tau += dt


def make_runners(opponents, our_side):
    out = []
    for o in opponents:
        name = o.extra.get("tactic")
        if name and (paths.OPPONENTS / (name + ".py")).exists():
            out.append(OppRunner(o, name, our_side))
    return out
