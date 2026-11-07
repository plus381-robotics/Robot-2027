# Provera bez kretanja: veza, SET_POSE i dnevnik. Bezbedno za pokretanje bilo kad.
from tac import *

log("STM32: %s" % status())
pose(250, 1000, 0)
wait(1)
log("posle SET_POSE: %s" % status())
