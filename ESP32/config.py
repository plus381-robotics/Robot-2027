# Pinovi za ESP32 DevKit (WROOM-32). Za ESP32-S3 se menja samo ovaj fajl.
BOARD = "wroom32"
HOSTNAME = "eurokik"            # dostupan kao eurokik.local

# UART2 ka Nucleu
UART_ID, UART_TX, UART_RX = 2, 17, 16
UART_BAUD = 115200              # na 921600 tek kad sve radi

# I2C ekran (SSD1306 128x64)
I2C_ID, I2C_SDA, I2C_SCL = 0, 21, 22

# tasteri na GND (interni pull-up): nazad (dugo = početni ekran), OK, STOP (šalje STOP odmah)
BTN_BACK, BTN_OK, BTN_STOP = 25, 26, 27

# rotacioni enkoder: A, B, taster (None = nije povezan). STEPS: prelaza po kliku (4 ili 2).
ENC_A, ENC_B, ENC_SW = 32, 33, 14
ENC_STEPS = 4

# STM32 NRST (open-drain) i BOOT0 za flešovanje kad softverski ulazak u bootloader ne radi.
# None = nije povezano (vidi dijagram povezivanja: 18 = NRST, 19 = BOOT0).
STM_NRST, STM_BOOT0 = None, None

# Aktuatori na STM32 (komanda ACTUATOR id, value): ime -> id. Taktika piše actuator("hvataljka", 1).
# ACTUATOR_MIRROR: na drugoj strani terena (ogledanje) se levi i desni zamenjuju.
ACTUATORS = {"hvataljka": 1, "lift": 2, "ruka_l": 3, "ruka_r": 4}
ACTUATOR_MIRROR = {"ruka_l": "ruka_r", "ruka_r": "ruka_l"}

# SET_POSE posle povezivanja sa STM32 (mm, mm, stepeni); isključuje se u Podešavanjima
START_POSE = (250, 1000, 0)

WIFI_TIMEOUT_S = 10             # posle toga pravi sopstvenu mrežu
