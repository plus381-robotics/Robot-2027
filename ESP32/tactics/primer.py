# Primer taktike. POKREĆE MOTORE.
#   python tools/tactic.py primer [--side plava]  (odmah, kao test; Ctrl+C = STOP)
#   na robotu: PROVERA -> taktika primer -> strana -> "naoruzaj" (čeka činč) ili "test odmah"
# Taster STOP na robotu uvek prekida taktiku.
# Piše se za žutu stranu; na plavoj se koordinate same ogledaju. Vidi ESP32/lib/tac.py.
from tac import *

START = (250, 1000, 0)          # startna poza; u meču je ESP postavi kad se izvuče činč
TOTAL = 3                       # broj koraka (za ekran "2/3")
# START poza se postavlja sama, i u meču (na činč) i u testu (podešavanje "test_start").
if not goto(600, 1000, speed=300, next="okret 90"):     # 35 cm napred
    log("nije stigao, vracam se")
    move(-100)
    raise Abort("GOTO nije uspeo")
turn_to(90, next="nazad 20 cm")                          # apsolutni ugao terena
move(-200, speed=200)
log("poza na kraju: %s" % (here(),))
