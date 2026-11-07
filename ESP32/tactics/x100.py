# Pomeri se 100 mm u +x osi od mesta gde stoji, pa se okreni za 180°. POKREĆE MOTORE.
#   python tools/tactic.py x100        (Ctrl+C = STOP)
# Poza se ne postavlja: kreće od onoga što trenutno pokazuje odometrija.
from tac import *

s = status()
if not s:
    raise Abort("nema STATUS-a od STM32")
log("start: x=%d y=%d ugao=%.1f" % (s["x"], s["y"], s["theta"] / 100))

if not goto(s["x"], s["y"] + 100, speed=100, name="GOTO +100 y", next="okret 180"):
    raise Abort("GOTO nije uspeo")

ugao = status()["theta"] / 100 + 180       # trenutni ugao + 180, u opsegu -180..180
if ugao > 180:
    ugao -= 360
rotate(ugao, name="ROTATE na %d" % ugao)

s = status()
log("kraj: x=%d y=%d ugao=%.1f" % (s["x"], s["y"], s["theta"] / 100))
