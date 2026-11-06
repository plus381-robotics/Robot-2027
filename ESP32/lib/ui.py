# Meni za OLED 128x64 (SSD1306). Ne zna ništa o robotu: stavke dobijaju funkcije.
#
# Ulaz (main.py ga prevodi iz enkodera i tastera):
#   ui.input("rot", n)   okret enkodera za n koraka (+ = dole / više)
#   ui.input("ok")       klik
#   ui.input("back")     nazad (dugi klik enkodera ili taster)
#   ui.input("home")     nazad na početni ekran
#   ui.hold(ms)          koliko dugo se drži OK (0 = pušten), za "drži za potvrdu"
# Crtanje: ui.tick() u glavnoj petlji; crta samo kad se nešto promenilo.
try:
    from time import ticks_ms, ticks_diff
except ImportError:                     # CPython (simulator na laptopu)
    import time as _t

    def ticks_ms():
        return int(_t.monotonic() * 1000)

    def ticks_diff(a, b):
        return a - b

W, H = 128, 64
HEAD = 16       # naslovna traka (na dvobojnom OLED-u je to tačno žuta zona)
ROW = 12        # visina reda
ROWS = 4        # redova ispod trake: (64 - HEAD) // ROW
LIVE_MS = 150   # koliko često se osvežavaju ekrani sa živim podacima

# Ikonice: redovi od 8 piksela, levi piksel je najviši bit.
ICON_WIFI = (0x3C, 0x42, 0x99, 0x24, 0x00, 0x18)
ICON_AP = (0x42, 0x99, 0xA5, 0x99, 0x5A, 0x18, 0x24)
ICON_LINK = (0x04, 0xFE, 0x04, 0x20, 0x7F, 0x20)         # strelice levo-desno
ICON_NOLINK = (0x82, 0x44, 0x28, 0x10, 0x28, 0x44, 0x82)  # x
ICON_CHEVRON = (0x80, 0x40, 0x20, 0x10, 0x20, 0x40, 0x80)
ICON_PLAY = (0x80, 0xC0, 0xE0, 0xF0, 0xE0, 0xC0, 0x80)
ICON_LEFT = (0x20, 0x60, 0xE0, 0x60, 0x20)
ICON_RIGHT = (0x80, 0xC0, 0xE0, 0xC0, 0x80)
ICON_THETA = (0x70, 0x88, 0x88, 0xF8, 0x88, 0x88, 0x70)
ICON_DEG = (0x40, 0xA0, 0x40)


def icon(fb, ic, x, y, c=1):
    for r, bits in enumerate(ic):
        if bits:
            for b in range(8):
                if bits & (0x80 >> b):
                    fb.pixel(x + b, y + r, c)


def box(fb, x, y, w, h, c=1):
    """Pun pravougaonik zaobljenih ivica."""
    fb.fill_rect(x, y, w, h, c)
    for px, py in ((x, y), (x + w - 1, y), (x, y + h - 1), (x + w - 1, y + h - 1)):
        fb.pixel(px, py, 1 - c)


def frame(fb, x, y, w, h, c=1):
    """Okvir zaobljenih ivica."""
    fb.hline(x + 1, y, w - 2, c)
    fb.hline(x + 1, y + h - 1, w - 2, c)
    fb.vline(x, y + 1, h - 2, c)
    fb.vline(x + w - 1, y + 1, h - 2, c)


def text_right(fb, s, xr, y, c=1):
    fb.text(s, xr - 8 * len(s), y, c)


