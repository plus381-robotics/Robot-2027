# Ekran na robotu: telemetrija i tok taktike. Robotom se odavde ne upravlja (osim taster STOP).
#
# Stranice (okret enkodera): TAKTIKA, KORACI, ROBOT, VEZA.
# Kad taktika krene, ekran sam prelazi na TAKTIKA.
# Dugi klik enkodera (ili NAZAD): podešavanja ekrana. Običan klik ne radi ništa (slučajan dodir).
import gc
import config as cfg
import protocol as P
import state
import ui
from ui import Menu, Toggle, Number, Choice, Info, Action, Screen, icon, box, text_right, text_center, fit
from tactic import tracker, Demo

TAGS = ((P.State.MOVING, "VOZI"), (P.State.BLOCKED, "BLOK"),
        (P.State.MATCH_RUNNING, "MEC"), (P.State.MATCH_OVER, "KRAJ"), (P.State.LINK_LOST, "VEZA!"))
SHORT = {"SET_POSE": "POZA", "ROTATE": "OKRET", "MOVE": "PRAVO", "MATCH_START": "START"}
REASON = {"INVALID": "odbijeno", "BLOCKED": "prepreka", "TIMEOUT": "isteklo",
          "PREEMPTED": "prekinuto", "MATCH_OVER": "kraj meca", "STOPPED": "stop"}

ICON_OK = (0x00, 0x02, 0x04, 0x88, 0x50, 0x20)           # kvačica
ICON_FAIL = (0x00, 0x88, 0x50, 0x20, 0x50, 0x88)         # iks
ICON_NEXT = (0x00, 0x20, 0x10, 0xF8, 0x10, 0x20)         # strelica desno

R1, R2, R3, R4 = ui.HEAD + 1, ui.HEAD + 13, ui.HEAD + 25, ui.HEAD + 37   # y četiri reda


