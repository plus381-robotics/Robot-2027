# Stranice ekrana (registar, okret enkodera ide u krug): PROVERA, TAKTIKA, KORACI, ROBOT, VEZA,
# DNEVNIK, IZVESTAJ. Svaka stranica crta iz stanja app-a i zna svoju glavnu radnju (OK) i NAZAD.
# Stanje meča bira stranicu (app.show_page), a listanje radi uvek. Vidi ui.py za značenje kontrola.
import protocol as P
import state
import ui
import tekst as T
from ui import Screen, icon, box, text_right, text_center, fit, big, big_center, action_bar
from tactic import tracker

ICON_OK = (0x00, 0x02, 0x04, 0x88, 0x50, 0x20)           # kvačica
ICON_FAIL = (0x00, 0x88, 0x50, 0x20, 0x50, 0x88)         # iks
ICON_WARN = (0x20, 0x20, 0x20, 0x20, 0x00, 0x20)         # uzvičnik
ICON_WAIT = (0x00, 0x70, 0x88, 0xA8, 0x88, 0x70)         # sat (čeka)
ICON_NEXT = (0x00, 0x20, 0x10, 0xF8, 0x10, 0x20)         # strelica desno
MARK = {"ok": ICON_OK, "ne": ICON_FAIL, "upoz": ICON_WARN, "ceka": ICON_WAIT}

R1, R2, R3, R4 = ui.HEAD + 1, ui.HEAD + 13, ui.HEAD + 25, ui.HEAD + 37   # y četiri reda
RETURN_MS = 10000      # u meču: posle 10 s bez dodira nazad na stranicu stanja


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


