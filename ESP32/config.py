# Pinovi za ESP32 DevKit (WROOM-32). Za ESP32-S3 se menja samo ovaj fajl.
BOARD = "wroom32"
HOSTNAME = "eurokik"            # dostupan kao eurokik.local

# UART2 ka Nucleu
UART_ID, UART_TX, UART_RX = 2, 17, 16
UART_BAUD = 115200              # na 921600 tek kad sve radi

# I2C ekran (SSD1306 128x64)
I2C_ID, I2C_SDA, I2C_SCL = 0, 21, 22

# tasteri na GND (interni pull-up)
BTN = (25, 26, 27)

WIFI_TIMEOUT_S = 10             # posle toga pravi sopstvenu mrežu