def secs(ms):
    return "%.1fs" % (ms / 1000) if ms < 100000 else "%ds" % (ms // 1000)


def tags(fb, x, y, words):
    """Reči kao male inverzne etikete; vraća x posle poslednje."""
    for t in words:
        w = 8 * len(t) + 3
        if x + w > ui.W:
            break
        box(fb, x, y - 1, w, 10, 1)
        fb.text(t, x + 2, y, 0)
        x += w + 2
    return x


class Pages(Screen):
    live = True
    NAMES = ("TAKTIKA", "KORACI", "ROBOT", "VEZA")

    def __init__(self, app):
        self.app = app
        self.page = 0

    def rotate(self, u, n):
        self.page = (self.page + n) % len(self.NAMES)

    def back(self, u):
        u.push(self.app.settings_menu())
        return True

    def draw(self, u, fb):
        r = self.app.robot
        s = r.status if r.alive else None
        right, alert = None, False
        if s and s["state"] & P.State.MATCH_RUNNING:
            left = max(0, 100 - s["match_ms"] // 1000)
            right, alert = "%ds" % left, left <= 10
        elif tracker.demo:
            right = "DEMO"
        u.header(fb, self.NAMES[self.page], right, (self.page, len(self.NAMES)), alert)
        getattr(self, "p_" + self.NAMES[self.page].lower())(u, fb, r, s)

    # ---------------- TAKTIKA: trenutni korak ----------------

    def p_taktika(self, u, fb, r, s):
        t = tracker
        if not t.running:
            fb.text("nema taktike", 0, R1, 1)
            last = t.last
            if last:
                icon(fb, ICON_OK if last[2] else ICON_FAIL, 0, R2 + 1)
                fb.text(fit(last[1], 15), 9, R2, 1)
            if s:                                     # kratko: x,y ugao
                p = fit("%d,%d %d" % (s["x"], s["y"], round(s["theta"] / 100)), 15)
                fb.text(p, 0, R3, 1)
                icon(fb, ui.ICON_DEG, 8 * len(p) + 1, R3)
            fb.text("robot:", 0, R4, 1)
            self.robot_tags(fb, 52, R4, r, s)
            return
        # red 1: "3/12" kao etiketa + ime koraka
        n = "%d/%d" % (t.idx, t.total) if t.total else str(t.idx)
        x = tags(fb, 0, R1, [n])
        fb.text(fit(t.step_name or "...", (ui.W - x) // 8), x + 1, R1, 1)
        # red 2: traka trajanja koraka u odnosu na timeout
        el = t.elapsed()
        ts = secs(el) if not t.timeout_ms else "%s/%d" % (secs(el)[:-1], t.timeout_ms // 1000)
        bw = ui.W - 8 * len(ts) - 3
        ui.frame(fb, 0, R2, bw, 9, 1)
        if t.timeout_ms:
            p = min(el, t.timeout_ms) * (bw - 4) // t.timeout_ms
            if el <= t.timeout_ms or (ui.ticks_ms() // 250) % 2:   # preko vremena: trepće
                fb.fill_rect(2, R2 + 2, p, 5, 1)
        elif t.step_name:                                 # bez timeout-a: samo "živi" pokazivač
            k = (ui.ticks_ms() // 60) % (bw - 8)
            fb.fill_rect(2 + k, R2 + 2, 4, 5, 1)
        text_right(fb, ts, ui.W, R2 + 1, 1)
        # red 3: sledeći korak
        icon(fb, ICON_NEXT, 0, R3 + 1)
        fb.text(fit(t.next or "-", 15), 9, R3, 1)
        # red 4: prethodni korak
        last = t.last
        if last:
            idx, name, ok, reason, dur = last
            icon(fb, ICON_OK if ok else ICON_FAIL, 0, R4 + 1)
            d = secs(dur)
            if ok:
                fb.text(fit(name, (ui.W - 9 - 8 * len(d) - 4) // 8), 9, R4, 1)
            else:
                tags(fb, 9, R4, [REASON.get(reason, str(reason))])
            text_right(fb, d, ui.W, R4, 1)

    # ---------------- KORACI: istorija ----------------

    def p_koraci(self, u, fb, r, s):
        h = tracker.history[-4:]
        if not h:
            text_center(fb, "jos nema koraka", R2 + 6)
            return
        for i, (idx, name, ok, reason, dur) in enumerate(h):
            y = R1 + 12 * i
            icon(fb, ICON_OK if ok else ICON_FAIL, 0, y + 1)
            d = secs(dur)
            text_right(fb, d, ui.W, y, 1)
            label = name if ok else "%s %s" % (name.split()[0], REASON.get(reason, str(reason)))
            fb.text(fit(label, (ui.W - 9 - 8 * len(d) - 3) // 8), 9, y, 1)

    # ---------------- ROBOT: pozicija i stanje ----------------

    def p_robot(self, u, fb, r, s):
        fb.text("x", 0, R1, 1)
        fb.text("y", 66, R1, 1)
        icon(fb, ui.ICON_THETA, 0, R2)
        fb.text("v", 66, R2, 1)
        fb.vline(62, R1, 20, 1)
        if s:
            text_right(fb, str(s["x"]), 58, R1)
            text_right(fb, str(s["y"]), ui.W, R1)
            text_right(fb, "%.1f" % (s["theta"] / 100), 54, R2)
            icon(fb, ui.ICON_DEG, 55, R2)
            text_right(fb, str(s["v"]), ui.W, R2)
        else:
            for x in (58, ui.W):
                text_right(fb, "-", x, R1)
                text_right(fb, "-", x, R2)
        self.robot_tags(fb, 0, R3 + 2, r, s)
        age = r.status_age()
        fb.text("STATUS", 0, R4 + 2, 1)
        text_right(fb, "-" if age is None or not r.alive else "%dms" % age, ui.W, R4 + 2, 1)

    def robot_tags(self, fb, x, y, r, s):
        if not r.alive:
            fb.text("nema veze", x, y, 1)
        elif r.version != P.VERSION:
            fb.text("verzija N%s" % r.version, x, y, 1)
        else:
            tags(fb, x, y, [t for bit, t in TAGS if s["state"] & bit] or ["miruje"])

    # ---------------- VEZA: STM32 i WiFi ----------------

    def p_veza(self, u, fb, r, s):
        fb.text("STM32", 0, R1, 1)
        text_right(fb, ("OK v%d" % r.version) if r.ok else ("v%s?" % r.version if r.alive else "nema"), ui.W, R1)
        fb.text("%d/s" % r.fps, 0, R2, 1)
        text_right(fb, "CRC %d" % r.parser.errors, ui.W, R2)
        fb.text("pon %d" % r.retries, 0, R3, 1)
        text_right(fb, "bez odg %d" % r.noreply, ui.W, R3)
        if not state.MODE:
            ip = "WiFi %s..." % (state.SSID or "")
        else:
            ip = state.IP if state.MODE == "STA" else "AP " + state.IP
        fb.text(fit(ip, 16), 0, R4 + 2, 1)


class App:
    def __init__(self, robot, settings, fb):
        self.robot, self.st, self.fb = robot, settings, fb
        self._pose_sent = False
        self._seen_start = None
        self.events = []                   # događaji iz poslednjeg robot.poll() (za tac.py)
        self.abort = None                  # razlog prekida taktike (STOP)
        self.request = None                # ime taktike koju treba pokrenuti
        self.running = None                # ime taktike koja radi
        self.log = []                      # dnevnik taktike (tools/tactic.py ga čita preko WiFi-ja)
        self.log_n = 0                     # ukupno redova ikad (za čitanje od mesta)
        self.pump = None                   # jedan krug glavne petlje (postavlja main.py)
        self.demo = Demo(tracker)
        tracker.demo = self.st["demo"]
        self.pages = Pages(self)
        self.ui = ui.UI(fb, self.pages, self.indicators, lambda: self.st["sleep_s"])
        self.apply_display()

    # ---------------- ekran ----------------

    def apply_display(self, contrast=None):
        if not self.fb:
            return
        self.fb.contrast(self.st["contrast"] if contrast is None else contrast)
        f = 1 if self.st["flip"] else 0
        if hasattr(self.fb, "rotate"):
            self.fb.rotate(f)
        else:                              # stariji ssd1306 drajver
            self.fb.write_cmd(0xC0 | (f << 3))
            self.fb.write_cmd(0xA0 | f)

    def indicators(self):
        out = [(ui.ICON_AP, False) if state.MODE == "AP" else (ui.ICON_WIFI, not state.MODE)]  # trepće dok se povezuje
        out.append((ui.ICON_LINK, False) if self.robot.ok else (ui.ICON_NOLINK, True))
        return out

    # ---------------- glavna petlja ----------------

    def update(self):
        r = self.robot
        self.events = r.poll()
        for seq, label, kind, reason in self.events:
            name = SHORT.get(label, label)
            if kind == "fail":
                self.ui.toast("%s: %s" % (name, REASON.get(reason, reason)), 2500, alert=True)
            elif kind == "timeout":
                self.ui.toast("%s: nema odg." % name, 2500, alert=True)
        if r.ok and not self._pose_sent:
            self._pose_sent = True
            if self.st["start_pose"]:
                x, y, th = cfg.START_POSE
                r.send("SET_POSE", x=x, y=y, theta=th * 100)
        if tracker.demo and not self.running:
            self.demo.update()
        if tracker.running and tracker.t_start != self._seen_start:   # nova taktika: prikaži je
            self._seen_start = tracker.t_start
            self.pages.page = 0
            self.ui.home()
            self.ui.wake()

    def stop(self):
        """Taster STOP: radi uvek, i bez veze i dok je ekran ugašen."""
        self.robot.send("STOP")
        if self.running:
            self.abort = "STOP"
        self.ui.wake()
        self.ui.toast("STOP", 1500, alert=True)

    def tlog(self, text):
        print("[taktika]", text)
        self.log = (self.log + [text])[-40:]
        self.log_n += 1

    def tactics(self):
        import os
        try:
            return sorted(f[:-3] for f in os.listdir("/tactics") if f.endswith(".py"))
        except OSError:
            return []

    def tactics_menu(self):
        items = [Action(n, (lambda n: lambda u: setattr(self, "request", n))(n),
                        ["Taktika: " + n, "POKRECE MOTORE", "STOP taster prekida"]) for n in self.tactics()]
        return Menu("Taktike", items or [Info("nema", lambda: "-")])

    # ---------------- podešavanja ----------------

    def set_demo(self, v):
        self.st.set("demo", v)
        tracker.demo = v
        if not v and tracker.name == "DEMO":
            tracker.finish()
            tracker.history = []

    def settings_menu(self):
        st = self.st
        def flip(v):
            st.set("flip", v)
            self.apply_display()
        return Menu("Meni", [
            ui.Sub("Taktike", self.tactics_menu),
            Number("kontrast", lambda: st["contrast"], lambda v: (st.set("contrast", v), self.apply_display()),
                   0, 255, 15, preview=lambda v: self.apply_display(v)),
            Toggle("okreni 180", lambda: st["flip"], flip),
            Toggle("obrni enk.", lambda: st["enc_rev"], lambda v: st.set("enc_rev", v)),
            Choice("spavanje", [(0, "nikad"), (60, "1min"), (300, "5min")],
                   lambda: st["sleep_s"], lambda v: st.set("sleep_s", v)),
            Toggle("auto poza", lambda: st["start_pose"], lambda v: st.set("start_pose", v)),
            Toggle("demo takt.", lambda: st["demo"], self.set_demo),
            Info("RAM", lambda: "%dk" % (gc.mem_free() // 1024) if hasattr(gc, "mem_free") else "-"),
            Info("radi", lambda: "%dmin" % (ui.ticks_ms() // 60000)),
        ])
