# Pinovi za Waveshare ESP32-S3-DEV-KIT-N16R8 na ploči ESP32_Main (Robot-elektronika-2027).
# Bira se u config.py (BOARD = "s3"). Ploča je pin-kompatibilna sa ESP32-S3-DevKitC-1.
# Ne koristiti: 0, 3, 45, 46 (strapping), 19/20 (USB), 43/44 (UART0 = REPL preko CH343), 35-37 (PSRAM).
# Imena mreža iz šeme su u komentarima. Pretpostavka: sufiks govori čiji je pin
# (TX_ESP = TX ESP-a, TX_LIDAR = TX lidara). Proveriti sa šemom.

# UART1 ka STM32 (Nucleo), konektor J6: TX_ESP = 40, RX_ESP = 39
UART_ID, UART_TX, UART_RX = 1, 40, 39

# I2C ekran (SSD1306 128x64), konektor J5: SDA_display = 12, SCL_display = 14
I2C_ID, I2C_SDA, I2C_SCL = 0, 12, 14
# ekran je na robotu montiran naopako: slika se okreće za 180° (Meni -> "okreni 180" okreće još jednom)
DISPLAY_ROT180 = True

# tasteri na GND (interni pull-up), J5: BACK = 18, OK = 11, STOP = 17
BTN_BACK, BTN_OK, BTN_STOP = 18, 11, 17

# rotacioni enkoder, J5: ENC_A = 10, ENC_B = 9, ENC_BTN = 8
ENC_A, ENC_B, ENC_SW = 10, 9, 8

# STM32 NRST = 15, BOOT0 = 16 (konektor J2). NRST ide preko N-MOSFET-a Q1, pa je obrnut:
# 1 na ESP pinu = STM32 u resetu (lib/nrst.py).
STM_NRST, STM_BOOT0 = 15, 16
STM_NRST_INV = True

# RGB LED (WS2812) na Waveshare ploči, stanje robota (lib/led.py); isti pin izlazi i na J4
NEOPIXEL = 38

# pasivni buzzer (PWM_BUZZ, J5), lib/buzzer.py; zvuci (RTTTL) su u config.SOUNDS
BUZZER = 13

# LIDAR (RPLIDAR A2M8, 115200 baud) na UART2, konektor J3: TX_LIDAR = 21 (ide na ESP RX), RX_LIDAR = 47
# (ESP TX), MOTOCTL_LIDAR = 48 (PWM motora). lib/lidar.py, Meni -> "Lidar test".
LIDAR_UART, LIDAR_TX, LIDAR_RX, LIDAR_MOTOCTL = 2, 47, 21, 48
LIDAR_BAUD = 115200
LIDAR_MOTOR_HZ, LIDAR_MOTOR_DUTY = 25000, 60     # PWM motora: frekvencija, popuna u % (A2: ~60 % = ~10 Hz)
LIDAR_MOUNT_DEG = 0              # gde gleda 0° lidara, u uglu robota (0 = napred, + = levo)

# --- još ne koristi kod (pinovi su rezervisani na ploči) ---
I2C_PB_ID, I2C_PB_SDA, I2C_PB_SCL = 1, 7, 6    # I2C ka PowerBoard-u (INA3221), J8
ADC_VBAT, ADC_VMOT = 4, 5        # VBAT_SENSE, VMOT_SENSE (ADC1, radi i uz WiFi), J8
