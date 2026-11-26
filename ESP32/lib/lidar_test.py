# Meni -> Lidar test: lidar se pali kad se uđe, gasi kad se izađe (NAZAD, taktika krene...).
#   mapa (prvi prikaz): poslednji krug odozgo, robot u sredini, napred = gore; okret enkodera = razmera
#   info (OK):          model, firmver, zdravlje, krugova/s, tačaka, najbliža tačka, odbačeni bajtovi
# Lidar se čita u tick() (svaki krug petlje dok je ovaj ekran na vrhu), crta se na LIVE_MS.
import math
import ui
from ui import Screen, text_center, text_right, fit, H, W, HEAD

ZOOM = (500, 1000, 2000, 4000)          # mm od robota do gornje ivice mape
_SIN = _COS = None


def _tables():
    global _SIN, _COS
    if _SIN is None:
        _SIN = [math.sin(math.radians(k)) for k in range(360)]
        _COS = [math.cos(math.radians(k)) for k in range(360)]


def model_name(m):
    """RPLIDAR model (bajt iz GET_INFO): gornja 4 bita = serija (A1 = 1, A2 = 2, A3 = 3)."""
    return "A%d" % (m >> 4) if 1 <= m >> 4 <= 3 else "0x%02X" % m


class LidarScreen(Screen):
    live = True
    live_ms = 150

    def __init__(self, app):
        self.app = app
        self.view = 0
        self.zoom = 1
        self.err = None
        self.lidar = None
        try:
            import config as cfg
            import lidar
            self.lidar = lidar.get(cfg)
            if self.lidar is None:
                self.err = "nema na ploci"
        except Exception as e:          # noqa: BLE001  (UART/PWM ne može da se otvori)
            self.err = fit("%s %s" % (type(e).__name__, e), 16)
        if self.lidar:
            self.lidar.start()

    def tick(self, u):
        if self.lidar:
            self.lidar.poll()

    def leave(self):
        if self.lidar:
            self.lidar.stop()

    def rotate(self, u, n):
        self.zoom = max(0, min(len(ZOOM) - 1, self.zoom + n))

    def ok(self, u):
        self.view ^= 1

    # ---------------- crtanje ----------------

    def _status(self):
        """Kratko stanje za traku desno."""
        L = self.lidar
        if not L:
            return "-"
        if L.scanning:
            return "%.1fHz" % L.hz
        return {"greska": "GRESKA", "off": "iskl"}.get(L.state, "...")

    def draw(self, u, fb):
        u.header(fb, "LIDAR", self._status())
        L = self.lidar
        if self.view == 1:
            self._info(fb, L)
        elif not L or not L.scanning:
            self._waiting(fb, L)
        else:
            self._map(fb, L)

    def _waiting(self, fb, L):
        if not L:
            text_center(fb, "nema lidara", HEAD + 10)
            text_center(fb, fit(self.err or "", 16), HEAD + 24)
            return
        if L.state == "greska":
            text_center(fb, fit(L.why, 16), HEAD + 8)
            text_center(fb, "proveri TX/RX," if L.why == "nema odgovora" else "", HEAD + 22)
            text_center(fb, "5V i motor" if L.why == "nema odgovora" else "", HEAD + 32)
            ui.action_bar(fb, "NAZAD = izlaz")
            return
        text_center(fb, {"stop": "pokrecem", "info": "GET_INFO", "health": "GET_HEALTH",
                         "scanwait": "SCAN", "scan": fit(L.why or "ceka krug", 16)}.get(L.state, L.state), HEAD + 10)
        dots = "." * (1 + (ui.ticks_ms() // 300) % 3)
        text_center(fb, dots, HEAD + 22)
        if L.why == "nema tacaka":
            text_center(fb, "motor se vrti?", HEAD + 34)

    def _map(self, fb, L):
        _tables()
        top = HEAD
        cx, cy = W // 2, top + (H - top) // 2
        r = cy - top - 1                         # piksela do gornje ivice
        k = r / ZOOM[self.zoom]
        for a in range(0, 360, 15):              # krug razmere (tačkasto)
            fb.pixel(int(cx - r * _SIN[a]), int(cy - r * _COS[a]), 1)
        dist = L.dist
        for a in range(360):                     # napred = gore, levo (+ugao) = levo
            d = dist[a]
            if d:
                x = int(cx - d * k * _SIN[a] + 0.5)
                y = int(cy - d * k * _COS[a] + 0.5)
                if 0 <= x < W and top <= y < H:
                    fb.pixel(x, y, 1)
        fb.pixel(cx, cy - 2, 1)                   # robot: trougao, vrh napred
        fb.hline(cx - 1, cy - 1, 3, 1)
        fb.hline(cx - 2, cy, 5, 1)
        z = ZOOM[self.zoom]
        fb.text(("%dm" % (z // 1000)) if z >= 1000 else ("%.1fm" % (z / 1000)), 0, H - 8, 1)
        n = L.nearest
        if n:
            d, a = n
            a %= 360
            x, y = int(cx - d * k * _SIN[a] + 0.5), int(cy - d * k * _COS[a] + 0.5)
            if 0 <= x < W and top <= y < H:      # najbliža tačka: krstić
                fb.hline(x - 2, y, 5, 1)
                fb.vline(x, y - 2, 5, 1)
            text_right(fb, "%dmm" % d, W, H - 8)

    def _info(self, fb, L):
        rows = []
        if not L:
            rows = ["nema lidara", self.err or ""]
        else:
            i = L.info
            rows.append(("%s fw%s hw%d" % (model_name(i["model"]), i["fw"], i["hw"])) if i else "model: -")
            h = L.health
            rows.append("zdravlje: " + (("%s" % ("ok", "upoz", "greska")[min(h[0], 2)])
                                         + ("" if not h[1] else " %d" % h[1]) if h else "-"))
            rows.append("%.1fHz %d tac" % (L.hz, L.points) if L.scanning else "stanje: " + L.state)
            n = L.nearest
            rows.append("najbl %dmm %d" % n if n else "najbl -")
            rows.append("losi B %d rst %d" % (L.bad, L.restarts))
        for j, t in enumerate(rows[:5]):
            fb.text(fit(t, 16), 0, HEAD + 1 + j * 9, 1)
        if L and L.nearest:                       # stepen posle ugla najbliže tačke
            ui.icon(fb, ui.ICON_DEG, 8 * min(16, len(rows[3])), HEAD + 1 + 3 * 9)
