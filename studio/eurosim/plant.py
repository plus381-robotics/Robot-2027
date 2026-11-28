# Model robota ("fizika"): diferencijalni pogon, odometrija sa pasivnim točkovima, sudari, IR senzori.
#
#  - Pogonski točkovi prate referencu iz regulacije sa kašnjenjem (motor_tau) i ograničenim ubrzanjem
#    (wheel_a_max), najviše wheel_v_max. To zamenjuje brzinski PID + motor (bez merenja nemamo bolje).
#  - Stvarna poza se računa iz stvarnih brzina točkova i stvarnog razmaka (wheel_track).
#  - Odometrija (ono što STM32 javlja i po čemu vozi) se računa iz pasivnih točkova na encoder_track,
#    sa opcionim greškama (left_scale, right_scale, track_scale). SET_POSE menja samo odometriju.
#  - Sudar sa ivicom stola ili preprekom: robot stoji (pogonski točkovi proklizavaju), pasivni točkovi
#    ne broje -> regulacija vidi v = 0 -> "stacked" -> BLOCKED, kao na robotu.
#  - IR: po 4 senzora napred i nazad (uglovi, dole i gore); bit 0 = prepreka napred, bit 1 = nazad.
import math

from . import field

DT = 0.001


class Obstacle:
    """Prepreka (npr. protivnik): pravougaonik w x h (mm) oko (x, y), ugao th (stepeni), visina z (mm).
    r > 0: krug poluprečnika r umesto pravougaonika."""

    def __init__(self, x, y, w=300, h=300, th=0.0, z=350, r=0, name="protivnik", kind="protivnik", **extra):
        self.x, self.y, self.w, self.h, self.th, self.z, self.r, self.name = x, y, w, h, th, z, r, name
        self.kind, self.extra = kind, extra

    def poly(self):
        key = (self.x, self.y, self.th, self.w, self.h)
        if getattr(self, "_pk", None) != key:          # prepreka se retko pomera: oblik se pamti
            self._pk = key
            self._poly = rect_corners(self.x / 1000, self.y / 1000, math.radians(self.th), self.w / 1000, self.h / 1000)
        return self._poly

    @property
    def pushable(self):
        """Elementi igre (kamenolom) se guraju; protivnik ne."""
        return self.kind == "kamenolom"

    def moved(self, dx_mm, dy_mm):
        """Kopija oblika pomerena za dx, dy (za proveru pre guranja)."""
        return rect_corners((self.x + dx_mm) / 1000, (self.y + dy_mm) / 1000, math.radians(self.th),
                            self.w / 1000, self.h / 1000)

    def radius(self):
        """Poluprečnik kruga oko prepreke (m), za brzo odbacivanje dalekih."""
        return (self.r if self.r else math.hypot(self.w, self.h) / 2) / 1000

    def to_dict(self):
        return dict(self.extra, name=self.name, kind=self.kind, x=self.x, y=self.y, w=self.w, h=self.h,
                    th=self.th, z=self.z, r=self.r)


def rect_corners(cx, cy, th, length, width, offset=0.0):
    """Temena pravougaonika (m): length duž ugla th, width popreko, centar pomeren za offset napred."""
    c, s = math.cos(th), math.sin(th)
    cx, cy = cx + offset * c, cy + offset * s
    hl, hw = length / 2, width / 2
    return [(cx + a * c - b * s, cy + a * s + b * c) for a, b in ((hl, hw), (-hl, hw), (-hl, -hw), (hl, -hw))]


def _proj(poly, ax, ay):
    d = [px * ax + py * ay for px, py in poly]
    return min(d), max(d)


def poly_hit(a, b):
    """SAT: da li se dva konveksna poligona preklapaju."""
    for poly in (a, b):
        for i in range(len(poly)):
            x1, y1 = poly[i]
            x2, y2 = poly[(i + 1) % len(poly)]
            ax, ay = y1 - y2, x2 - x1
            a0, a1 = _proj(a, ax, ay)
            b0, b1 = _proj(b, ax, ay)
            if a1 <= b0 or b1 <= a0:
                return False
    return True


