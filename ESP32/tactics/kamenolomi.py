# Od kamenoloma do kamenoloma na našoj (žutoj) polovini, pa kući. Kamenolom = gomila od 3 kamena
# (simulator/eurosim/field.py, QUARRIES). Piše se za žutu stranu; na plavoj se koordinate same ogledaju.
#
# Prilaz u dva dela: normalno (IR štiti od protivnika) do ~270 mm ispred kamenoloma, pa poslednji deo sa
# near=True (IR ne zaustavlja robota, sporo, protokol v5). Bez near IR vidi kamenolom kao prepreku i robot stane.
from gambit import *

START = (250, 1000, 0)
TOTAL = 25

LICE = 40              # mm između prednje ivice robota i kamenoloma na kraju prilaza
POLA = 82              # pola dužine robota (165 mm)
ISPRED = 270           # do ove udaljenosti od lica kamenoloma vozi se normalno (IR domet 250 mm)


def uzmi(ime):
    actuator("hvataljka", 1, label="uzmi " + ime)      # na novom robotu: hvataljka; ovde samo pokazuje mesto


def gore(x, ime):
    """Kamenolom uz gornju ivicu (y 1945, lice na 1890): prilaz odozdo, okrenut na 90°."""
    goto(x, 1890 - POLA - ISPRED, deg=90, name=ime)
    goto(x, 1890 - POLA - LICE, deg=90, near=True, name=ime + " prilaz")
    uzmi(ime)
    move(-(ISPRED - LICE))                             # nazad, da sledeći put bude slobodan


def dole(x, ime):
    """Kamenolom uz donju ivicu (y 55, lice na 110): prilaz odozgo, okrenut na -90°."""
    goto(x, 110 + POLA + ISPRED, deg=-90, name=ime)
    goto(x, 110 + POLA + LICE, deg=-90, near=True, name=ime + " prilaz")
    uzmi(ime)
    move(-(ISPRED - LICE))


# Srednji kamenolomi (x 1445..1555) su blizu kolone x = 1250: put do nje ide dovoljno daleko od njih
# (y 1150 gore, y 850 dole), inače ih IR vidi u prolazu i robot stane.
deadline(12)                                           # kad ostane 12 s: prekid i kući
try:
    gore(750, "kamenolom 1")
    goto(750, 1150, name="ka kamenolomu 2")
    goto(1250, 1150)
    gore(1250, "kamenolom 2")
    goto(1093, 1500, deg=0, timeout=6, name="kamenolom 9")         # srednji (1500, 1500), okrenut 90°
    goto(1445 - POLA - LICE, 1500, deg=0, near=True, name="kamenolom 9 prilaz")
    uzmi("9")
    move(-(ISPRED - LICE))
    goto(1093, 850, name="ka kamenolomu 6")
    goto(1250, 850)
    dole(1250, "kamenolom 6")
    dole(750, "kamenolom 5")
except TimeUp:
    log("malo vremena: kuci")
go_home()
