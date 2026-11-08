# Pomeri se 100 mm u +y (teren) od mesta gde stoji, pa se okreni za 180°. POKREĆE MOTORE.
#   python tools/tactic.py x100        (Ctrl+C = STOP)
# Poza se ne postavlja: kreće od onoga što trenutno pokazuje odometrija.
# here() vraća pozu u koordinatama naše strane (kao goto), pa radi isto na obe strane terena.
# (status() je sirov STATUS u koordinatama terena: ne sme direktno u goto, jer bi se na drugoj strani
#  ogledao dvaput.)
from tac import *

x, y, ugao = here()
log("start: x=%d y=%d ugao=%.1f" % (x, y, ugao))

if not goto(x, y + 100, speed=100, name="GOTO +100 y", next="okret 180"):
    raise Abort("GOTO nije uspeo")

turn_by(180, name="okret 180")

x, y, ugao = here()
log("kraj: x=%d y=%d ugao=%.1f" % (x, y, ugao))
