# Sve komande Gambit Micro na jednom mestu (pregled, ne za meč). Piše se za ŽUTU stranu; na plavoj se samo ogleda.
# Objašnjenja: u simulatoru Editor -> 📖 Commands.
from gambit import *

START = (250, 1000, 0)        # x, y [mm], ugao [°]: odavde robot kreće (ESP je postavlja na činč)
TOTAL = 16                     # koliko koraka očekujemo (za traku napretka na ekranu)

deadline(15)                   # kad do kraja meča ostane 15 s, tekuća komanda baca TimeUp
try:
    log("strana %s, u mecu %s" % (side(), in_match()))
    pose(250, 1000, 0)                              # ručno postavi odometriju (u meču to radi START)
    step("priprema")                                # korak bez kretanja, samo natpis na ekranu
    h = actuator("lift", 100, wait=False)           # aktuator radi dok robot vozi
    goto(600, 1000, speed=400)                      # vozi do tačke (x, y)
    wait_done(h)                                    # sačekaj aktuator pokrenut sa wait=False
    turn_to(90)                                     # okreni se ka 90° (apsolutno, ka +y)
    turn_by(-45)                                    # okreni se za -45° od trenutnog ugla
    rotate(0)                                       # staro ime za turn_to
    move(200)                                       # pravo 200 mm napred
    move(-200, speed=200)                           # 200 mm nazad, sporije
    goto(500, 1200, deg=180, name="tacka B", next="nazad")   # do tačke i na kraju okret na 180°
    goto(700, 1000, reverse=True)                   # do tačke vožnjom unazad
    goto(700, 1300, deg=90)
    ir_off("FD")                                    # donji prednji IR ne zaustavljaju robota (i dalje mere)
    move(100)
    ir_on()                                         # svi IR ponovo uključeni (i sami na kraju taktike)
    if ir_sees("BU"):                               # gornji zadnji senzor sada vidi nešto (protivnik?)
        log("nesto je iza")
    actuator("hvataljka", 1)                        # aktuator, čeka da završi (True/False)
    h2 = actuator("ruka_l", 50, wait=False)
    wait_until(lambda: done(h2) is not None, 2, name="ruka")  # čekaj uslov, najviše 2 s
    wait(0.5)                                       # pauza
    x, y, ugao = here()                             # gde je robot (u koordinatama naše strane)
    log("here %d %d %d" % (x, y, ugao))
    log("status %s" % (status(),))                  # sirov STATUS sa STM32 (teren, cdeg)
    log("vreme %s, ostalo %s, napad %s" % (match_time(), remaining(), attack_phase()))
except TimeUp:
    log("malo vremena: kuci")
go_home()                                           # u startnu zonu (pravila: kraj u svojoj zoni)
