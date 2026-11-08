# Primer taktike. POKREĆE MOTORE.
#   python tools/tactic.py primer [--side plava]  (odmah, kao test; Ctrl+C = STOP)
#   na robotu: dugi klik -> Taktike -> primer -> "zuta: mec" (čeka činč) ili "zuta: test"
# Taster STOP na robotu uvek prekida taktiku.
# Piše se za žutu stranu; na plavoj se koordinate same ogledaju. Vidi ESP32/lib/tac.py.
from tac import *

START = (250, 1000, 0)          # startna poza; u meču je ESP postavi kad se izvuče činč
TOTAL = 4                       # broj koraka (za ekran "2/4")

if not remaining():             # test bez meča: postavi pozu ručno
    pose(*START)
if not goto(600, 1000, speed=300, next="okret 90"):     # 35 cm napred
    log("nije stigao, vracam se")
    move(-100)
    raise Abort("GOTO nije uspeo")
turn_to(90, next="nazad 20 cm")                          # apsolutni ugao terena
move(-200, speed=200)
log("poza na kraju: %s" % (here(),))
