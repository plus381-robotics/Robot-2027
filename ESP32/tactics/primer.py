# Primer taktike. POKREĆE MOTORE.
#   python tools/tactic.py primer        (bez kabla, preko WiFi-ja; Ctrl+C = STOP)
#   ili na robotu: dugi klik -> Taktike -> primer -> drži OK
# Taster STOP na robotu uvek prekida taktiku.
# Jedinice: mm, stepeni (0° = +x, pozitivno = levo), mm/s, sekunde. Vidi ESP32/lib/tac.py.
from tac import *

pose(250, 1000, 0)                                   # gde robot stoji na početku
if not goto(600, 1000, speed=300, next="okret 90"):  # 35 cm napred
    log("nije stigao, vracam se")
    move(-100)
    raise Abort("GOTO nije uspeo")
rotate(90, next="nazad 20 cm")
move(-200, speed=200)
log("poza na kraju: %s" % status())