def circle_poly_hit(cx, cy, r, poly):
    inside = True
    for i in range(len(poly)):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % len(poly)]
        dx, dy = x2 - x1, y2 - y1
        t = max(0.0, min(1.0, ((cx - x1) * dx + (cy - y1) * dy) / (dx * dx + dy * dy)))
        if math.hypot(x1 + t * dx - cx, y1 + t * dy - cy) < r:
            return True
        if (dx * (cy - y1) - dy * (cx - x1)) < 0:
            inside = False
    return inside


def ray_dist(ox, oy, dx, dy, poly=None, circle=None, max_d=1.0):
    """Udaljenost duž zraka do poligona ili kruga (cx, cy, r), ili None (m)."""
    best = None
    if circle:
        cx, cy, r = circle
        fx, fy = ox - cx, oy - cy
        b = fx * dx + fy * dy
        c = fx * fx + fy * fy - r * r
        disc = b * b - c
        if disc >= 0:
            t = -b - math.sqrt(disc)
            if t < 0:
                t = -b + math.sqrt(disc) if c > 0 else 0.0
            if 0 <= t <= max_d:
                best = t
        return best
    for i in range(len(poly)):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % len(poly)]
        ex, ey = x2 - x1, y2 - y1
        den = dx * ey - dy * ex
        if abs(den) < 1e-12:
            continue
        t = ((x1 - ox) * ey - (y1 - oy) * ex) / den
        u = ((x1 - ox) * dy - (y1 - oy) * dx) / den
        if 0 <= u <= 1 and 0 <= t <= max_d and (best is None or t < best):
            best = t
    return best


