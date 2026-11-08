# Protivnik: patrolira gore-dole po svojoj polovini (tamo-nazad do kraja meča).
# Taktike protivnika se pišu kao naše (Gambit Micro, žuta strana); simulator ih ogleda na protivnikovu stranu.
from gambit import *

START = (250, 1000, 0)          # njegova startna zona

goto(700, 1000, speed=500)
while True:
    goto(700, 1600, speed=500)
    goto(700, 400, speed=500)
