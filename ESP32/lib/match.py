# Tok meča: izbor taktike -> strana -> NAORUZAN (čeka se činč) -> MEC -> KRAJ.
#
# Činč je na STM32: kad se izvuče, STM32 krene da broji 100 s i u STATUS-u postavi MATCH_RUNNING.
# ESP to vidi, odmah pošalje startnu pozu izabrane strane (START iz taktike), sačeka ACK i pokrene
# taktiku. Robot do tada stoji, pa poza ostaje tačna. Bez činča (BlackPill) se za razvoj koristi
# "simulirani činč" iz menija (komanda MATCH_START).
# Dok je robot naoružan i u meču: machine.WDT (ESP se restartuje ako se zaglavi; posle restarta
# nema auto poze jer STATUS pokazuje meč) i, ako je podešeno, ugašen WiFi.
#
# Zaštita (pregled logike L1, L2, L7):
#  - meč kreće samo na NOV činč: posle naoružavanja mora se videti STATUS bez meča, pa tek onda
#    MATCH_RUNNING. Ako je STM32 ostao u starom meču (gotov meč, STOP, restart ESP-a), naoružavanje ga
#    resetuje preko NRST (config.STM_NRST), a bez NRST-a se odbija ("restartuj STM32").
#  - ESP ima svoj sat meča (od činča) i sam prekida taktiku posle 100 s, i kad STM32 ne zna za meč.
#  - STM32 restartovan u meču (STATUS bez bitova meča pre 100 s): ESP vrati poslednju pozu (SET_POSE),
#    pa MATCH_START; komanda koja je bila u toku vraća False ("RESTART"). Nema odgovora duže od
#    HANG_MS: reset preko NRST (ako postoji).
#  - ESP restartovan u meču: ništa ne pokreće (robot stoji), samo jasno javi.
from compat import ticks_ms, ticks_diff
import protocol as P
import tac
import tactic

IDLE, RESET, ARMED, POSE, MATCH, DONE = "NEMA", "RESET", "NAORUZAN", "POZA", "MEC", "KRAJ"
WDT_MS = 3000
MATCH_MS = 100000
RESET_WAIT_MS = 3000           # posle NRST: koliko se čeka da se STM32 javi bez meča
HANG_MS = 1500                 # STM32 se ne javlja ovoliko u meču: NRST
NRST_LOW_MS = 20
INMATCH = P.State.MATCH_RUNNING | P.State.MATCH_OVER


class StmReset:
    """NRST (open-drain) i BOOT0 sa ESP-a, bez blokiranja petlje: pulse() pa poll() u svakom krugu."""

    def __init__(self, cfg):
        from machine import Pin
        self.nrst = Pin(cfg.STM_NRST, Pin.OPEN_DRAIN, value=1)
        self.boot0 = Pin(cfg.STM_BOOT0, Pin.OUT, value=0) if getattr(cfg, "STM_BOOT0", None) is not None else None
        self.t = None                  # kad je NRST spušten (None = pušten)
        self.t_last = None             # poslednji impuls

    def pulse(self):
        if self.boot0:
            self.boot0.value(0)        # normalan start (ne bootloader)
        self.nrst.value(0)
        self.t = self.t_last = ticks_ms()

    def poll(self):
        if self.t is not None and ticks_diff(ticks_ms(), self.t) >= NRST_LOW_MS:
            self.nrst.value(1)
            self.t = None

    def since(self):
        return None if self.t_last is None else ticks_diff(ticks_ms(), self.t_last)


def stm_reset():
    """StmReset ako je NRST povezan (config.STM_NRST), inače None."""
    import config as cfg
    if getattr(cfg, "STM_NRST", None) is None:
        return None
    return StmReset(cfg)


