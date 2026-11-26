# Podešavanja ESP-a. Pinovi su u board_<ploča>.py; ploča se bira ovde jednim redom.
BOARD = "s3"                    # "s3" (ESP32-S3 N16R8, ESP32_Main) ili "wroom32" (test ploča)
if BOARD == "s3":
    from board_s3 import *      # noqa: F401,F403
else:
    from board_wroom32 import *  # noqa: F401,F403

HOSTNAME = "eurokik"            # dostupan kao eurokik.local
UART_BAUD = 115200              # na 921600 tek kad sve radi
ENC_STEPS = 4                   # prelaza enkodera po kliku (4 ili 2)

# STM32 NRST i BOOT0 (STM_NRST, STM_BOOT0 u board fajlu) služe za flešovanje kad softverski ulazak
# u bootloader ne radi. STM32 sa protokolom v4 ESP restartuje komandom RESET (pri naoružavanju, ako je
# ostao u starom meču); NRST je potreban samo kad se STM32 zaglavi i ne prima komande (u meču: reset pa
# obnova poze, lib/match.py) i kao rezerva ako RESET ne uspe. Stari STM32 (v1-v3) bez NRST-a: naoružavanje
# se odbija.

# Aktuatori na STM32 (komanda ACTUATOR id, value): ime -> id. Taktika piše actuator("hvataljka", 1).
# ACTUATOR_MIRROR: na drugoj strani terena (ogledanje) se levi i desni zamenjuju.
ACTUATORS = {"hvataljka": 1, "lift": 2, "ruka_l": 3, "ruka_r": 4}
ACTUATOR_MIRROR = {"ruka_l": "ruka_r", "ruka_r": "ruka_l"}

