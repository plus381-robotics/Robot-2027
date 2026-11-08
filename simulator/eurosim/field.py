# Teren Eurobot 2027 (pravila, dodatak G.1, slika 8). Koordinate kao na STM32: x duž 3000 mm,
# y duž 2000 mm, ugao 0 = +x, pozitivno = levo (suprotno kazaljci gledano odozgo).
# Iz slike 8: žuta "prestona sala" (start i cilj, 50 x 50 cm) je na x 0..500, plava na x 2500..3000,
# obe na y 750..1250. Ivice: 70 mm visoke, 22 mm debele, van površine 3000 x 2000.
# Elementi igre (kamenolomi) i zone (bedemi, kapija, štale): ispod.

W, H = 3000, 2000
BORDER_T, BORDER_H = 22, 70

COLORS = {"plava": (0, 91, 140), "zuta": (247, 181, 0)}      # pravila, G.3 (RAL 5017 / RAL 1023)

START_ZONES = {                                              # (x0, y0, x1, y1) mm
    "zuta": (0, 750, 500, 1250),
    "plava": (2500, 750, 3000, 1250),
}


def describe():
    """Opis terena za prikaz (JSON)."""
    return {"w": W, "h": H, "border_t": BORDER_T, "border_h": BORDER_H,
            "zones": [{"side": s, "rect": r, "color": COLORS[s]} for s, r in START_ZONES.items()],
            "rule_zones": list(ZONES), "elements": elements(), "stone": STONE}


def in_zone(side, corners):
    """Da li su sva temena (lista (x, y) u mm) u startnoj zoni strane."""
    x0, y0, x1, y1 = START_ZONES[side]
    return all(x0 <= x <= x1 and y0 <= y <= y1 for x, y in corners)


# ---------------- elementi igre 2027 (pravila D.4 i E, položaji izmereni sa slike 8, 1 px = 1 mm) ----------------
# Kamen: kartonska kutija 320 x 110 x 110 mm (~90 g). Kamenolom: 3 kamena položena i naslagana (visina 330 mm).
# Ima ih 10 (30 kamenova): 4 uz gornju i 4 uz donju ivicu, 2 na sredini (uspravno, duž y).
STONE = (320, 110, 110)
QUARRIES = [(750, 1945, 0), (1250, 1945, 0), (1750, 1945, 0), (2250, 1945, 0),
            (750, 55, 0), (1250, 55, 0), (1750, 55, 0), (2250, 55, 0),
            (1500, 1500, 90), (1500, 500, 90)]


def _both(items):
    """Žuta polovina -> obe (plava je ogledalo po x)."""
    out = []
    for side, it in (("zuta", items), ("plava", items)):
        for d in it:
            d = dict(d, side=side)
            if side == "plava":
                d["x"] = W - d["x"]
                if "th" in d:
                    d["th"] = 180 - d["th"]
            out.append(d)
    return out


# Zone (oznake na podu, ne prepreke): bedemi (zid 200 x 400, kula fi 200), kapija (200 x 400, deo zida),
# štala za SIMA (200 x 300). Dvorište i jarak su na slici stola (nepravilni oblici).
ZONES = (
    _both([{"kind": "kula", "x": 500, "y": 1600, "r": 100}, {"kind": "kula", "x": 850, "y": 1250, "r": 100},
           {"kind": "kula", "x": 850, "y": 750, "r": 100}, {"kind": "kula", "x": 500, "y": 400, "r": 100}])
    + _both([{"kind": "zid", "x": 820, "y": 1575, "w": 400, "h": 200, "th": -45},
             {"kind": "zid", "x": 820, "y": 425, "w": 400, "h": 200, "th": 45}])
    + _both([{"kind": "kapija", "x": 1050, "y": 1000, "w": 200, "h": 400, "th": 0}])
    + _both([{"kind": "stala", "x": 100, "y": 150, "w": 200, "h": 300, "th": 0},
             {"kind": "stala", "x": 100, "y": 1850, "w": 200, "h": 300, "th": 0}])
)


def elements():
    """Prepreke na početku meča: kamenolomi (3 kamena, 330 mm). Za plant.Obstacle(**d)."""
    L, Wd, H = STONE
    return [{"name": "kamenolom %d" % (i + 1), "kind": "kamenolom", "x": x, "y": y, "w": L, "h": Wd, "th": th,
             "z": 3 * H, "stones": 3} for i, (x, y, th) in enumerate(QUARRIES)]
