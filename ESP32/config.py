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

# SET_POSE posle povezivanja sa STM32 (mm, mm, stepeni); isključuje se u Podešavanjima
START_POSE = (250, 1000, 0)

WIFI_TIMEOUT_S = 10             # posle toga pravi sopstvenu mrežu
