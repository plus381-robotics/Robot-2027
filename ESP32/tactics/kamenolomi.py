# Od kamenoloma do kamenoloma na našoj (žutoj) polovini, pa kući. Kamenolom = gomila od 3 kamena
# (simulator/eurosim/field.py, QUARRIES). Piše se za žutu stranu; na plavoj se koordinate same ogledaju.
#
# IR senzori su iznad kutija (340 mm), pa kamenolome (330 mm) ne vide: robot prilazi do 4 cm, a protivnika
# (350 mm) i dalje vidi. Primer ir_off: posle uzimanja nazad bez zadnjih senzora (iza je naš put, prazan).
from gambit import *

START = (250, 1000, 0)
TOTAL = 25

LICE = 40              # mm između prednje ivice robota i kamenoloma na kraju prilaza
POLA = 82              # pola dužine robota (165 mm)
ISPRED = 230           # prvo stani toliko ispred, okrenut ka kamenolomu (ćošak robota ne sme da ga zakači pri
                       # okretu), pa pravo do njega
NAZAD = 230            # posle uzimanja: toliko nazad, da sledeći put bude slobodan


def uzmi(ime):
    actuator("hvataljka", 1, label="uzmi " + ime)      # na novom robotu: hvataljka; ovde samo pokazuje mesto


def odmakni():
    ir_off("B")                                        # nazad po putu kojim smo došli: zadnji senzori ne trebaju
    move(-NAZAD)
    ir_on()


def gore(x, ime):
    """Kamenolom uz gornju ivicu (y 1945, lice na 1890): prilaz odozdo, okrenut na 90°."""
    goto(x, 1890 - POLA - ISPRED, deg=90, name=ime)
    goto(x, 1890 - POLA - LICE, name=ime + " prilaz")
    uzmi(ime)
    odmakni()


def dole(x, ime):
    """Kamenolom uz donju ivicu (y 55, lice na 110): prilaz odozgo, okrenut na -90°."""
    goto(x, 110 + POLA + ISPRED, deg=-90, name=ime)
    goto(x, 110 + POLA + LICE, name=ime + " prilaz")
    uzmi(ime)
    odmakni()


deadline(12)                                           # kad ostane 12 s: prekid i kući
try:
    gore(750, "kamenolom 1")
    goto(750, 1150, name="ka kamenolomu 2")
    goto(1250, 1150)
    gore(1250, "kamenolom 2")
    goto(1445 - POLA - ISPRED, 1500, deg=0, timeout=6, name="kamenolom 9")   # srednji (1500, 1500), okrenut 90°
    goto(1445 - POLA - LICE, 1500, name="kamenolom 9 prilaz")
    uzmi("9")
    odmakni()
    goto(1093, 850, name="ka kamenolomu 6")
    goto(1250, 850)
    dole(1250, "kamenolom 6")
    dole(750, "kamenolom 5")
except TimeUp:
    log("malo vremena: kuci")
go_home()
