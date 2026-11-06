# Ekrani i meni za robota. ui.py crta i vodi navigaciju, robot.py priča sa STM32.
import math
import gc
import config as cfg
import protocol as P
import state
import ui
from ui import Menu, Sub, Action, Toggle, Number, Choice, Info, Screen, icon, box, text_right, text_center

TAGS = ((P.State.MOVING, "VOZI"), (P.State.BLOCKED, "BLOK"),
        (P.State.MATCH_RUNNING, "MEC"), (P.State.MATCH_OVER, "KRAJ"), (P.State.LINK_LOST, "VEZA"))
RESULT = {"ok": "OK", "done": "gotovo", "timeout": "nema odg."}
# kraća imena za poruke na dnu ekrana (staje 16 znakova)
SHORT = {"SET_POSE": "POZA", "ROTATE": "OKRET", "MOVE": "PRAVO", "MATCH_START": "START"}
REASON = {"INVALID": "odbijeno", "BLOCKED": "prepreka", "TIMEOUT": "isteklo",
          "PREEMPTED": "prekinuto", "MATCH_OVER": "kraj meca", "STOPPED": "stop"}


def deg(cdeg):
    return "%.1f" % (cdeg / 100)


class Dashboard(Screen):
    """Početni ekran: pozicija, ugao (kompas), brzina, stanje. OK otvara meni."""
    live = True

    def __init__(self, app):
        self.app = app

    def ok(self, ui_):
        ui_.push(self.app.main_menu())

    def rotate(self, ui_, n):
        ui_.push(self.app.main_menu())

    def draw(self, u, fb):
        r = self.app.robot
        s = r.status if r.alive else None
        title = cfg.HOSTNAME.upper()
        if s and s["state"] & P.State.MATCH_RUNNING:
            title = "MEC %3ds" % max(0, 100 - s["match_ms"] // 1000)
        u.header(fb, title)
        y0 = ui.HEAD + 3
        fb.text("x", 2, y0, 1)
        fb.text("y", 2, y0 + 10, 1)
        icon(fb, ui.ICON_THETA, 2, y0 + 20)
        fb.text("v", 2, y0 + 30, 1)
        if s:
            text_right(fb, str(s["x"]), 70, y0)
            text_right(fb, str(s["y"]), 70, y0 + 10)
            text_right(fb, deg(s["theta"]), 66, y0 + 20)
            icon(fb, ui.ICON_DEG, 67, y0 + 20)
            text_right(fb, str(s["v"]), 70, y0 + 30)
        else:
            for i in range(4):
                text_right(fb, "-", 70, y0 + 10 * i)
        fb.vline(76, ui.HEAD + 2, 40, 1)
        self.compass(fb, 102, 34, 20, s["theta"] if s else None)
        # dno: stanje kao "etikete"
        y = 54
        if not r.alive:
            text_center(fb, "cekam STM32" + "." * ((ui.ticks_ms() // 400) % 4), y + 1)
        elif r.version != P.VERSION:
            text_center(fb, "verzija N%s/E%d" % (r.version, P.VERSION), y + 1)
        else:
            x = 1
            tags = [t for bit, t in TAGS if s["state"] & bit]
            if r.busy and "VOZI" not in tags:
                tags.insert(0, r.busy)
            for t in tags or ["spreman"]:
                w = 8 * len(t) + 4
                if x + w > 128:
                    break
                box(fb, x, y, w, 10, 1)
                fb.text(t, x + 2, y + 1, 0)
                x += w + 3

    def compass(self, fb, cx, cy, rad, theta):
        fb.ellipse(cx, cy, rad, rad, 1)
        for a in range(0, 360, 45):          # crtice na svakih 45°, duže na 90°
            ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
            k = 4 if a % 90 == 0 else 2
            fb.line(int(cx + ca * (rad - k)), int(cy - sa * (rad - k)),
                    int(cx + ca * rad), int(cy - sa * rad), 1)
        if theta is None:
            fb.text("?", cx - 3, cy - 3, 1)
            return
        a = math.radians(theta / 100)
        ca, sa = math.cos(a), math.sin(a)
        tip = (int(cx + ca * (rad - 3)), int(cy - sa * (rad - 3)))
        bl = (int(cx - ca * 6 + sa * 6), int(cy + sa * 6 + ca * 6))
        br = (int(cx - ca * 6 - sa * 6), int(cy + sa * 6 - ca * 6))
        fb.line(tip[0], tip[1], bl[0], bl[1], 1)       # strelica: smer robota
        fb.line(tip[0], tip[1], br[0], br[1], 1)
        fb.line(bl[0], bl[1], cx, cy, 1)
        fb.line(br[0], br[1], cx, cy, 1)
        fb.line(tip[0], tip[1], cx, cy, 1)


class App:
    def __init__(self, robot, settings, fb):
        self.robot, self.st, self.fb = robot, settings, fb
        # parametri za probne komande (ne pamte se posle restarta)
        x, y, th = cfg.START_POSE
        self.goto = {"x": x, "y": y, "theta": th, "speed": 500, "reverse": False, "no_theta": True}
        self.rot = 0
        self.move = {"dist": 200, "speed": 300}
        self.pose = {"x": x, "y": y, "theta": th}
        self.debug_mask = 0
        self._pose_sent = False
        self.ui = ui.UI(fb, Dashboard(self), self.indicators, lambda: self.st["sleep_s"])
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
        r = self.robot
        out = []
        if state.MODE:
            out.append((ui.ICON_WIFI if state.MODE == "STA" else ui.ICON_AP, False))
        out.append((ui.ICON_LINK, False) if r.ok else (ui.ICON_NOLINK, True))
        return out

    # ---------------- glavna petlja ----------------

    def update(self):
        r = self.robot
        for label, kind, reason in r.poll():
            if kind == "ok" and label == "DEBUG_STREAMS":
                continue
            name = SHORT.get(label, label)
            if kind == "fail":
                self.ui.toast("%s: %s" % (name, REASON.get(reason, reason)), 2500, alert=True)
            elif kind == "timeout":
                self.ui.toast("%s: %s" % (name, RESULT[kind]), 2500, alert=True)
            else:
                self.ui.toast("%s %s" % (name, RESULT[kind]))
        if r.ok and not self._pose_sent:
            self._pose_sent = True
            if self.st["start_pose"]:
                x, y, th = cfg.START_POSE
                r.send("SET_POSE", x=x, y=y, theta=th * 100)

    def stop(self):
        """Taster STOP: radi uvek, i bez veze i dok je ekran ugašen."""
        self.robot.send("STOP")
        self.ui.wake()
        self.ui.toast("STOP", 1500, alert=True)

    # ---------------- komande ----------------

    def cmd(self, name, **f):
        if not self.robot.ok:
            self.ui.toast("STM32 nije tu", 2000, alert=True)
            return
        self.robot.send(name, **f)

    def do_goto(self, u):
        g = self.goto
        flags = (P.GotoFlags.REVERSE if g["reverse"] else 0) | (P.GotoFlags.NO_THETA if g["no_theta"] else 0)
        self.cmd("GOTO", x=g["x"], y=g["y"], theta=g["theta"] * 100, flags=flags, max_speed=g["speed"])

    def do_rotate(self, u):
        self.cmd("ROTATE", theta=self.rot * 100)

    def do_move(self, u):
        self.cmd("MOVE", dist=self.move["dist"], max_speed=self.move["speed"])

    def do_set_pose(self, u):
        p = self.pose
        self.cmd("SET_POSE", x=p["x"], y=p["y"], theta=p["theta"] * 100)

    def take_pose(self, u):
        s = self.robot.status
        if not (self.robot.alive and s):
            u.toast("nema STATUS-a", alert=True)
            return
        self.pose.update(x=s["x"], y=s["y"], theta=round(s["theta"] / 100))
        u.toast("preuzeto")

    def set_debug(self, bit, on):
        self.debug_mask = (self.debug_mask | bit) if on else (self.debug_mask & ~bit)
        self.cmd("DEBUG_STREAMS", mask=self.debug_mask)

    # ---------------- meni ----------------

    @staticmethod
    def num(d, key, label, lo, hi, step, unit=""):
        return Number(label, lambda: d[key], lambda v: d.__setitem__(key, v), lo, hi, step, unit)

    @staticmethod
    def tog(d, key, label):
        return Toggle(label, lambda: d[key], lambda v: d.__setitem__(key, v))

    def main_menu(self):
        return Menu("Meni", [
            Sub("Kretanje", self.motion_menu),
            Sub("Pozicija", self.pose_menu),
            Sub("Mec", self.match_menu),
            Sub("Debug", self.debug_menu),
            Sub("Veza STM32", self.link_menu),
            Sub("WiFi", self.wifi_menu),
            Sub("Podesavanja", self.settings_menu),
            Sub("O uredjaju", self.about_menu),
        ])

    def motion_menu(self):
        g, m = self.goto, self.move
        busy = lambda: "%s traje" % self.robot.busy if self.robot.busy else "robot stoji"
        return Menu("Kretanje", [
            Action("STOP", lambda u: self.stop()),
            Sub("Idi na x,y", lambda: Menu("GOTO", [
                self.num(g, "x", "x", -3000, 3000, 10, "mm"),
                self.num(g, "y", "y", -3000, 3000, 10, "mm"),
                self.num(g, "theta", "ugao", -180, 180, 5),
                self.tog(g, "no_theta", "bez ugla"),
                self.tog(g, "reverse", "unazad"),
                self.num(g, "speed", "brzina", 50, 1500, 50),
                Action("Kreni", self.do_goto, [
                    lambda: "x=%d y=%d" % (g["x"], g["y"]),
                    lambda: ("bez ugla" if g["no_theta"] else "ugao %d" % g["theta"]) + (" unazad" if g["reverse"] else ""),
                    busy]),
            ])),
            Sub("Okreni se", lambda: Menu("ROTATE", [
                Number("ugao", lambda: self.rot, lambda v: setattr(self, "rot", v), -180, 180, 5),
                Action("Kreni", self.do_rotate, [lambda: "na %d stepeni" % self.rot, busy]),
            ])),
            Sub("Pravo", lambda: Menu("MOVE", [
                self.num(m, "dist", "duzina", -2000, 2000, 10, "mm"),
                self.num(m, "speed", "brzina", 50, 1500, 50),
                Action("Kreni", self.do_move, [lambda: "%d mm" % m["dist"], busy]),
            ])),
        ])

    def pose_menu(self):
        p = self.pose
        return Menu("Pozicija", [
            Info("sada", lambda: "%d,%d" % (self.robot.status["x"], self.robot.status["y"])
                 if self.robot.alive and self.robot.status else "-"),
            self.num(p, "x", "x", -3000, 3000, 10, "mm"),
            self.num(p, "y", "y", -3000, 3000, 10, "mm"),
            self.num(p, "theta", "ugao", -180, 180, 5),
            Action("Uzmi sadasnju", self.take_pose),
            Action("Postavi", lambda u: self.do_set_pose(u)),
        ])

    def match_menu(self):
        s = lambda: self.robot.status if self.robot.alive else None
        return Menu("Mec", [
            Info("stanje", lambda: ("traje" if s()["state"] & P.State.MATCH_RUNNING else "ne traje") if s() else "-"),
            Info("vreme", lambda: "%.1fs" % (s()["match_ms"] / 1000) if s() else "-"),
            Action("Start meca", lambda u: self.cmd("MATCH_START"),
                   ["Pocinje 100 s.", "Posle toga robot", "ne prima komande."]),
        ])

    def debug_menu(self):
        return Menu("Debug", [
            Toggle("lidar", lambda: bool(self.debug_mask & P.Debug.LIDAR),
                   lambda v: self.set_debug(P.Debug.LIDAR, v)),
            Toggle("regulacija", lambda: bool(self.debug_mask & P.Debug.CONTROL),
                   lambda v: self.set_debug(P.Debug.CONTROL, v)),
        ])

    def link_menu(self):
        r = self.robot
        return Menu("Veza", [
            Info("STM32", lambda: ("OK v%d" % r.version) if r.ok else ("v%s?" % r.version if r.alive else "nema")),
            Info("okviri", lambda: r.frames),
            Info("greske", lambda: r.parser.errors),
            Info("ponovljeno", lambda: r.retries),
            Info("bez odg.", lambda: r.noreply),
            Info("LOG", lambda: r.logs[-1] if r.logs else "-"),
        ])

    def wifi_menu(self):
        return Menu("WiFi", [
            Info("mod", lambda: state.MODE or "-"),
            Info("mreza", lambda: state.SSID or "-"),
            Info("IP", lambda: state.IP or "-"),
            Info("ime", lambda: cfg.HOSTNAME + ".local"),
        ])

    def settings_menu(self):
        st = self.st
        def flip(v):
            st.set("flip", v)
            self.apply_display()
        return Menu("Podesavanja", [
            Number("kontrast", lambda: st["contrast"], lambda v: (st.set("contrast", v), self.apply_display()),
                   0, 255, 15, preview=lambda v: self.apply_display(v)),
            Toggle("okreni ekran", lambda: st["flip"], flip),
            Toggle("obrni smer", lambda: st["enc_rev"], lambda v: st.set("enc_rev", v)),
            Choice("spavanje", [(0, "nikad"), (30, "30s"), (60, "1min"), (300, "5min")],
                   lambda: st["sleep_s"], lambda v: st.set("sleep_s", v)),
            Toggle("auto poza", lambda: st["start_pose"], lambda v: st.set("start_pose", v)),
        ])

    def about_menu(self):
        return Menu("O uredjaju", [
            Info("protokol", lambda: "v%d" % P.VERSION),
            Info("ploca", lambda: cfg.BOARD),
            Info("RAM", lambda: "%dk" % (gc.mem_free() // 1024) if hasattr(gc, "mem_free") else "-"),
            Info("radi", lambda: "%dmin" % (ui.ticks_ms() // 60000)),
        ])