class Plant:
    def __init__(self, profile):
        p = profile
        self.track = p.m("drive", "wheel_track")
        self.v_max = p["drive"]["wheel_v_max"]
        self.a_max = p["drive"]["wheel_a_max"]
        self.tau = p["drive"]["motor_tau"]
        self.length = p.m("body", "length")
        self.width = p.m("body", "width")
        self.height = p["body"]["height"]
        self.offset = p.m("body", "axle_offset")
        self.enc = p.m("odometry", "encoder_track")
        o = p["odometry"]
        self.ls, self.rs, self.ts = o["left_scale"], o["right_scale"], o["track_scale"]
        ir = p.get("ir", {})
        self.ir_on = ir.get("enabled", True)
        self.ir_range = ir.get("range", 250) / 1000
        # senzori (protokol v5): u svakom uglu donji (D) i gornji (U); visine iz profila
        self.ir_z = (ir.get("low_z", 40), ir.get("high_z", 340))
        self.ir_mask = 0xFF                    # uključeni (STM32 IR_MASK), samo za prikaz
        self.ir_walls = ir.get("see_walls", False)
        self.ir_elements = ir.get("see_elements", True)
        self.reach = math.hypot(self.length, self.width) / 2 + abs(self.offset)    # robot u krugu ovog poluprečnika
        # stanje
        self.x = self.y = self.th = 0.0         # stvarna poza (m, rad)
        self.vl = self.vr = 0.0                 # stvarne brzine pogonskih točkova (m/s)
        self.v = self.w = 0.0                   # stvarna brzina tela (0 kad je zaglavljen)
        self.ox = self.oy = self.oth = 0.0      # odometrija
        self.ov = self.ow = 0.0
        self.stuck = False
        self.obstacles = []
        el = p.get("elements", {})
        self.push_on = el.get("pushable", True)            # robot gura kamenolome (plan E3)
        self.push_resist = el.get("push_resist", 0.5)      # 0..1: koliko guranje usporava robota
        self.pushed = False                                # neki element je pomeren (za snimak)
        self.ir = 0                             # bit po senzoru (protocol.Ir: FLD=1 ... BRU=128): šta vidi
        self.ir_hits = []                       # [(senzor, d_m)] za prikaz

    # ---------------- poza ----------------

    def place(self, x_mm, y_mm, deg):
        """Postavi robota na sto (stvarna poza). Odometrija se ne menja (STM32 to ne zna)."""
        self.x, self.y, self.th = x_mm / 1000, y_mm / 1000, math.radians(deg)

    def set_odom(self, x, y, th):
        self.ox, self.oy, self.oth = x, y, th

    def corners(self, x=None, y=None, th=None):
        return rect_corners(self.x if x is None else x, self.y if y is None else y,
                            self.th if th is None else th, self.length, self.width, self.offset)

    def collides(self, poly):
        """Brza provera (robot, svake ms): prva prepreka ili ivica. Ko je udaren: hits()."""
        W, H = field.W / 1000, field.H / 1000
        if any(px < 0 or px > W or py < 0 or py > H for px, py in poly):
            return True
        cx, cy = sum(p[0] for p in poly) / 4, sum(p[1] for p in poly) / 4
        rr = self.reach
        for o in self.obstacles:
            if math.hypot(o.x / 1000 - cx, o.y / 1000 - cy) > rr + o.radius():
                continue
            if o.r:
                if circle_poly_hit(o.x / 1000, o.y / 1000, o.r / 1000, poly):
                    return True
            elif poly_hit(poly, o.poly()):
                return True
        return False

    def hits(self, poly, ignore=(), first=False, rr=None):
        """(udara u ivicu stola, [prepreke koje dodiruje]). rr: poluprečnik oblika (m), ako je poznat."""
        W, H = field.W / 1000, field.H / 1000
        if any(px < 0 or px > W or py < 0 or py > H for px, py in poly):
            return True, []
        cx, cy = sum(p[0] for p in poly) / len(poly), sum(p[1] for p in poly) / len(poly)
        if rr is None:
            rr = max(math.hypot(px - cx, py - cy) for px, py in poly)
        out = []
        for o in self.obstacles:
            if o in ignore or math.hypot(o.x / 1000 - cx, o.y / 1000 - cy) > rr + o.radius():
                continue
            if (circle_poly_hit(o.x / 1000, o.y / 1000, o.r / 1000, poly) if o.r else poly_hit(poly, o.poly())):
                out.append(o)
                if first:
                    break
        return False, out

    def push(self, objs, dx, dy, mover=None):
        """Pomeri gurnute elemente za dx, dy (m), ako ne udaraju u ivicu, druge prepreke ili onoga ko gura
        (mover: oblik posle pomeranja). True = pomereno."""
        dmx, dmy = dx * 1000, dy * 1000
        for o in objs:
            poly = o.moved(dmx, dmy)
            wall, other = self.hits(poly, ignore=list(objs), first=True)
            if wall or other:
                return False
        for o in objs:
            o.x, o.y = o.x + dmx, o.y + dmy
        self.pushed = True
        return True

    # ---------------- korak ----------------

    def step(self, vr_ref, vl_ref):
        dt = DT
        k = dt / self.tau if self.tau > 0 else 1.0
        amax = self.a_max * dt
        for side in ("vr", "vl"):
            v = getattr(self, side)
            ref = vr_ref if side == "vr" else vl_ref
            dv = (ref - v) * min(1.0, k)
            dv = max(-amax, min(amax, dv))
            v = max(-self.v_max, min(self.v_max, v + dv))
            setattr(self, side, v)
        v = (self.vr + self.vl) / 2
        w = (self.vr - self.vl) / self.track
        th_mid = self.th + w * dt / 2
        nx = self.x + v * math.cos(th_mid) * dt
        ny = self.y + v * math.sin(th_mid) * dt
        nth = self.th + w * dt
        blocked = False
        if (v or w) and self.collides(self.corners(nx, ny, nth)):
            blocked = True
            # kamenolom ispred: gura se (robot sporije), ako ima mesta; inače točkovi proklizavaju, telo stoji
            wall, objs = self.hits(self.corners(nx, ny, nth), rr=self.reach) if self.push_on and abs(v) > 1e-4 \
                else (True, [])
            if not wall and objs and all(o.pushable for o in objs):
                f = 1.0 - self.push_resist
                v, w = v * f, w * f
                th_mid = self.th + w * dt / 2
                nx, ny, nth = self.x + v * math.cos(th_mid) * dt, self.y + v * math.sin(th_mid) * dt, self.th + w * dt
                blocked = not self.push(objs, nx - self.x, ny - self.y)
        if blocked:
            v = w = 0.0
            self.stuck = True
        else:
            self.stuck = False
            self.x, self.y, self.th = nx, ny, (nth + math.pi) % (2 * math.pi) - math.pi
        self.v, self.w = v, w
        # pasivni točkovi odometrije (na ±enc/2) i greške
        e = self.enc / 2
        ml = (v - w * e) * self.ls
        mr = (v + w * e) * self.rs
        ov = (ml + mr) / 2
        ow = (mr - ml) / (self.enc * self.ts)
        oth_mid = self.oth + ow * dt / 2
        self.ox += ov * math.cos(oth_mid) * dt
        self.oy += ov * math.sin(oth_mid) * dt
        self.oth = (self.oth + ow * dt + math.pi) % (2 * math.pi) - math.pi
        self.ov, self.ow = ov, ow

    # ---------------- IR ----------------

    def sensor_layout(self):
        """[(ime, x, y, smer, z)] u koordinatama robota (m; x napred, y levo; smer +1 napred, -1 nazad).
        U svakom uglu donji i gornji: FLD FLU FRD FRU BLD BLU BRD BRU (redosled = bitovi protocol.Ir)."""
        if getattr(self, "_layout", None):
            return self._layout
        out = self._layout = []
        hw = self.width / 2 - 0.01
        for fb, d in (("F", 1), ("B", -1)):
            x = d * self.length / 2 + self.offset             # prednja ili zadnja ivica tela
            for lr, y in (("L", hw), ("R", -hw)):
                for du, z in (("D", self.ir_z[0]), ("U", self.ir_z[1])):
                    out.append((fb + lr + du, x, y, d, z))
        return out

    def sensors(self):
        """Senzori na stolu: (ime, x, y, (dx, dy), z) u metrima. Redosled = bitovi protocol.Ir (FLD FLU FRD FRU BLD BLU BRD BRU)."""
        c, s = math.cos(self.th), math.sin(self.th)
        return [(name, self.x + a * c - b * s, self.y + a * s + b * c, (c * d, s * d), z)
                for name, a, b, d, z in self.sensor_layout()]

    def scan(self):
        """Osveži IR bitove. Vidi prepreke više od senzora (i ivice, ako je see_walls)."""
        bits, hits = 0, []
        if not self.ir_on:
            self.ir, self.ir_hits = 0, []
            return 0
        W, H = field.W / 1000, field.H / 1000
        walls = [(0, 0), (W, 0), (W, H), (0, H)]
        near = [o for o in self.obstacles
                if (o.kind == "protivnik" or self.ir_elements)
                and math.hypot(o.x / 1000 - self.x, o.y / 1000 - self.y) <= self.reach + self.ir_range + o.radius()]
        if not near and not self.ir_walls:
            self.ir, self.ir_hits = 0, []
            return 0
        for k, (name, sx, sy, (dx, dy), z) in enumerate(self.sensors()):
            best = None
            for o in near:
                if o.z < z:
                    continue
                d = ray_dist(sx, sy, dx, dy, circle=(o.x / 1000, o.y / 1000, o.r / 1000), max_d=self.ir_range) \
                    if o.r else ray_dist(sx, sy, dx, dy, poly=o.poly(), max_d=self.ir_range)
                if d is not None and (best is None or d < best):
                    best = d
            if self.ir_walls and z <= field.BORDER_H:
                d = ray_dist(sx, sy, dx, dy, poly=walls, max_d=self.ir_range)
                if d is not None and (best is None or d < best):
                    best = d
            if best is not None:
                hits.append((name, best))
                bits |= 1 << k                    # protocol.Ir: FLD=1, FLU=2 ... BRU=128
        self.ir, self.ir_hits = bits, hits
        return bits
