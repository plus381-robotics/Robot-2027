# Provera bez kretanja: veza, SET_POSE i dnevnik. Robot se ne pomera, ali SET_POSE pregazi odometriju
# (postavi je na 250, 1000, 0 naše strane): ne pokretati usred rada sa robotom na drugom mestu.
from tac import *

log("STM32: %s" % status())
pose(250, 1000, 0)
wait(1)
log("posle SET_POSE: %s" % status())
