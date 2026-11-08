# PAMI: stoji do poslednjih 15 s meča, pa vozi pravo napred (od mesta gde je postavljen).
from gambit import *

wait_until(lambda: match_time() >= 85, 100)
move(700, speed=400)
