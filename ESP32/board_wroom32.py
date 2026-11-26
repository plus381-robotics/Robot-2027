# Pinovi za ESP32 DevKit (WROOM-32, test ploča). Bira se u config.py (BOARD = "wroom32").

# UART2 ka STM32 (BlackPill)
UART_ID, UART_TX, UART_RX = 2, 17, 16

# I2C ekran (SSD1306 128x64)
I2C_ID, I2C_SDA, I2C_SCL = 0, 21, 22

# tasteri na GND (interni pull-up): nazad (dugo = početni ekran), OK, STOP (šalje STOP odmah)
BTN_BACK, BTN_OK, BTN_STOP = 25, 26, 27

# rotacioni enkoder: A, B, taster (None = nije povezan)
ENC_A, ENC_B, ENC_SW = 32, 33, 14

# STM32 NRST (open-drain, 0 = reset) i BOOT0. None = nije povezano (dijagram povezivanja: 18 = NRST, 19 = BOOT0).
STM_NRST, STM_BOOT0 = None, None
