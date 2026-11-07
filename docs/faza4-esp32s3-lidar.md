# Faza 4 (za kasnije): ESP32-S3 i lidar

Ostavljeno za kad stignu ESP32-S3-DevKitC-1 N16R8 i lidar (RPLIDAR A2). Oznake su iz
arhitektonskog pregleda ESP koda (vidi `docs/plan-esp.md`) i pregleda ekrana.

## Prelazak na ESP32-S3
- [ ] **S-1** `config.py` razdvojiti na pinove ploče (`board_wroom32.py`, `board_s3.py`) i ponašanje;
      izbor ploče jednim redom (`BOARD = "s3"`). Plan pinova za S3: UART1 17/18 (STM32), I2C 8/9,
      tasteri 4/5/6, enkoder 11/12/13, buzzer 14, NeoPixel 21, STM32 NRST 15 / BOOT0 16,
      E-STOP preko optokaplera 7, dodatni UART2 47/48 (lidar).
- [ ] **S-2** PSRAM menja ponašanje GC-a (veći heap, duže sakupljanje): izmeriti `gc.collect()` i krug
      petlje (STAT), po potrebi ručni `gc.collect()` u mirnim trenucima i `gc.threshold()`.
- [ ] MicroPython firmver za S3 (ESP32_GENERIC_S3, SPIRAM_OCT), ista verzija kao na WROOM-u (1.29) da
      `mpy-cross` u CI-ju ostane isti.
- [ ] USB na S3 (nativni USB-CDC): proveriti `mpremote` i Ctrl+C; `/dev/ttyACM*` umesto `/dev/ttyUSB0`.
- [ ] Fajl sistem: na WROOM-32 je spor (listdir ~380 ms, stat ~55 ms, open ~30 ms). Izmeriti na S3; ako
      ostane spor: keš sha256 u fajlu (preživi restart) i LIST samo za `/lib` i `/tactics`.
- [ ] Enkoder: hard IRQ je uveden; na S3 probati i PCNT (`machine.Encoder`/`esp32.PCNT`) ako postoji u firmveru.
- [ ] STM32 NRST/BOOT0 sa ESP-a (Nucleo): `config.STM_NRST`, `config.STM_BOOT0` (kod u `stmflash.py`
      postoji); stavka „Resetuj STM32“ u meniju, sa držanjem OK, zaključana od NAORUZAN do kraja meča.
- [ ] E-STOP signal na GPIO7: samo prikaz i prekid taktike (pravi E-STOP hardverski prekida motore, R-5).

## Svetlo i zvuk (iz pregleda ekrana, K-1, K-2)
- [ ] **K-1** NeoPixel (GPIO21): jedna tabela boja po stanju (ljubičasto sto, plavo izbor, crveno
      provera ne prolazi, žuto naoružan, zeleno spreman, belo puls meč, žuto treptanje blokiran, crveno
      treptanje STOP/greška, zeleno treptanje gotovo). Upis samo pri promeni stanja; svetlina u podešavanjima.
- [ ] **K-2** Buzzer (GPIO14): 1 kratak = potvrda, 2 = upozorenje, 3 = greška, dug = slaba baterija.
      PWM + raspored u petlji (bez sleep); u meču isključen osim greške; podešavanje uključen/isključen.

## Memorija i performanse (M-1..M-3, T-3)
- [ ] **M-1** manje alokacija u krugu petlje (STATUS dict, liste događaja, formatiranje teksta).
- [x] **M-2** `lib/` kao `.mpy` (esp_push, urađeno jer je na WROOM-32 RAM bio pun).
- [ ] frozen moduli u firmveru (kod iz fleša, ne iz RAM-a), ako ni na S3 ne bude dovoljno RAM-a.
- [ ] **M-3** `ticks_add` umesto `ticks_ms() + ms` svuda gde se računa rok.
- [ ] **T-3** I2C ekrana na 800 kHz-1 MHz (proveriti na komadu), slanje samo izmenjene stranice SSD1306
      (128 B umesto 1024 B).
- [ ] **U-3** veći ekran SSD1309 2,42" iste rezolucije: bez izmene koda.

## Lidar (L-1..L-3), na ESP32-S3, za taktike (ne za koliziju)
- [ ] **L-1** mesto u arhitekturi: `lib/lidar.py` kao servis u petlji (`Loop`), model podataka za taktike:
      `opponent()` -> (x, y, udaljenost, starost) u koordinatama terena, `seen(zona)`.
      LIDAR_SCAN iz protocol.yaml (lidar na STM32) obrisati ili označiti kao rezervisano u protokolu v3.
- [ ] **L-2** RPLIDAR A2: standardni SCAN (0x20), 115200 baud, 5 B po tački; parser u `@micropython.viper`
      ili native modulu, UART rxbuf dovoljan za najduži krug petlje (meriti STAT); pin za MOTOCTL (PWM motora).
      Test parsera na laptopu sa snimljenim podacima (`ESP32/sim/`), kao ostali host testovi.
- [ ] **L-3** sinhronizacija sa pozom: STATUS stiže na 20 Hz (do 50 ms kašnjenja); interpolacija poze po
      vremenu prijema, filtriranje tačaka van terena, grupisanje u protivnika.
- [ ] stavka „lidar“ na stranici PROVERA (GET_HEALTH, upozorenje).

## Van ESP-a (zavisi od drugih)
- [ ] Baterija preko INA3221 (prikaz na PROVERA i ROBOT, ikonica u traci): zavisi od hardvera.
- [ ] Bit CORD_IN (činč ubačen) u STATUS-u, protokol v3: tada stanje SPREMAN na ekranu.
- [ ] Protokol v3 (last_seq/last_result u STATUS, caps u PONG): u dogovoru sa Nucleo timom.