def read_meta(name):
    """START i TOTAL sa vrha taktike, bez izvršavanja: redovi 'START = (x, y[, ugao])' i 'TOTAL = n'.
    Ime mora biti tačno START / TOTAL (ne START_ZONA). Ugao se dopunjuje nulom. Red koji ne može da se
    pročita daje meta["greska"] (PROVERA je tada crvena, ne pada tek na činč)."""
    meta = {}
    try:
        with open("%s/%s.py" % (tactic.TACTICS_DIR, name)) as f:
            for line in f:
                line = line.split("#")[0].strip()
                if "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                if key not in ("START", "TOTAL"):
                    continue
                try:
                    nums = [float(n) for n in val.strip().strip("()[]").split(",") if n.strip()]
                    if key == "START":
                        if len(nums) not in (2, 3):
                            raise ValueError
                        meta["START"] = nums + [0.0] * (3 - len(nums))
                    else:
                        meta["TOTAL"] = int(nums[0])
                except (ValueError, IndexError):
                    meta["greska"] = "%s necitljiv" % key
    except OSError:
        pass
    return meta


class Match:
    def __init__(self, app):
        self.app = app
        self.state = IDLE
        self.tactic = None
        self.side = tac.REF_SIDE
        self.start = None              # (x, y, ugao) naše strane
        self.wdt = None
        self._pose_seq = None
        self._t = 0
        self.hw = stm_reset()          # NRST/BOOT0 ili None
        self.t_cord = None             # kad je viđen činč (ESP sat meča)
        self.stm_resets = 0            # koliko puta je STM32 restartovan u meču (tac.py prekida korak)
        self._last_pose = None         # poslednja poza iz STATUS-a dok meč traje (teren)
        self._restore = None           # obnova posle restarta: ("pose"|"start", seq, vreme)
        self._retry = False            # obnova nije potvrđena: sledeći pokušaj nije nov restart
        self._settle = -1              # status_n posle obnove: stari STATUS (bez meča) se ne računa
        self._pose_try = 0             # pokušaji START poze na činč (L14)
        self._was_running = None       # prethodni bit MATCH_RUNNING (činč bez naoružavanja, L4)
        self._idle_seen = False        # posle naoružavanja viđen STATUS bez meča (čeka se NOV činč)
        self._boot_seen = False

    @property
    def armed(self):
        """Naoružan ili meč traje: meni, test i upload su zaključani. Meč traje do 100 s od činča, i kad
        se taktika završi ranije (L8)."""
        if self.state in (RESET, ARMED, POSE, MATCH):
            return True
        return self.state == DONE and self.t_cord is not None and self.elapsed() < MATCH_MS

    def waiting(self):
        """Naoružan, čeka činč (može da se otkaže)."""
        return self.state in (RESET, ARMED)

    def restoring(self):
        """Obnova posle restarta STM32 u toku: tac.py ne šalje komande dok se ne završi."""
        return self._restore is not None

    def elapsed(self):
        """ms od činča (ESP sat), ili None."""
        return None if self.t_cord is None else ticks_diff(ticks_ms(), self.t_cord)

    def _stale(self, s):
        """STM32 je u (starom) meču: MATCH_RUNNING ili MATCH_OVER."""
        return bool(s and s["state"] & INMATCH)

    def arm(self, name, side):
        if self.app.running or self.armed:
            return False
        r = self.app.robot
        s = r.status if r.alive else None
        meta = read_meta(name)
        if meta.get("greska"):
            self.app.error("%s: %s" % (name, meta["greska"]))
            return False
        try:                            # prevedi sada (ne na činč: prevođenje na ESP-u traje, PROBLEMI 6)
            import runner
            runner._compiled(name)
        except Exception as e:          # noqa: BLE001
            self.app.error("%s: %s" % (name, type(e).__name__))
            return False
        self.app.errors, self.app.unseen = [], 0     # nov meč: stare greške se brišu sada, ne na start taktike
        self.tactic, self.side, self.start = name, side, meta.get("START")
        self.t_cord, self._pose_try = None, 0
        if self._stale(s):
            if not self._hw_reset("STM32 u starom mecu"):
                self.app.error("STM32 vec u mecu: restartuj STM32")
                return False
        else:
            self.state = ARMED
            self._idle_seen = s is not None
        self.app.tlog("NAORUZAN %s (%s)%s" % (name, side, "" if self.start else ", bez START poze"))
        if self.app.st["wdt_match"] and self.wdt is None:
            try:
                from machine import WDT
                self.wdt = WDT(timeout=WDT_MS)      # na ESP32 ne može da se isključi do restarta
            except Exception as e:
                self.app.tlog("WDT: %s" % e)
        return True

    def stopped(self):
        """Taster STOP (ili STOP preko WiFi-ja) usred meča: meč je namerno prekinut, zaključavanje prestaje.
        Ponovno naoružavanje tada ide preko zaštite starog meča (NRST ili "restartuj STM32")."""
        if self.state in (POSE, MATCH, DONE) and self.t_cord is not None:
            self.state, self.t_cord = IDLE, None
            self.app.tlog("mec prekinut (STOP)")

    def _hw_reset(self, why):
        """NRST impuls (ako postoji) i čekanje da se STM32 javi bez meča. False = nema NRST-a."""
        if not self.hw:
            return False
        self.hw.pulse()
        self.state, self._t = RESET, ticks_ms()
        self.app.tlog("%s: reset STM32 (NRST)" % why)
        return True

    def cancel(self):
        if self.state in (RESET, ARMED):
            self.state = IDLE
            self.app.tlog("otkazano")

    def simulate_cord(self):
        """Za robot bez činča: isto što STM32 uradi kad se činč izvuče."""
        if self.state == ARMED:
            self.app.robot.send("MATCH_START")

    def update(self):
        if self.wdt:
            self.wdt.feed()
        if self.hw:
            self.hw.poll()
        r, a = self.app.robot, self.app
        s = r.status if r.alive else None
        if s:
            run = bool(s["state"] & P.State.MATCH_RUNNING)
            if not self._boot_seen:
                self._boot_seen = True
                if self.state == IDLE and run:
                    a.tlog("MEC U TOKU posle restarta ESP-a: robot stoji")
                    a.error("ESP restart u mecu")
                    a.ui.alarm("MEC U TOKU", "ESP restart: robot stoji")
            elif run and self._was_running is False and self.state in (IDLE, DONE):
                a.tlog("CINC, a robot nije naoruzan: stoji")   # L4: npr. meč otkazan, a činč izvučen
                a.error("cinc bez naoruzavanja")
                a.ui.alarm("NIJE NAORUZAN", "cinc izvucen, robot stoji")
            self._was_running = run
        if self.state == RESET:
            if s and r.ok and not self._stale(s):
                self.state, self._idle_seen = ARMED, True
                a.tlog("STM32 resetovan: NAORUZAN, ceka cinc")
            elif ticks_diff(ticks_ms(), self._t) > RESET_WAIT_MS:
                self.state = IDLE
                a.error("STM32 se ne javlja posle reseta")
        elif self.state == ARMED and s and not self._stale(s):
            self._idle_seen = True
        elif self.state == ARMED and s and s["state"] & P.State.MATCH_RUNNING and not self._idle_seen:
            # od naoružavanja nije bilo STATUS-a bez meča: ovo nije nov činč nego stari meč
            if not self._hw_reset("STM32 u starom mecu"):
                self.state = IDLE
                a.error("STM32 vec u mecu: restartuj STM32")
        elif self.state == ARMED and s and s["state"] & P.State.MATCH_RUNNING:
            self.t_cord = ticks_ms()
            a.tlog("CINC: start")
            if self.start:
                self._send_pose(r)
                self.state = POSE
            else:
                self._go()
        elif self.state == POSE:
            ev = [k for sq, _, k, _ in a.events if sq == self._pose_seq]
            if "ok" in ev:
                self._go()
            elif ev or ticks_diff(ticks_ms(), self._t) > 300:
                # L14: odbijena (FAIL) ili bez odgovora. Robot na činč stoji: STOP pa ponovo, najviše 3 puta.
                if self._pose_try < 3:
                    r.send("STOP")
                    self._send_pose(r)
                else:
                    a.error("START poza nije postavljena")
                    a.tlog("POZA nije potvrdjena (3 puta), krecem")
                    self._go()
        elif self.state == MATCH and not a.running and not a.request:
            self.state = DONE
            a.tlog("KRAJ meca")
        if self.state in (MATCH, DONE) and s and s["state"] & P.State.MATCH_OVER and a.running:
            a.abort = "kraj meca"
        if self.state in (MATCH, DONE) and self.t_cord is not None:
            self._guard(r, a, s)

    def _guard(self, r, a, s):
        """Meč traje: ESP sat (100 s), restart STM32, STM32 koji se ne javlja."""
        el = self.elapsed()
        if el >= MATCH_MS:
            if a.running and not a.abort:
                a.abort = "kraj meca"
            return
        if s and s["state"] & P.State.MATCH_RUNNING and not self._restore:
            self._last_pose = (s["x"], s["y"], s["theta"], s["v"])
        if self._restore:
            self._restoring(r, a)
        elif s and not self._stale(s) and el < MATCH_MS - 500 and r.status_n > self._settle:
            if not self._retry:
                self.stm_resets += 1
                a.tlog("STM32 restart u mecu (%.1f s): vracam pozu" % (el / 1000))
                a.error("STM32 restart u mecu")
            self._restore_pose(r)
        elif self.hw and r.last_rx is not None and ticks_diff(ticks_ms(), r.last_rx) > HANG_MS \
                and (self.hw.since() is None or self.hw.since() > 3 * HANG_MS):
            a.tlog("STM32 se ne javlja u mecu: reset (NRST)")
            self.hw.pulse()

    def _restore_pose(self, r):
        if self._last_pose:
            # poslednji STATUS je star 0..50 ms kad STM32 stane: pomeri ga za pola perioda (25 ms) brzinom
            import math
            x, y, th, v = self._last_pose
            d = v * 0.025
            a = math.radians(th / 100)
            x, y = int(x + d * math.cos(a)), int(y + d * math.sin(a))
            self._restore = ("pose", r.send("SET_POSE", x=x, y=y, theta=th), ticks_ms())
        else:
            self._restore = ("start", r.send("MATCH_START"), ticks_ms())

    def _restoring(self, r, a):
        kind, seq, t = self._restore
        if any(sq == seq and k == "ok" for sq, _, k, _ in a.events):
            if kind == "pose":
                self._restore = ("start", r.send("MATCH_START"), ticks_ms())
            else:
                self._restore, self._retry = None, False
                self._settle = r.status_n       # čekaj nov STATUS (već u meču) pre nove provere
                a.tlog("STM32 obnovljen: poza i mec, nastavljam")
        elif ticks_diff(ticks_ms(), t) > 1000:
            self._restore, self._retry = None, True     # sledeći STATUS bez meča: novi pokušaj

    def _send_pose(self, r):
        x, y, deg = self.start
        tac.current_side = self.side
        mx, my = tac.mirror_xy(x, y)
        self._pose_try += 1
        self._pose_seq = r.send("SET_POSE", x=int(mx), y=int(my), theta=int(tac.mirror_deg(deg) * 100))
        self._t = ticks_ms()

    def _go(self):
        self.state = MATCH
        a = self.app
        if a.st["wifi_off_match"]:
            try:
                import network
                network.WLAN(network.STA_IF).active(False)
                network.WLAN(network.AP_IF).active(False)
            except Exception:
                pass
        a.side = self.side
        a.request = self.tactic

    def remaining(self):
        return tac.remaining()
