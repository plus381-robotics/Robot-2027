# Ekran na robotu: telemetrija, provera spremnosti, tok meča i izveštaj. Robotom se odavde ne upravlja
# (osim taster STOP).
#
# App povezuje delove: robot (veza sa STM32), pages (stranice), match (tok meča), meni.
# Stanje bira stranicu: PROVERA pred start, TAKTIKA kad taktika krene, IZVESTAJ posle.
# Dugi NAZAD: meni (zaključan od NAORUZAN do kraja meča). Kontrole: vidi ui.py.
import gc
import os
import config as cfg
import protocol as P
import state
import ui
import tekst as T
from compat import ticks_ms, ticks_diff
from ui import Menu, Toggle, Number, Choice, Info, Action
import tactic
from tactic import tracker, Demo
from pages import Pages, RETURN_MS
from match import Match
import tac

MEC_DIR = "/mec"        # sačuvani izveštaji (poslednjih MEC_KEEP)
MEC_KEEP = 20
ICON_BANG = (0x60, 0x60, 0x60, 0x60, 0x00, 0x60)    # ! (nepregledane greške)


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
        self.errors = []                   # (ms od starta taktike/ESP-a, tekst), ostaju dok se ne pogledaju
        self.unseen = 0
        self.report = None                 # poslednji izveštaj (dict), vidi make_report
        self.pump = None                   # jedan krug glavne petlje (postavlja main.py)
        self.loop = None
        self.side = self.st["sel_side"] or tac.REF_SIDE    # strana za sledeću taktiku
        self.last = None                   # (ime, strana) poslednje pokrenute taktike
        self._run = None                   # podaci o taktici koja radi (za izveštaj)
        self._alive = False
        self.match = Match(self)
        self.demo = Demo(tracker)
        tracker.demo = self.st["demo"]
        self.pages = Pages(self)
        self.ui = ui.UI(fb, self.pages, self.indicators, lambda: self.st["sleep_s"])
        self.ui.on_menu = self.open_menu
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
        out = []
        if self.unseen:
            out.append((ICON_BANG, False))
        if state.MODE == "AP":
            out.append((ui.ICON_AP, False))
        elif state.MODE or not (self.match.state == "MEC" and self.st["wifi_off_match"]):
            out.append((ui.ICON_WIFI, not state.MODE))     # trepće dok se povezuje (ne kad je namerno ugašen)
        out.append((ui.ICON_LINK, False) if self.robot.ok else (ui.ICON_NOLINK, True))
        return out

    def show_page(self, name):
        self.pages.show(name)
        self.ui.home()
        self.ui.wake()

    # ---------------- poruke ----------------

    def error(self, text):
        """Greška: ostaje na stranici DNEVNIK, a u traci je ! dok se ne pogleda."""
        t = ticks_diff(ticks_ms(), self._run["t0"]) if self._run else ticks_ms()
        self.errors = (self.errors + [(t, text)])[-30:]
        self.unseen += 1
        self.tlog("GRESKA " + text)

    def errors_seen(self):
        self.unseen = 0

    # ---------------- glavna petlja ----------------

    def update(self):
        r = self.robot
        self.events = r.poll()
        for seq, label, kind, reason in self.events:
            name = T.SHORT.get(label, label)
            if reason == "MATCH_OVER":
                continue                        # kraj meča nije greška (L9)
            if kind == "fail" or (kind == "timeout" and reason != "SUPERSEDED"):
                self.error("%s: %s" % (name, T.reason(reason or kind)))
                self.ui.toast("%s: %s" % (name, T.reason(reason or kind)), 2000)
        # Auto poza samo za razvoj: posle povezivanja, i to samo ako STATUS kaže da ne traje meč
        # i robot ne vozi, i ne radi taktika. Restart ESP-a usred meča ne sme da pregazi odometriju.
        if r.ok and not self._pose_sent and r.status is not None:
            self._pose_sent = True
            quiet = not (r.status["state"] & (P.State.MATCH_RUNNING | P.State.MATCH_OVER | P.State.MOVING))
            if self.st["start_pose"] and quiet and not (self.running or self.request):
                x, y, th = cfg.START_POSE
                r.send("SET_POSE", x=x, y=y, theta=th * 100)
        if self._alive and not r.alive and self.match.state == "MEC":
            self.ui.alarm("VEZA", "STM32 ne odgovara")
        self._alive = r.alive
        if self._run is not None:
            self._run["ping_max"] = max(self._run["ping_max"], r.ping_gap)
        self.match.update()
        if tracker.demo and not self.running and not self.match.armed:
            self.demo.update()
        if tracker.running and tracker.t_start != self._seen_start:   # nova taktika: prikaži je
            self._seen_start = tracker.t_start
            self.show_page("TAKTIKA")
            if self.match.state == "MEC" and self.st["screen_match"] == "ugasen":
                self.ui.asleep = True
                if self.fb:
                    self.fb.poweroff()
        # u meču: posle 10 s bez dodira nazad na stranicu stanja (da se ne ostane slučajno na VEZA)
        want = {"NAORUZAN": "PROVERA", "POZA": "PROVERA", "MEC": "TAKTIKA"}.get(self.match.state)
        if want and self.pages.cur.name != want and len(self.ui.stack) == 1 \
                and ticks_diff(ticks_ms(), self.pages.t_touch) > RETURN_MS:
            self.pages.show(want)
            self.ui.dirty = True

    def stop(self):
        """Taster STOP: radi uvek, i bez veze i dok je ekran ugašen."""
        self.robot.send("STOP")
        self.request = None                    # izabrana taktika koja još nije krenula ne kreće
        self.match.cancel()                    # naoružan meč se otkazuje
        self.match.stopped()                   # meč u toku: STOP ga namerno završava (otključava, L8)
        if self.running:
            self.abort = "STOP"
        self.ui.alarm("STOP", "taster STOP" if not self.running else "taktika prekinuta")

    def tlog(self, text):
        print("[taktika]", text)
        self.log = (self.log + [text])[-40:]
        self.log_n += 1

    def remaining(self):
        return tac.remaining()

    # ---------------- taktike: izbor, provera, pokretanje ----------------

    def tactics(self):
        try:
            import tactic
            return sorted(f[:-3] for f in os.listdir(tactic.TACTICS_DIR) if f.endswith(".py"))
        except OSError:
            return []

    def busy(self):
        """Taktika radi, čeka da krene, meč je naoružan ili traje (i kad je ESP restartovan usred meča, po
        STATUS-u): servisi (upload, meni, test) tada ne smeju da smetaju."""
        s = self.robot.status if self.robot.alive else None
        return bool(self.running or self.request or self.match.armed
                    or (s and s["state"] & P.State.MATCH_RUNNING))

    def select(self, name=None, side=None):
        """Izbor taktike i strane (pamti se u settings.json, preživi restart i zamenu baterije)."""
        if name is not None:
            self.st.set("sel_tactic", name)
            self._compiled = None
        if side is not None:
            self.st.set("sel_side", side)
            self.side = side

    def tactic_ok(self):
        """Izabrana taktika postoji, START/TOTAL se čitaju i kompajlira se. Ponovo se proverava kad se fajl
        promeni (veličina, vreme izmene: posle PUT/esp_push), najviše jednom u sekundi (L5)."""
        name = self.st["sel_tactic"]
        c = getattr(self, "_compiled", None)
        now = ticks_ms()
        if c and c[0] == name and ticks_diff(now, c[4]) < 1000:
            return c[2], c[3]
        try:
            st = os.stat("%s/%s.py" % (tactic.TACTICS_DIR, name)) if name else None
        except OSError:
            st = None
        if st is None:
            self._compiled = (name, None, False, "nema fajla", now)
            return False, "nema fajla"
        key = (st[6], st[8])
        if c and c[0] == name and c[1] == key:
            self._compiled = c[:4] + (now,)
            return c[2], c[3]
        import match
        meta = match.read_meta(name)
        ok, why = True, ""
        if meta.get("greska"):
            ok, why = False, meta["greska"]
        else:
            try:
                import runner
                runner._compiled(name)
            except Exception as e:      # noqa: BLE001
                ok, why = False, type(e).__name__
        self._compiled = (name, key, ok, why, now)
        return ok, why

    def check(self):
        """PROVERA: (sve_ok, [(stanje, naziv, vrednost)]), stavke koje ne valjaju prve.
        stanje: ok / ne (blokira start) / upoz (upozorenje) / ceka (sledeći korak)."""
        r, st = self.robot, self.st
        items = []
        if r.ok:
            items.append(("ok", "STM32", "v%d" % r.version))
        else:
            items.append(("ne", "STM32", "nema" if not r.alive else "v%s" % r.version))
        age = r.status_age()
        items.append(("ok", "STATUS", "%dms" % age) if r.alive and age is not None and age < 200
                     else ("ne", "STATUS", "star" if r.alive else "-"))
        name = st["sel_tactic"]
        if not name:
            items.append(("ne", "taktika", "izaberi"))
        else:
            ok, why = self.tactic_ok()
            items.append(("ok", "taktika", name) if ok else ("ne", "taktika", why))
        side = st["sel_side"]
        items.append(("ok", "strana", side) if side else ("ne", "strana", "izaberi"))
        if self.unseen:
            items.append(("upoz", "greske", "%d novih" % self.unseen))
        s = r.status if r.alive else None
        if s and s["state"] & (P.State.MATCH_RUNNING | P.State.MATCH_OVER) and not self.match.armed:
            # stari meč na STM32 (pregled logike L1, L7): NRST ga resetuje pri naoružavanju, inače ručno
            items.append(("upoz", "STM32 mec", "reset pri naoruz.") if self.match.hw
                         else ("ne", "STM32 mec", "restartuj STM32"))
        if self.match.state == "RESET":
            items.append(("ceka", "STM32", "reset..."))
        elif self.match.armed:
            items.append(("ceka", "cinc", "izvuci"))
        order = {"ne": 0, "upoz": 1, "ceka": 2, "ok": 3}
        items.sort(key=lambda i: order[i[0]])
        return not any(i[0] == "ne" for i in items), items

    def arm(self):
        if self.match.arm(self.st["sel_tactic"], self.st["sel_side"]):
            self.show_page("PROVERA")

    def start_tactic(self, name, side=None):
        """Odmah pokreni taktiku (test bez meča)."""
        if not self.busy():
            self.side = side or self.st["sel_side"] or tac.REF_SIDE
            self.request = name

    # ---------------- izveštaj ----------------

    def on_tactic_start(self, name):
        r = self.robot
        self._run = {"t0": ticks_ms(), "crc": r.parser.errors, "retries": r.retries,
                     "noreply": r.noreply, "ping_max": 0}
        if self.match.state != "MEC":           # u meču su greške obrisane pri naoružavanju (L14)
            self.errors, self.unseen = [], 0

    def on_tactic_end(self, name, how):
        """how: None = završila normalno, inače razlog prekida. Pravi izveštaj, čuva ga, prikazuje."""
        r, run = self.robot, self._run or {"t0": ticks_ms(), "crc": 0, "retries": 0, "noreply": 0, "ping_max": 0}
        h = list(tracker.history)
        end = how == "kraj meca"                # L9: kraj meča (100 s) nije prekid ni greška
        fail = next(((i, n, rs) for i, n, ok, rs, d in h if not ok and not (end and rs in ("KRAJ", "KRAJ MECA", "MATCH_OVER"))),
                    None)
        if end:
            how = None
        s = r.status
        self.report = {
            "name": name, "side": self.side, "ok": how is None and fail is None,
            "ms": ticks_diff(ticks_ms(), run["t0"]), "steps": len(h), "total": tracker.total,
            "done": sum(1 for x in h if x[2]), "fail": fail or ((tracker.idx, tracker.step_name or "-", how) if how else None),
            "how": how, "steps_list": h,
            "link": {"crc": r.parser.errors - run["crc"], "retries": r.retries - run["retries"],
                     "noreply": r.noreply - run["noreply"], "ping_max": run["ping_max"]},
            "pose": [s["x"], s["y"], round(s["theta"] / 100)] if s else None,
            "match": self.match.state in ("MEC", "KRAJ"), "match_end": end,
        }
        self._run = None
        self.save_report(self.report)
        self.pages.list[-1].view = 0
        if how:                                # prekid: ceo ekran, pa izveštaj
            self.ui.alarm("PREKID" if how != "STOP" else "STOP", how, lambda: self.show_page("IZVESTAJ"))
        else:
            self.show_page("IZVESTAJ")

    def save_report(self, rp):
        try:
            import json
            try:
                os.mkdir(MEC_DIR)
            except OSError:
                pass
            names = sorted(os.listdir(MEC_DIR))
            n = int(names[-1][:-5]) + 1 if names else 1
            with open("%s/%04d.json" % (MEC_DIR, n), "w") as f:
                json.dump(rp, f)
            for old in names[:-(MEC_KEEP - 1)] if len(names) >= MEC_KEEP else []:
                os.remove("%s/%s" % (MEC_DIR, old))
        except Exception as e:
            print("izvestaj:", e)

    def reports(self):
        try:
            return sorted(os.listdir(MEC_DIR), reverse=True)
        except OSError:
            return []

    def load_report(self, fn):
        import json
        with open("%s/%s" % (MEC_DIR, fn)) as f:
            self.report = json.load(f)
        self.pages.list[-1].view = 0
        self.show_page("IZVESTAJ")

    # ---------------- meniji ----------------

    def open_menu(self):
        if self.match.armed or self.running:
            self.ui.toast("zakljucano", 1500)
            return
        self.ui.push(self.settings_menu())

    def tactics_menu(self):
        """TAKTIKE -> STRANA -> nazad na PROVERA (izbor se pamti)."""
        names = self.tactics()
        cur = self.st["sel_tactic"]
        items = [Action(("* " if n == cur else "") + n,
                        (lambda n: lambda u: (self.select(name=n), u.pop(), u.push(self.side_menu())))(n))
                 for n in names]
        return Menu("Taktike", items or [Info("nema", lambda: "-")])

    def side_menu(self):
        import match
        meta = match.read_meta(self.st["sel_tactic"] or "")
        def pick(s):
            def f(u):
                self.select(side=s)
                u.home()
                self.show_page("PROVERA")
            return f
        items = []
        for s in tac.SIDES:
            pos = meta.get("START")
            if pos:
                tac.current_side = s
                x, y = tac.mirror_xy(pos[0], pos[1])
                lbl = "%s x=%d" % (s, x)          # ogledanje menja samo x
            else:
                lbl = s
            items.append(Action(lbl, pick(s)))
        tac.current_side = self.side
        return Menu("Strana", items)

    def reports_menu(self):
        items = []
        for fn in self.reports():
            items.append(Action(fn[:-5], (lambda fn: lambda u: (u.home(), self.load_report(fn)))(fn)))
        return Menu("Mecevi", items or [Info("nema", lambda: "-")])

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
            ui.Sub("Mecevi", self.reports_menu),
            Choice("u mecu", [("miran", "miran"), ("ugasen", "ugasen"), ("detaljan", "detalj")],
                   lambda: st["screen_match"], lambda v: st.set("screen_match", v)),
            Number("kontrast", lambda: st["contrast"], lambda v: (st.set("contrast", v), self.apply_display()),
                   0, 255, 15, preview=lambda v: self.apply_display(v)),
            Toggle("okreni 180", lambda: st["flip"], flip),
            Toggle("obrni enk.", lambda: st["enc_rev"], lambda v: st.set("enc_rev", v)),
            Choice("spavanje", [(0, "nikad"), (60, "1min"), (300, "5min")],
                   lambda: st["sleep_s"], lambda v: st.set("sleep_s", v)),
            Toggle("auto poza", lambda: st["start_pose"], lambda v: st.set("start_pose", v)),
            Toggle("demo takt.", lambda: st["demo"], self.set_demo),
            Toggle("WDT u mecu", lambda: st["wdt_match"], lambda v: st.set("wdt_match", v)),
            Toggle("WiFi off mec", lambda: st["wifi_off_match"], lambda v: st.set("wifi_off_match", v)),
            Info("verzija", lambda: __import__("upload").version()),
            Info("RAM", lambda: "%dk" % (gc.mem_free() // 1024) if hasattr(gc, "mem_free") else "-"),
            Info("radi", lambda: "%dmin" % (ticks_ms() // 60000)),
        ])
