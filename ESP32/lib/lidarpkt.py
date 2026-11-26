# Paket jednog kruga lidara za telemetriju (telem.py šalje, laptop prima). Bez zavisnosti osim struct:
# simulator ga učitava po putanji (eurosim/lidarsrc.py), kao rtttl.py.
#   zaglavlje LIDAR_FMT: magija "LIDR", verzija, ms ESP-a, broj kruga, Hz*10, najbliža tačka (mm, ugao)
#   pa 360 x uint16: mm po stepenu robota (0 = napred, + = levo), 0 = nema tačke; isti binovi kao lib/lidar.py
import struct

LIDAR_MAGIC = b"LIDR"
LIDAR_FMT = "<4sBIIHHh"                 # magija, verzija, ms ESP-a, broj kruga, Hz*10, najbliža mm, ugao
LIDAR_HDR = struct.calcsize(LIDAR_FMT)
LIDAR_BINS = 360
BINS_FMT = "<%dH" % LIDAR_BINS          # lidar.py daje najviše 16383 mm (q2 >> 2), pa uint16 uvek staje


def lidar_packet(L, now, buf=None):
    """Paket za jedan krug lidara (bytearray, ponovo se koristi isti bafer)."""
    if buf is None:
        buf = bytearray(LIDAR_HDR + 2 * LIDAR_BINS)
    near = L.nearest or (0, 0)
    struct.pack_into(LIDAR_FMT, buf, 0, LIDAR_MAGIC, 1, now & 0xFFFFFFFF, L.scans & 0xFFFFFFFF,
                     min(65535, int(L.hz * 10)), min(65535, near[0]), near[1])
    struct.pack_into(BINS_FMT, buf, LIDAR_HDR, *L.dist)     # bez nove liste: ~0,3 ms, 0 B na ESP32-S3
    return buf


def parse_lidar(data):
    """Paket -> dict (laptop: simulator, alati). None ako nije paket lidara."""
    if len(data) < LIDAR_HDR + 2 * LIDAR_BINS or data[:4] != LIDAR_MAGIC:
        return None
    _, ver, t, n, hz10, near_mm, near_deg = struct.unpack_from(LIDAR_FMT, data, 0)
    bins = list(struct.unpack_from(BINS_FMT, data, LIDAR_HDR))
    return {"ver": ver, "t": t, "scan": n, "hz": hz10 / 10, "bins": bins,
            "near": (near_mm, near_deg) if near_mm else None}
