# Test dela → Lidar: međukoraci obrade jednog kruga lidara, računa ih LAPTOP (prikaz to i piše: „izračunao laptop“).
# ESP (ESP32/lib/lidar.py) danas ima samo drajver, binove po stepenu i najbližu tačku (_closest -> "near" u krugu);
# detekcije i grupisanja na robotu nema, pa se ovde ništa ne preuzima iz ESP koda. Kad ESP dobije detekciju (Faza 6),
# ovaj modul treba da je pozove isto kao lidarsrc.pkt() učitava lidarpkt.py.
#
#   stages(scan, pose, prof) -> {"in": [[x, y]], "out": [[x, y]], "groups": [{x, y, n, dist, angle, rx, ry}],
#                                "nearest": dict | None, + "raw", "frame", "esp_near", "by"}
#   scan  događaj "lidar" (eurosim/sim.py _collect_lidar, robotlink.py feed_lidar):
#         {"pts": [ugao, mm, ugao, mm, ...] (ugao robota u stepenima, 0 = napred, + = levo), "o": [x, y, z] lidar na
#          robotu (mm; nema -> profil [lidar]), "near": [mm, ugao] | None (ESP _closest), "hz": ...}
#   pose  (x, y, ugao°) robota na stolu ili None (nema poze: STM32 nije povezan, snimak bez poze)
#
# Sa pozom: tačke u koordinatama stola; "in" = na stolu 0..3000 × 0..2000 uz toleranciju MARGIN_MM, ostalo "out"
# (sudija pored stola nije protivnik). Grupe = tačke iz "in" bar EDGE_MM od ivice (ivica stola nije protivnik),
# redom po uglu, nova grupa kad je razmak > GAP_MM; grupa ima bar MIN_N tačaka.
# Bez poze: nema stola, "in" == "out" == []; grupe od svih tačaka, u koordinatama robota.
# "raw" = sve tačke u koordinatama robota ([x napred, y levo, k], k: 1 u stolu, 0 van stola, -1 nema poze), za radar.
# dist / angle grupe su od centra robota: dist = najbliža tačka grupe (mm), angle = pravac težišta (stepeni robota,
# suprotno kazaljci od napred, -180..180); x / y = težište na stolu (bez poze: kod robota), rx / ry = težište kod robota.
import math

from . import field

MARGIN_MM = 20         # tačka do 20 mm van ivice je još na stolu (šum, debljina ivice)
EDGE_MM = 60           # tačke bliže ivici od ovoga su ivica stola, ne ulaze u grupe
GAP_MM = 80            # veći razmak između susednih tačaka = nova grupa
MIN_N = 3              # manje tačaka nije grupa (šum)
MAX_PTS = 720          # najviše tačaka u krugu (360 binova; dvostruko za svaki slučaj)


def _offset(scan, prof):
    o = scan.get("o")
    if o and len(o) >= 2:
        return float(o[0]), float(o[1])
    lp = (prof or {}).get("lidar", {}) or {}
    return float(lp.get("x", 0)), float(lp.get("y", 0))


def _robot_points(scan, prof):
    """Tačke kruga u koordinatama robota (mm): [(x napred, y levo)], redom kao u krugu (po uglu)."""
    ox, oy = _offset(scan, prof)
    p = list(scan.get("pts") or [])[:2 * MAX_PTS]
    out = []
    for i in range(0, len(p) - 1, 2):
        a, d = float(p[i]), float(p[i + 1])
        if d <= 0:
            continue
        r = math.radians(a)
        out.append((ox + d * math.cos(r), oy + d * math.sin(r)))
    return out


def _on_table(x, y, m):
    return -m <= x <= field.W + m and -m <= y <= field.H + m


def _clusters(items):
    """items: [(px, py, rx, ry)] redom po uglu -> liste susednih (razmak <= GAP_MM); prva i poslednja se spajaju
    kad je krug zatvoren (0° i 359° su susedi)."""
    groups, cur = [], []
    for it in items:
        if cur and math.hypot(it[0] - cur[-1][0], it[1] - cur[-1][1]) > GAP_MM:
            groups.append(cur)
            cur = []
        cur.append(it)
    if cur:
        groups.append(cur)
    if len(groups) > 1:
        a, b = groups[0][0], groups[-1][-1]
        if math.hypot(a[0] - b[0], a[1] - b[1]) <= GAP_MM:
            groups[0] = groups.pop() + groups[0]
    return groups


def _group(g):
    n = len(g)
    cx, cy = sum(p[0] for p in g) / n, sum(p[1] for p in g) / n          # težište (sto ili robot)
    rx, ry = sum(p[2] for p in g) / n, sum(p[3] for p in g) / n          # težište u koordinatama robota
    dist = min(math.hypot(p[2], p[3]) for p in g)
    return {"x": round(cx), "y": round(cy), "n": n, "dist": round(dist),
            "angle": round(math.degrees(math.atan2(ry, rx)), 1), "rx": round(rx), "ry": round(ry)}


def stages(scan, pose, prof=None):
    scan = scan or {}
    rp = _robot_points(scan, prof)
    near = scan.get("near")
    res = {"in": [], "out": [], "groups": [], "nearest": None, "raw": [], "by": "laptop",
           "frame": "sto" if pose is not None else "robot",
           "esp_near": {"dist": near[0], "angle": near[1]} if near else None}
    items = []
    if pose is None:
        for rx, ry in rp:
            res["raw"].append([round(rx), round(ry), -1])
            items.append((rx, ry, rx, ry))
    else:
        x0, y0, th = float(pose[0]), float(pose[1]), math.radians(float(pose[2]))
        c, s = math.cos(th), math.sin(th)
        for rx, ry in rp:
            px, py = x0 + rx * c - ry * s, y0 + rx * s + ry * c
            on = _on_table(px, py, MARGIN_MM)
            (res["in"] if on else res["out"]).append([round(px), round(py)])
            res["raw"].append([round(rx), round(ry), 1 if on else 0])
            if on and _on_table(px, py, -EDGE_MM):
                items.append((px, py, rx, ry))
    res["groups"] = [_group(g) for g in _clusters(items) if len(g) >= MIN_N]
    if res["groups"]:
        res["nearest"] = dict(min(res["groups"], key=lambda g: g["dist"]))
    return res