def robot_tags(fb, x, y, r, s):
    if not r.alive:
        fb.text("nema veze", x, y, 1)
    elif not r.ok:
        fb.text(fit(T.version_msg(r.version, P.VERSION), 16 - x // 8), x, y, 1)
    else:
        tags(fb, x, y, [t for bit, t in T.TAGS if s["state"] & bit] or ["miruje"])


class Page:
    name = "?"
    live = True
    live_ms = ui.LIVE_MS

    def __init__(self, app):
        self.app = app

    def ok(self, u):
        pass

    def back(self, u):
        return True                     # na stranicama NAZAD ne radi ništa

    def title(self):
        return self.name

    def right(self):
        return None, False

    def draw(self, u, fb, r, s):
        pass


# ---------------- PROVERA: početni ekran sa opcijama ----------------

class Provera(Page):
    """Početni ekran: lista opcija (taktika, strana, provera, naoružaj, test). Okret enkodera
    pomera izbor; posle poslednjeg reda ide na sledeću stranicu, unazad se vraća na poslednji red."""
    name = "PROVERA"
    live_ms = 300

    def __init__(self, app):
        super().__init__(app)
        self.sel = self.top = 0

    def title(self):
        m = self.app.match
        if m.state == "RESET":
            return "RESET STM32"
        if m.waiting() or m.state == "POZA":
            return "NAORUZAN"
        if m.armed:
            return "MEC TRAJE"
        return "PROVERA"

    def right(self):
        ok = self.app.check()[0]
        return ("OK", False) if ok else ("NE", True)

    def rows(self):
        """[(natpis, vrednost, radnja)] za trenutno stanje."""
        a, m = self.app, self.app.match
        ok, items = a.check()
        bad = [i for i in items if i[0] == "ne"]
        summary = bad[0][1] if bad else ("OK" if ok else "upoz")    # NE je u naslovu
        side = a.st["sel_side"] or "-"
        rows = [("taktika", a.st["sel_tactic"] or "izaberi", self.do_tactic),
                ("strana", side, self.do_side),
                ("provera", summary, self.do_check)]
        if m.waiting():
            rows += [("simul. cinc", "", self.do_cord), ("otkazi", "drzi OK", self.do_cancel)]
        elif m.armed:
            rem = a.remaining()
            rows += [("mec traje", "%ds" % rem if rem is not None else "", lambda u: u.toast("zakljucano u mecu"))]
        else:
            rows += [("naoruzaj", "", self.do_arm), ("test odmah", "", self.do_test)]
        return rows

    def scroll(self, n):
        """Pomeri izbor; vraća koliko koraka "preliva" na susedne stranice (0 = ostali smo ovde)."""
        last = len(self.rows()) - 1
        s = self.sel + n
        if s > last:
            self.sel = last
            return s - last
        if s < 0:
            self.sel = 0
            return s
        self.sel = s
        if self.sel < self.top:
            self.top = self.sel
        elif self.sel >= self.top + 4:
            self.top = self.sel - 3
        return 0

    def enter_from_end(self):
        self.sel = len(self.rows()) - 1
        self.top = max(0, self.sel - 3)

    def ok(self, u):
        rows = self.rows()
        self.sel = min(self.sel, len(rows) - 1)
        rows[self.sel][2](u)

    def back(self, u):
        if self.app.match.waiting():            # L4: NAZAD ne otkazuje meč (lako se pritisne slučajno)
            u.toast("otkazi: drzi OK")
        return True

    # ---- radnje ----

    def locked(self, u):
        if self.app.match.armed:
            u.toast("zakljucano u mecu")
            return True
        return False

    def do_tactic(self, u):
        if not self.locked(u):
            u.push(self.app.tactics_menu())

    def do_side(self, u):
        if not self.locked(u):
            sides = ("plava", "zuta")
            cur = self.app.st["sel_side"]
            self.app.select(side=sides[(sides.index(cur) + 1) % 2] if cur in sides else sides[0])

    def do_check(self, u):
        items = self.app.check()[1]
        u.push(ui.Menu("Provera", [ui.Info("%s %s" % ({"ok": "+", "ne": "x", "upoz": "!", "ceka": "o"}[st], lb),
                                           (lambda v: lambda: v)(val)) for st, lb, val in items]))

    def do_arm(self, u):
        a = self.app
        if not a.st["sel_tactic"] or not a.st["sel_side"]:
            u.toast("izaberi taktiku")
        elif a.check()[0]:
            a.arm()
        else:
            u.toast("prvo popravi")

    def do_test(self, u):
        a = self.app
        name, side = a.st["sel_tactic"], a.st["sel_side"]
        if not name:
            return u.toast("izaberi taktiku")
        u.push(ui.Confirm("Test", ["%s %s" % (name, side or ""), "POKRECE MOTORE", "STOP prekida"],
                          lambda u2: a.start_tactic(name, side)))

    def do_cord(self, u):
        m = self.app.match
        u.push(ui.Confirm("Simul. cinc", ["Taktika krece!", "%s %s" % (m.tactic, T.SIDE.get(m.side, "")),
                                          "STOP prekida"], lambda u2: m.simulate_cord()))

    def do_cancel(self, u):
        m = self.app.match
        u.push(ui.Confirm("Otkazi mec", ["%s %s" % (m.tactic, T.SIDE.get(m.side, "")), "robot nece krenuti",
                                         "na cinc"], lambda u2: (m.cancel(), u2.toast("otkazano"))))

    def draw(self, u, fb, r, s):
        rows = self.rows()
        self.sel = min(self.sel, len(rows) - 1)
        for i in range(4):
            k = self.top + i
            if k >= len(rows):
                break
            label, val, _ = rows[k]
            y = ui.HEAD + 12 * i
            c = 1
            if k == self.sel:
                box(fb, 0, y, 124, 12, 1)
                c = 0
            fb.text(fit(label, 8 if val else 15), 4, y + 2, c)
            if val:
                text_right(fb, fit(val, 7), 121, y + 2, c)
        if len(rows) > 4:                           # klizač
            th = max(4, 48 * 4 // len(rows))
            fb.fill_rect(125, ui.HEAD + (48 - th) * self.top // (len(rows) - 4), 3, th, 1)


# ---------------- TAKTIKA: trenutni korak (u meču miran prikaz) ----------------

class Taktika(Page):
    name = "TAKTIKA"

    def calm(self):
        """Miran prikaz u meču (podešavanje 'ekran u mecu' = miran): krupno, crta se retko."""
        return self.app.match.state == "MEC" and self.app.st["screen_match"] == "miran"

    @property
    def live_ms(self):
        return 500 if self.calm() else ui.LIVE_MS

    def title(self):
        if self.calm():
            return "MEC"
        return "TAKTIKA"

    def draw(self, u, fb, r, s):
        t = tracker
        if self.calm():
            return self.draw_calm(fb, r, s)
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
            robot_tags(fb, 52, R4, r, s)
            return
        n = "%d/%d" % (t.idx, t.total) if t.total else str(t.idx)
        x = tags(fb, 0, R1, [n])
        fb.text(fit(t.step_name or "...", (ui.W - x) // 8), x + 1, R1, 1)
        el = t.elapsed()
        ts = T.secs(el) if not t.timeout_ms else "%s/%d" % (T.secs(el)[:-1], t.timeout_ms // 1000)
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
        icon(fb, ICON_NEXT, 0, R3 + 1)
        fb.text(fit(t.next or "-", 15), 9, R3, 1)
        last = t.last
        if last:
            idx, name, ok, reason, dur = last
            icon(fb, ICON_OK if ok else ICON_FAIL, 0, R4 + 1)
            d = T.secs(dur)
            if ok:
                fb.text(fit(name, (ui.W - 9 - 8 * len(d) - 4) // 8), 9, R4, 1)
            else:
                tags(fb, 9, R4, [T.reason(reason)])
            text_right(fb, d, ui.W, R4, 1)

    def draw_calm(self, fb, r, s):
        t = tracker
        left = self.app.remaining()
        big(fb, "%d" % left if left is not None else "--", 0, R1 + 1, 3)
        n = "%d/%d" % (t.idx, t.total) if t.total else "%d" % t.idx
        big(fb, n, ui.W - 16 * len(n), R1 + 5, 2)
        if s and s["state"] & P.State.MOVING:
            word = "VOZI"
        elif t.step_name:
            word = "CEKA"
        else:
            word = "GOTOVO" if t.last and t.last[2] else "STOP"
        tags(fb, 0, R4 - 4, [word])
        fb.text(fit(t.step_name or "", 10), 8 * len(word) + 6, R4 - 4, 1)


# ---------------- KORACI, ROBOT, VEZA ----------------

class Koraci(Page):
    name = "KORACI"

    def draw(self, u, fb, r, s):
        h = tracker.history[-4:]
        if not h:
            text_center(fb, "jos nema koraka", R2 + 6)
            return
        for i, (idx, name, ok, reason, dur) in enumerate(h):
            y = R1 + 12 * i
            icon(fb, ICON_OK if ok else ICON_FAIL, 0, y + 1)
            d = T.secs(dur)
            text_right(fb, d, ui.W, y, 1)
            label = name if ok else "%s %s" % (name.split()[0], T.reason(reason))
            fb.text(fit(label, (ui.W - 9 - 8 * len(d) - 3) // 8), 9, y, 1)


class Robot(Page):
    name = "ROBOT"

    def draw(self, u, fb, r, s):
        fb.text("x", 0, R1, 1)
        fb.text("y", 66, R1, 1)
        icon(fb, ui.ICON_THETA, 0, R2)
        fb.text("v", 66, R2, 1)
        fb.vline(62, R1, 20, 1)
        age = r.status_age()
        fresh = s and age is not None and age < 500           # zastareo podatak se ne prikazuje kao svež
        if fresh:
            text_right(fb, str(s["x"]), 58, R1)
            text_right(fb, str(s["y"]), ui.W, R1)
            text_right(fb, "%.1f" % (s["theta"] / 100), 54, R2)
            icon(fb, ui.ICON_DEG, 55, R2)
            text_right(fb, str(s["v"]), ui.W, R2)
        else:
            for x in (58, ui.W):
                text_right(fb, "--", x, R1)
                text_right(fb, "--", x, R2)
        robot_tags(fb, 0, R3 + 2, r, s)
        fb.text("STATUS", 0, R4 + 2, 1)
        text_right(fb, "-" if age is None or not r.alive else "%dms" % age, ui.W, R4 + 2, 1)


class Veza(Page):
    name = "VEZA"

    def draw(self, u, fb, r, s):
        fb.text("STM32", 0, R1, 1)
        text_right(fb, ("OK v%d" % r.version) if r.ok else ("v%s?" % r.version if r.alive else "nema"), ui.W, R1)
        fb.text("%d/s" % r.fps, 0, R2, 1)
        text_right(fb, "CRC%d pon%d" % (r.parser.errors, r.retries), ui.W, R2)
        lp = self.app.loop                 # najduži krug petlje i najduža pauza PING-a
        fb.text("krug %d" % (lp.step_max if lp else 0), 0, R3, 1)
        text_right(fb, "PING %d" % r.ping_gap, ui.W, R3)
        if not state.MODE:
            ip = "WiFi %s..." % (state.SSID or "")
        else:
            ip = state.IP if state.MODE == "STA" else "AP " + state.IP
        fb.text(fit(ip, 16), 0, R4 + 2, 1)


# ---------------- DNEVNIK: greške i poruke ----------------

class Dnevnik(Page):
    name = "DNEVNIK"
    live_ms = 500

    def right(self):
        n = len(self.app.errors)
        return ("%d gr" % n if n else None), False

    def draw(self, u, fb, r, s):
        a = self.app
        a.errors_seen()                     # pogledano: ! nestaje iz trake
        rows = [("ne", "t+%ds %s" % (t // 1000, txt)) for t, txt in a.errors[-4:]][::-1]
        if len(rows) < 4:
            rows += [(None, l) for l in a.log[-(4 - len(rows)):][::-1]]
        if not rows:
            text_center(fb, "prazno", R2 + 6)
        for i, (mark, txt) in enumerate(rows[:4]):
            y = R1 + 12 * i
            if mark:
                icon(fb, ICON_FAIL, 0, y + 1)
            fb.text(fit(txt, 15), 9, y, 1)


# ---------------- IZVESTAJ: posle meča (ili testa) ----------------

class Izvestaj(Page):
    name = "IZVESTAJ"
    live = False
    VIEWS = 3

    def __init__(self, app):
        super().__init__(app)
        self.view = 0

    def right(self):
        return ("%d/%d" % (self.view + 1, self.VIEWS) if self.app.report else None), False

    def ok(self, u):
        self.view = (self.view + 1) % self.VIEWS

    def back(self, u):
        self.view = 0
        return True

    def draw(self, u, fb, r, s):
        rp = self.app.report
        if not rp:
            text_center(fb, "jos nema meca", R2 + 6)
            return
        if self.view == 0:
            word = ("MEC GOTOV" if rp.get("match_end") else "GOTOVO") if rp["ok"] else "PAO"
            big(fb, word, 0, R1, 2)
            text_right(fb, "%d/%d" % (rp["done"], rp["total"] or rp["steps"]), ui.W, R1 + 4, 1)
            fb.text(fit("%s %s %s" % (T.secs(rp["ms"]), rp["name"], T.SIDE.get(rp["side"], "")), 16), 0, R3 - 4, 1)
            if rp.get("fail"):
                fb.text(fit("%d %s" % (rp["fail"][0], rp["fail"][1]), 16), 0, R4 - 6, 1)
                fb.text(fit(T.reason(rp["fail"][2]), 16), 0, R4 + 3, 1)
        elif self.view == 1:
            for i, (idx, name, ok, reason, dur) in enumerate(rp["steps_list"][-4:]):
                y = R1 + 12 * i
                icon(fb, ICON_OK if ok else ICON_FAIL, 0, y + 1)
                d = T.secs(dur)
                text_right(fb, d, ui.W, y, 1)
                fb.text(fit(name if ok else T.reason(reason), (ui.W - 9 - 8 * len(d) - 3) // 8), 9, y, 1)
        else:
            l = rp["link"]
            fb.text("CRC %d pon %d" % (l["crc"], l["retries"]), 0, R1, 1)
            fb.text("bez odg %d" % l["noreply"], 0, R2, 1)
            fb.text("PING max %dms" % l["ping_max"], 0, R3, 1)
            p = rp.get("pose")
            fb.text(fit("kraj %s" % ("%d,%d %d" % tuple(p) if p else "-"), 16), 0, R4, 1)


PAGES = (Provera, Taktika, Koraci, Robot, Veza, Dnevnik, Izvestaj)


class Pages(Screen):
    """Krug stranica; OK i NAZAD idu trenutnoj stranici."""
    live = True

    def __init__(self, app):
        self.app = app
        self.list = [P_(app) for P_ in PAGES]
        self.NAMES = tuple(p.name for p in self.list)
        self.page = 0
        self.t_touch = 0

    @property
    def cur(self):
        return self.list[self.page]

    @property
    def live_ms(self):
        return self.cur.live_ms

    def show(self, name):
        for i, p in enumerate(self.list):
            if p.name == name:
                self.page = i

    def rotate(self, u, n):
        """Na početnom ekranu okret prvo pomera izbor opcije; posle poslednje ide na sledeću stranicu."""
        self.t_touch = ui.ticks_ms()
        home = self.list[0]
        if self.page == 0:
            n = home.scroll(n)
            if not n:
                return
            n = 1 if n > 0 else -1
        new = (self.page + n) % len(self.list)
        if new == 0 and n < 0:
            home.enter_from_end()                    # unazad na početni: poslednja opcija
        elif new == 0:
            home.sel = home.top = 0
        self.page = new

    def ok(self, u):
        self.t_touch = ui.ticks_ms()
        self.cur.ok(u)

    def back(self, u):
        self.t_touch = ui.ticks_ms()
        return self.cur.back(u)

    def draw(self, u, fb):
        r = self.app.robot
        s = r.status if r.alive else None
        p = self.cur
        right, alert = p.right()
        a = self.app
        if a.match.state == "MEC":                  # preostalo vreme meča
            left = a.remaining()
            if left is not None and not (isinstance(p, Taktika) and p.calm()):
                right, alert = "%ds" % left, left <= 10
        elif a.st["sel_tactic"] and right is None:
            right = fit("%s %s" % (a.st["sel_tactic"], T.SIDE.get(a.st["sel_side"], "")), 9)
        if tracker.demo and not a.match.armed and right is None:
            right = "DEMO"
        u.header(fb, p.title(), right, (self.page, len(self.list)), alert)
        p.draw(u, fb, r, s)