# Zvuci (lib/buzzer.py), RTTTL: "ime:d=trajanje,o=oktava,b=tempo:nota,nota,...", nota = [trajanje]slovo[#][.][oktava],
# p = pauza. Ovde se menjaju ili dodaju (dodati se čuju iz taktike: play("ime"), i u Meni -> test zvuka).
# Buzzer je najglasniji oko 2,4 kHz (oktave 6-7). Šta se ne navede, ostaje podrazumevano iz lib/buzzer.py.
SOUNDS = {
    "ok": "ok:d=16,o=7,b=200:d",                              # 1 kratak: potvrda
    "upoz": "upoz:d=16,o=7,b=200:d,p,d",                      # 2 kratka: upozorenje
    "greska": "greska:d=8,o=7,b=200:d,16p,d,16p,d",           # 3 kratka: greška, prekid
    "baterija": "baterija:d=2,o=6,b=120:g",                   # dug: slaba baterija
    "boot": "boot:d=16,o=6,b=180:c,e,g,8c7",                  # ESP pokrenut
    "start": "start:d=16,o=6,b=180:c,d,e,f,g,a,b,4c7",        # činč: meč kreće
    "kraj": "kraj:d=8,o=6,b=160:c7,g,e,4c",                   # kraj meča (100 s)
    "gotovo": "gotovo:d=16,o=6,b=200:e,g,8c7",                # test taktika završena bez greške
    # Paganini, Kapričo br. 24 (~43 s), oktavu više nego original da se čuje na buzzeru: play("paganini")
    "paganini": (
                 "paganini:d=16,o=7,b=186:8a6.,32a6,32p,16a6,16c7,16b6,16a6,8e7.,16e6,32e6,32p,16g#6,16f#6,16e6,"
                 "8a6.,32a6,32p,16a6,16c7,16b6,16a6,4e7,4e6,8a6.,32a6,32p,16a6,16c7,16b6,16a6,8e7.,16e6,32e6,32p,"
                 "16g#6,16f#6,16e6,8a6.,32a6,32p,16a6,16c7,16b6,16a6,4e7,4e6,8a7.,32a7,32p,16a7,16a#7,16a7,16g7,"
                 "8f7.,16d7,32d7,32p,16f7,16e7,16d7,8g7.,32g7,32p,16g7,16a7,16g7,16f7,8e7.,16c7,32c7,32p,16e7,16d7,"
                 "16c7,8f7.,16b6,32b6,32p,16d7,16c7,16b6,8e7.,16a6,32a6,32p,16c7,16b6,16a6,8f6.,16d#7,16e6,16e7,"
                 "16d7,16b6,4a6,4a5,32a7,32c8,16e8.,16c8.,16a7.,16e7.,16c7.,16a6,32e7,32g#7,16b7.,16g#7.,16e7.,"
                 "16b6.,16g6.,16e6,32a7,32c8,16e8.,16c8.,16a7.,16e7.,16c7.,16a6.,4e7,4e6,32a7,32c8,16e8.,16c8.,"
                 "16a7.,16e7.,16c7.,16a6,32e7,32g#7,16b7.,16g#7.,16e7.,16b6.,16g6.,16e6,32a7,32c8,16e8.,16c8.,"
                 "16a7.,16e7.,16c7.,16a6.,4e7,4e6,32c#8,32e8,16a8.,16e8.,16c#8.,16a7.,16e7.,16c7,32c6,32f6,16a6.,"
                 "16d7.,16f7.,16a7.,16d8.,16f8,32b7,32d8,16g8.,16d8.,16b7.,16g7.,16d7.,16b6,32c6,32e6,16g6.,16c7.,"
                 "16e7.,16g7.,16c8.,16e8,32f8,32d8,16b7.,16g#7.,16f7.,16d7.,16b6.,32g6,32e8,32c8,16a7.,16e7.,16c7.,"
                 "16a6.,16e6.,16c6,32d6,32f6,16b6.,16d7.,16f7.,16e6.,16e7.,16g#6.,4a6,4a5,16a6,16g#6,16a6,16g#6,"
                 "32a#6,16a6,16b6,16c7,16d7,16e7,16d#7,16e7,16d#7,32f7,16e7,16d7,16c7,16b6,16a6,16g#6,16a6,16g#6,"
                 "32a#6,16a6,16b6,16c7,16d7,16e7,16d#7,16e7,16d#7,32f7,8e7,8e6,16a6,16g#6,16a6,16g#6,32a#6,16a6,"
                 "16b6,16c7,16d7,16e7,16d#7,16e7,16d#7,32f7,16e7,16d7,16c7,16b6,16a6,16g#6,16a6,16g#6,32a#6,16a6,"
                 "16b6,16c7,16d7,16e7,16d#7,16e7,16d#7,32f7,8e7,8e6,16a7,16g#7,16a7,16g#7,32a#7,16a7,16g7,16f7,"
                 "16e7,16d7,16c#7,16d7,16c#7,32d#7,16d7,16e7,16f7,16d7,16g7,16f#7,16g7,16f#7,32g#7,16g7,16f7,16e7,"
                 "16d7,16c7,16b6,16c7,16b6,32c#7,16c7,16d7,16e7,16c7,16f7,16e7,16f7,16e7,32g7,16f7,16d7,16c7,16b6,"
                 "16e7,16d#7,16e7,16d#7,32f7,16e7,16c7,16b6,16a6,16b6,16a#6,16b6,16a#6,32c7,16b6,16f7,16e7,16g#6,"
                 "16a6,16g#6,16a6,16g#6,32b6,4a6,8c6.,8a6.,16a5,16a6,16c6,16g#6,16c6,16b6,8e6,8e7,8c6.,8c7.,16a5,"
                 "16a6,16b5,16b6,16d#6,16d#7,16f6,16f7,16e6,16e7,8c6.,8a6.,16a5,16a6,16c6,16g#6,16c6,16b6,8e6,8e7,"
                 "8c6.,8c7.,16a5,16a6,16b5,16b6,16d#6,16d#7,16f6,16f7,16e6,16e7,8a6.,8a7.,16c#6,16c#7,16d6,16d7,"
                 "16e6,16e7,16f6,16f7,16f#6,16f#7,8g6.,8g7.,16b5,16b6,16a5,16c7,16d6,16d7,16d#6,16d#7,16e6,16e7,"
                 "8f6.,8f7.,16b5,16b6,8e6.,8e7.,16a5,16a6,16b5,16b6,16f6,16f7,16e6,16e7,16g#5,16g#6,8b5,8b6,8a5,"
                 "8a6"),
}

# SET_POSE posle povezivanja sa STM32 (mm, mm, stepeni); isključuje se u Podešavanjima
START_POSE = (250, 1000, 0)

WIFI_TIMEOUT_S = 10             # posle toga pravi sopstvenu mrežu
