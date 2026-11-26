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
}

# SET_POSE posle povezivanja sa STM32 (mm, mm, stepeni); isključuje se u Podešavanjima
START_POSE = (250, 1000, 0)

WIFI_TIMEOUT_S = 10             # posle toga pravi sopstvenu mrežu
