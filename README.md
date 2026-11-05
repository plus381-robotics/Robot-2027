# Robot-2027

[![yt video koji objasnjava repo](https://img.youtube.com/vi/ONZMAUEJe-c/0.jpg)](https://www.youtube.com/watch?v=ONZMAUEJe-c)


## Struktura

| Folder | Uređaj | Sadržaj |
|---|---|---|
| [`nucleo/`](nucleo/) | STM32 Nucleo F401RE | firmware za kretanje (CubeMX + CMake) |
| [`ESP32/`](ESP32/) | ESP32 (test: WROOM-32, kasnije ESP32-S3) | taktike, OLED, tasteri, enkoder, NeoPixel, WiFi |
| [`protocol/`](protocol/) | oba | `protocol.yaml` je jedini opis poruka; `python protocol/gen.py` pravi `protocol.h` i `protocol.py` |