def text_center(fb, s, y, c=1, x0=0, w=W):
    fb.text(s, x0 + (w - 8 * len(s)) // 2, y, c)


def fit(s, chars):
    s = str(s)
    return s if len(s) <= chars else s[:max(chars - 1, 0)] + "~"


# ---------------- stavke menija ----------------

class Item:
    live = False          # vrednost se menja sama od sebe (osvežavaj ekran)
    def __init__(self, label):
        self.label = label

    def value(self):      # tekst desno u redu, ili None
        return None

    def activate(self, ui, scr):
        pass

    def right_w(self, editing):         # koliko piksela zauzima desni deo reda
        v = self.value()
        return 0 if v is None else 8 * len(fit(v, 7)) + (12 if editing else 0)

    def draw_right(self, fb, xr, y, c, editing):
        v = self.value()
        if v is not None:
            text_right(fb, fit(v, 7), xr, y, c)


class Sub(Item):
    """Podmeni. screen je ekran ili funkcija koja ga pravi (svež pri svakom ulasku)."""
    def __init__(self, label, screen):
        super().__init__(label)
        self.screen = screen

    def activate(self, ui, scr):
        ui.push(self.screen() if callable(self.screen) else self.screen)

    def right_w(self, editing):
        return 5

    def draw_right(self, fb, xr, y, c, editing):
        icon(fb, ICON_CHEVRON, xr - 4, y, c)


class Action(Item):
    """Akcija. Ako je dat confirm (tekst), traži se držanje OK pre izvršavanja."""
    def __init__(self, label, fn, confirm=None):
        super().__init__(label)
        self.fn, self.confirm = fn, confirm

    def activate(self, ui, scr):
        if self.confirm:
            ui.push(Confirm(self.label, self.confirm, self.fn))
        else:
            self.fn(ui)

    def right_w(self, editing):
        return 5

    def draw_right(self, fb, xr, y, c, editing):
        icon(fb, ICON_PLAY, xr - 4, y, c)


class Toggle(Item):
    def __init__(self, label, get, set):
        super().__init__(label)
        self.get, self.set = get, set

    def activate(self, ui, scr):
        self.set(not self.get())

    def right_w(self, editing):
        return 15

    def draw_right(self, fb, xr, y, c, editing):
        x = xr - 15                      # prekidač 15x8
        frame(fb, x, y, 15, 8, c)
        if self.get():
            box(fb, x + 8, y + 2, 5, 4, c)
            fb.fill_rect(x + 2, y + 3, 5, 2, c)
        else:
            frame(fb, x + 2, y + 2, 5, 4, c)


class Number(Item):
    """Broj koji se menja enkoderom. Brzo okretanje = veći korak. set() se zove tek na OK.
    preview(v): zove se dok se okreće (npr. kontrast se vidi odmah); NAZAD vraća staru vrednost."""
    def __init__(self, label, get, set, lo, hi, step=1, unit="", fmt=None, preview=None):
        super().__init__(label)
        self.get, self.set = get, set
        self.lo, self.hi, self.step = lo, hi, step
        self.unit, self.fmt, self.preview = unit, fmt, preview
        self.v = None                    # vrednost dok se menja
        self._last = 0

    def text(self, v):
        return (self.fmt(v) if self.fmt else str(v)) + self.unit

    def value(self):
        return self.text(self.get() if self.v is None else self.v)

    def activate(self, ui, scr):
        self.v, self._old = self.get(), self.get()
        scr.editing = True

    def adjust(self, n):
        now = ticks_ms()
        fast = ticks_diff(now, self._last) < 60
        self._last = now
        self.v = max(self.lo, min(self.hi, self.v + n * self.step * (10 if fast else 1)))
        if self.preview:
            self.preview(self.v)

    def commit(self, ui):
        self.set(self.v)
        self.v = None

    def cancel(self):
        if self.preview:
            self.preview(self._old)
        self.v = None

    def draw_right(self, fb, xr, y, c, editing):
        s = fit(self.value(), 7)
        if not editing:
            text_right(fb, s, xr, y, c)
            return
        w = 8 * len(s) + 12              # vrednost u "rupi" sa strelicama
        x = xr - w + 2
        box(fb, x, y - 2, w, 12, 1 - c)
        icon(fb, ICON_LEFT, x + 1, y + 1, c)
        fb.text(s, x + 6, y, c)
        icon(fb, ICON_RIGHT, x + w - 5, y + 1, c)


class Choice(Number):
    """Izbor jedne od ponuđenih vrednosti: options = [(vrednost, tekst), ...]."""
    def __init__(self, label, options, get, set):
        self.options = options
        super().__init__(label, self._get_i, self._set_i, 0, len(options) - 1)
        self._get, self._set = get, set

    def _get_i(self):
        v = self._get()
        for i, (o, _) in enumerate(self.options):
            if o == v:
                return i
        return 0

    def _set_i(self, i):
        self._set(self.options[i][0])

    def adjust(self, n):
        self.v = max(0, min(len(self.options) - 1, self.v + n))

    def text(self, i):
        return self.options[i][1]


class Info(Item):
    """Samo prikaz. Klik pokazuje celu vrednost ako ne staje u red."""
    live = True
    def __init__(self, label, fn):
        super().__init__(label)
        self.fn = fn

    def value(self):
        return str(self.fn())

    def activate(self, ui, scr):
        ui.toast(self.value(), 2500)


# ---------------- ekrani ----------------

class Screen:
    live = False
    wants_hold = False
    def rotate(self, ui, n): pass
    def ok(self, ui): pass
    def back(self, ui): return False     # True = obrađeno, ne vraćaj se nazad
    def hold(self, ui, ms): pass
    def draw(self, ui, fb): pass


class Menu(Screen):
    def __init__(self, title, items):
        self.title, self.items = title, items
        self.sel = self.top = 0
        self.editing = False
        self.live = any(i.live for i in items)

    def rotate(self, ui, n):
        if self.editing:
            self.items[self.sel].adjust(n)
            return
        self.sel = max(0, min(len(self.items) - 1, self.sel + n))
        if self.sel < self.top:
            self.top = self.sel
        elif self.sel >= self.top + ROWS:
            self.top = self.sel - ROWS + 1

    def ok(self, ui):
        it = self.items[self.sel]
        if self.editing:
            self.editing = False
            it.commit(ui)
        else:
            it.activate(ui, self)

    def back(self, ui):
        if self.editing:
            self.editing = False
            self.items[self.sel].cancel()
            return True
        return False

    def draw(self, ui, fb):
        ui.header(fb, self.title, "%d/%d" % (self.sel + 1, len(self.items)))
        for r in range(ROWS):
            i = self.top + r
            if i >= len(self.items):
                break
            it = self.items[i]
            y = HEAD + r * ROW
            c = 1
            if i == self.sel:
                box(fb, 0, y, 124, ROW, 1)
                c = 0
            editing = self.editing and i == self.sel
            rw = it.right_w(editing)
            fb.text(fit(it.label, (121 - 4 - rw - (4 if rw else 0)) // 8), 4, y + 2, c)
            it.draw_right(fb, 121, y + 2, c, editing)
        n = len(self.items)                  # klizač desno
        if n > ROWS:
            top, h = HEAD, H - HEAD
            for yy in range(top, top + h, 2):
                fb.pixel(126, yy, 1)
            th = max(4, h * ROWS // n)
            ty = top + (h - th) * self.top // (n - ROWS)
            fb.fill_rect(125, ty, 3, th, 1)


class Confirm(Screen):
    """Opasna akcija (kretanje): izvršava se tek kad se OK drži HOLD_MS."""
    HOLD_MS = 800
    live = True
    wants_hold = True
    def __init__(self, title, lines, fn):
        self.title, self.fn = title, fn
        self.lines = lines if isinstance(lines, (list, tuple)) else [lines]
        self.ms = 0
        self.done = False

    def hold(self, ui, ms):
        self.ms = ms
        if ms >= self.HOLD_MS and not self.done:
            self.done = True
            ui.pop()
            self.fn(ui)

    def draw(self, ui, fb):
        ui.header(fb, self.title + "?")
        for i, l in enumerate(self.lines[:3]):
            l = l() if callable(l) else l
            fb.text(fit(l, 16), 0, HEAD + 1 + i * 9, 1)
        frame(fb, 2, 45, 124, 8, 1)
        p = min(self.ms, self.HOLD_MS) * 120 // self.HOLD_MS
        if p:
            fb.fill_rect(4, 47, p, 4, 1)
        text_center(fb, "drzi OK" if not self.ms else "jos malo...", 56)


# ---------------- glavni objekat ----------------

class UI:
    def __init__(self, fb, home, indicators=None, sleep_s=None):
        """fb: SSD1306 (ili None bez ekrana). home: početni ekran.
        indicators(): lista (ikonica, treperi) za desni deo naslovne trake.
        sleep_s(): posle koliko sekundi bez dodira se gasi ekran (0 = nikad)."""
        self.fb = fb
        self.stack = [home]
        self.indicators = indicators or (lambda: [])
        self.sleep_s = sleep_s or (lambda: 0)
        self.dirty = True
        self.last_draw = self.last_input = ticks_ms()
        self.asleep = False
        self._toast = None
        self._toast_until = 0
        self._toast_alert = False

    @property
    def top(self):
        return self.stack[-1]

    def push(self, scr):
        self.stack.append(scr)
        self.dirty = True

    def pop(self):
        if len(self.stack) > 1:
            self.stack.pop()
        self.dirty = True

    def home(self):
        del self.stack[1:]
        self.dirty = True

    def toast(self, text, ms=1500, alert=False):
        """Kratka poruka preko ekrana. alert=True: inverzna (greška) i budi ekran."""
        self._toast, self._toast_alert = str(text), alert
        self._toast_until = ticks_ms() + ms
        if alert:
            self.wake()
        self.dirty = True
        print("[ui]", text)

    def wake(self):
        self.last_input = ticks_ms()
        if self.asleep:
            self.asleep = False
            if self.fb:
                self.fb.poweron()
            self.dirty = True
            return True
        return False

    def input(self, ev, arg=None):
        if self.wake():
            return                      # prvi dodir samo pali ekran
        t = self.top
        if ev == "rot":
            t.rotate(self, arg)
        elif ev == "ok":
            t.ok(self)
        elif ev == "back":
            if not t.back(self):
                self.pop()
        elif ev == "home":
            self.home()
        self.dirty = True

    def hold(self, ms):
        if self.top.wants_hold:
            if ms:
                self.wake()
            self.top.hold(self, ms)

    def tick(self):
        now = ticks_ms()
        if self._toast and ticks_diff(now, self._toast_until) >= 0:
            self._toast = None
            self.dirty = True
        s = self.sleep_s()
        if s and not self.asleep and ticks_diff(now, self.last_input) > s * 1000:
            self.asleep = True
            if self.fb:
                self.fb.poweroff()
        if self.asleep:
            return
        if self.dirty or (self.top.live and ticks_diff(now, self.last_draw) >= LIVE_MS):
            self.draw()

    def draw(self):
        self.dirty = False
        self.last_draw = ticks_ms()
        fb = self.fb
        if not fb:
            return
        fb.fill(0)
        self.top.draw(self, fb)
        if self._toast:                    # traka na dnu, pokriva samo poslednji red
            s = fit(self._toast, 16)
            fb.fill_rect(0, H - 13, W, 13, 0)
            if self._toast_alert:
                box(fb, 0, H - 12, W, 12, 1)
                text_center(fb, s, H - 10, 0)
            else:
                fb.hline(0, H - 13, W, 1)
                fb.hline(0, H - 11, W, 1)
                text_center(fb, s, H - 9, 1)
        fb.show()

    def header(self, fb, title, right=None, page=None, alert=False):
        """Naslovna traka: podebljan naslov levo, desno tekst i ikonice stanja,
        ispod linija; page=(i, n) podebljava i-ti deo linije (na kojoj smo stranici).
        alert=True: tekst desno je inverzan (npr. vreme pred kraj meča)."""
        x = W
        blink = (ticks_ms() // 400) % 2
        for ic, blinks in self.indicators():
            x -= 9
            if not (blinks and blink):
                icon(fb, ic, x, 4 if len(ic) > 6 else 5, 1)
        room = (x - 3) // 8                         # znakova levo od ikonica
        if right and len(title) + 1 + len(right) <= room:
            if alert:
                box(fb, x - 4 - 8 * len(right), 2, 8 * len(right) + 3, 11, 1)
            text_right(fb, right, x - 3, 4, 0 if alert else 1)
            room -= len(right) + 1
        t = fit(title, room)
        fb.text(t, 0, 4, 1)
        fb.text(t, 1, 4, 1)                         # podebljano
        fb.hline(0, HEAD - 2, W, 1)
        if page:
            i, n = page
            seg = W // n
            fb.fill_rect(i * seg + 1, HEAD - 3, seg - 2, 3, 1)
