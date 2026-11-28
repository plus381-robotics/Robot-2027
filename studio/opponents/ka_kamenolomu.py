# Protivnik: ide pravo na srednji kamenolom NA NAŠOJ polovini i stoji ispred njega (blokira ga), pa na donji.
from gambit import *

START = (250, 1000, 0)

goto(1900, 1500, speed=700)     # x > 1500 = naša polovina (posle ogledanja)
wait(8)
goto(1900, 600, speed=500)
wait(100)
