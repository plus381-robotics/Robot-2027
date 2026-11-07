# Teren Eurobot 2027 (pravila, dodatak G.1, slika 8). Koordinate kao na STM32: x duž 3000 mm,
# y duž 2000 mm, ugao 0 = +x, pozitivno = levo (suprotno kazaljci gledano odozgo).
# Iz slike 8: žuta "prestona sala" (start i cilj, 50 x 50 cm) je na x 0..500, plava na x 2500..3000,
# obe na y 750..1250. Ivice: 70 mm visoke, 22 mm debele, van površine 3000 x 2000.
# Elementi igre (zamak, jarak, kamenje...) dolaze u kasnijoj fazi.

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
            "zones": [{"side": s, "rect": r, "color": COLORS[s]} for s, r in START_ZONES.items()]}


def in_zone(side, corners):
    """Da li su sva temena (lista (x, y) u mm) u startnoj zoni strane."""
    x0, y0, x1, y1 = START_ZONES[side]
    return all(x0 <= x <= x1 and y0 <= y <= y1 for x, y in corners)
