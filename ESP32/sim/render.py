#!/usr/bin/env python3
"""Svi ekrani iz simulatora u jednu sliku (pravi kod ui.py/pages.py, lažni STM32, MicroPython font).

    python ESP32/sim/render.py [izlaz.png]        (treba Pillow)
"""
import pathlib
import sys
import tempfile

ESP = pathlib.Path(__file__).resolve().parents[1]
for p in (ESP / "sim", ESP, ESP / "lib"):
    sys.path.insert(0, str(p))

import compat
compat.fake = [100000]
import state
state.MODE, state.SSID, state.IP = "STA", "YU.net", "192.168.18.33"
import protocol as P
import ssd1306
import tactic
import tac
import app as appmod
from fakestm import FakeSTM
from robot import Robot
from settings import Settings
from app import App
from runner import Loop, run_tactic

tmp = pathlib.Path(tempfile.mkdtemp())
tactic.TACTICS_DIR = str(tmp)
appmod.MEC_DIR = str(tmp / "mec")
(tmp / "x100.py").write_text("from tac import *\nSTART = (250, 1000, 0)\nTOTAL = 3\n"
                             "goto(350, 1000, name='GOTO kocka B', next='okret 180')\n"
                             "turn_by(180, name='okret 180', next='nazad')\nmove(-100, name='nazad')\n")
(tmp / "primer.py").write_text("from tac import *\nSTART = (250, 1000, 0)\n")
stm = FakeSTM(motion_ms=900)
a = App(Robot(stm), Settings(str(tmp / "s.json")), ssd1306.SSD1306_I2C(128, 64))
a.loop = Loop([("robot", a.update), ("ekran", a.ui.tick)], compat.sleep_ms)
a.pump = a.loop.step
tac.app = a
u = a.ui
shots = []


def run(ms):
    end = compat.ticks_ms() + ms
    while compat.ticks_ms() < end:
        a.pump()


def snap(name):
    u.dirty = True
    u._shown = None
    u.tick()
    shots.append((name, a.fb.frames[-1]))


def page(name, title):
    a.pages.show(name)
    snap(title)


run(400)
page("PROVERA", "PROVERA: nije izabrana taktika")
u.input("ok"); u.input("rot", 1); snap("TAKTIKE")
u.input("ok"); snap("STRANA (sa startnom pozom)")
u.input("ok"); run(300); snap("PROVERA: sve OK, OK=naoruzaj")
u.input("ok"); run(300); snap("NAORUZAN: ceka cinc")
u.input("ok"); snap("simulirani cinc: drzi OK")
u.hold(900); u.hold(0); run(100)
for _ in range(300):
    if a.request:
        break
    run(20)
name, a.request = a.request, None
a.st.set("screen_match", "detaljan")
orig = a.pump
taken = {}


def pump_and_snap():
    orig()
    t = tactic.tracker
    if t.step_name == "GOTO kocka B" and "d" not in taken and t.elapsed() > 400:
        taken["d"] = 1
        a.pages.show("TAKTIKA"); snap("MEC detaljan: korak traje")
        a.st.set("screen_match", "miran")
        a.pages.show("TAKTIKA"); snap("MEC miran (krupno, retko crta)")
    if t.step_name == "okret 180" and "s" not in taken:
        taken["s"] = 1
        stm.drop = 3                 # okret ostane bez odgovora -> greska u dnevniku
a.pump = pump_and_snap
run_tactic(a, name)
a.pump = orig
run(2100)
snap("IZVESTAJ 1/3")
a.pages.cur.view = 1; snap("IZVESTAJ 2/3: koraci")
a.pages.cur.view = 2; snap("IZVESTAJ 3/3: veza, kraj")
a.pages.cur.view = 0
page("DNEVNIK", "DNEVNIK: greske ostaju")
page("ROBOT", "ROBOT")
page("VEZA", "VEZA")
a.stop(); snap("STOP preko celog ekrana")
u.input("ok")
run(200); u.input("menu"); snap("Meni (dugi NAZAD)")

from PIL import Image, ImageDraw
SC, PAD, CAP = 3, 14, 18
cols = 4
rows = (len(shots) + cols - 1) // cols
W, H = 128 * SC, 64 * SC
img = Image.new("RGB", (cols * (W + PAD) + PAD, rows * (H + PAD + CAP) + PAD), (30, 30, 34))
d = ImageDraw.Draw(img)
for i, (title, fr) in enumerate(shots):
    x0 = PAD + (i % cols) * (W + PAD)
    y0 = PAD + (i // cols) * (H + PAD + CAP)
    d.rectangle([x0 - 3, y0 - 3, x0 + W + 2, y0 + H + 2], fill=(0, 0, 0), outline=(70, 70, 76))
    for y in range(64):
        for x in range(128):
            if fr[y][x]:
                col = (255, 214, 90) if y < 16 else (120, 200, 255)
                d.rectangle([x0 + x * SC, y0 + y * SC, x0 + x * SC + SC - 2, y0 + y * SC + SC - 2], fill=col)
    d.text((x0, y0 + H + 5), "%d. %s" % (i + 1, title), fill=(220, 220, 220))
out = sys.argv[1] if len(sys.argv) > 1 else str(ESP / "ekran.png")
img.save(out)
print(out, len(shots), "ekrana")
