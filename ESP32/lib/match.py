# Tok meča: izbor taktike -> strana -> NAORUZAN (čeka se činč) -> MEC -> KRAJ.
#
# Činč je na STM32: kad se izvuče, STM32 krene da broji 100 s i u STATUS-u postavi MATCH_RUNNING.
# ESP to vidi, odmah pošalje startnu pozu izabrane strane (START iz taktike), sačeka ACK i pokrene
# taktiku. Robot do tada stoji, pa poza ostaje tačna. Bez činča (BlackPill) se za razvoj koristi
# "simulirani činč" iz menija (komanda MATCH_START).
# Dok je robot naoružan i u meču: machine.WDT (ESP se restartuje ako se zaglavi; posle restarta
# nema auto poze jer STATUS pokazuje meč) i, ako je podešeno, ugašen WiFi.
from compat import ticks_ms, ticks_diff
import protocol as P
import tac
import tactic

IDLE, ARMED, POSE, MATCH, DONE = "NEMA", "NAORUZAN", "POZA", "MEC", "KRAJ"
WDT_MS = 3000


def read_meta(name):
    """START i TOTAL sa vrha taktike, bez izvršavanja (redovi 'START = (x, y, ugao)', 'TOTAL = n')."""
    meta = {}
    try:
        with open("%s/%s.py" % (tactic.TACTICS_DIR, name)) as f:
            for line in f:
                line = line.split("#")[0].strip()
                for key in ("START", "TOTAL"):
                    if line.startswith(key) and "=" in line:
                        v = line.split("=", 1)[1].strip().strip("()")
                        nums = [float(n) for n in v.split(",") if n.strip()]
                        meta[key] = nums if key == "START" else int(nums[0])
    except (OSError, ValueError, IndexError):
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

    @property
    def armed(self):
        return self.state in (ARMED, POSE, MATCH)

    def arm(self, name, side):
        if self.app.running or self.armed:
            return False
        meta = read_meta(name)
        self.tactic, self.side, self.start = name, side, meta.get("START")
        self.state = ARMED
        self.app.tlog("NAORUZAN %s (%s)%s" % (name, side, "" if self.start else ", bez START poze"))
        if self.app.st["wdt_match"] and self.wdt is None:
            try:
                from machine import WDT
                self.wdt = WDT(timeout=WDT_MS)      # na ESP32 ne može da se isključi do restarta
            except Exception as e:
                self.app.tlog("WDT: %s" % e)
        return True

    def cancel(self):
        if self.state in (ARMED, POSE):
            self.state = IDLE
            self.app.tlog("otkazano")

    def simulate_cord(self):
        """Za robot bez činča: isto što STM32 uradi kad se činč izvuče."""
        if self.state == ARMED:
            self.app.robot.send("MATCH_START")

    def update(self):
        if self.wdt:
            self.wdt.feed()
        r, a = self.app.robot, self.app
        s = r.status if r.alive else None
        if self.state == ARMED and s and s["state"] & P.State.MATCH_RUNNING:
            a.tlog("CINC: start")
            if self.start:
                x, y, deg = self.start
                tac.current_side = self.side
                mx, my = tac.mirror_xy(x, y)
                self._pose_seq = r.send("SET_POSE", x=int(mx), y=int(my), theta=int(tac.mirror_deg(deg) * 100))
                self._t = ticks_ms()
                self.state = POSE
            else:
                self._go()
        elif self.state == POSE:
            if any(sq == self._pose_seq and k == "ok" for sq, _, k, _ in a.events):
                self._go()
            elif ticks_diff(ticks_ms(), self._t) > 500:
                a.tlog("POZA nije potvrdjena, krecem")
                self._go()
        elif self.state == MATCH and not a.running and not a.request:
            self.state = DONE
            a.tlog("KRAJ meca")
        if self.state in (MATCH, DONE) and s and s["state"] & P.State.MATCH_OVER and a.running:
            a.abort = "kraj meca"

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
