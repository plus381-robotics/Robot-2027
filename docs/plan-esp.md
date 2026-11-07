# Plan unapređenja ESP koda

Izvor: arhitektonski pregled ESP32 koda (45 nalaza, oznake A/T/R/P/K/M/U/W/S/L/Q/D).
Obim: samo ESP32 (BlackPill robot služi za razvoj ESP koda i protokola). Svaka ispravka ima host test
u `ESP32/tests/host/` (`python -m pytest ESP32/tests/host`), CI je `.github/workflows/esp32.yml`.

## Faza 0: osnova za testiranje
- [x] Q-2 simulator i lažni STM32 u repou (`ESP32/sim/`), host testovi
- [x] Q-1 CI: mpy-cross 1.29, protokol u skladu sa yaml-om, host testovi
- [x] A-3 `compat.py` (vreme isto na ESP-u i laptopu, lažni sat za testove)
- [x] A-4 `main.py` u `def main()`

## Faza 1: bezbednost i očigledne greške
- [x] P-1 ponavlja se samo poslednja komanda (GOTO više ne može posle STOP-a)
- [x] P-3 kretanje bez odgovora -> STOP i čekanje ACK-a
- [x] K-1 STOP briše izabranu taktiku; meni Taktike zaključan dok taktika radi
- [x] R-3 auto SET_POSE samo van meča, kad robot ne vozi i ne radi taktika
- [x] R-1 rescue režim (greška na ekranu, WiFi + upload rade), taktika hvata i SystemExit
- [ ] R-1 machine.WDT samo u meču (ide uz K-4, faza 2)
- [x] A-2, T-1 (1) dok radi taktika upload prima samo LOG/STOP/STAT; timeout 0.5 s / 3 s
- [x] P-4 ESP prihvata protokol v1 i v2, `robot.can("bootloader")`
- [x] U-1 enkoder na hard IRQ (sa rezervom na soft)
- [x] T-2 merenje petlje: stranica VEZA (krug, PING) i upload `STAT`

## Faza 2: taktike i tok meča
- [ ] A-1 podela app.py: match.py, runner.py (urađeno), pages.py
- [ ] K-2 API: turn_to/turn_by, timeout iz dužine puta, here(), step(), __all__, total
- [ ] K-3 strana terena (x -> 3000 - x, theta -> 180 - theta)
- [ ] K-4 izbor taktike -> strana -> čeka se činč (MATCH_RUNNING) -> SET_POSE -> taktika; WDT u meču
- [ ] P-2 kraj kretanja i iz bita MOVING
- [ ] K-5, U-2, W-4

## Faza 3: WiFi i alati
- [ ] T-1 (2) neblokirajući upload server
- [ ] R-2 atomičan upload (/lib.new, SHA-256, COMMIT), LIST, version.txt
- [ ] W-1, W-2, R-4, W-3, Q-3, D-1, D-2

## Faza 4: ESP32-S3 i lidar
- [ ] S-1, S-2, M-1..M-3, T-3, U-3, L-1..L-3

## Van ESP koda (predlog, ne radi se ovde)
- protokol v3 (last_seq/last_result u STATUS, caps u PONG, CORD_IN), P-1 na STM32,
  R-5 hardverski E-STOP, Nucleo protocol.h (Lea), "Resetuj STM32" (kad bude Nucleo sa NRST)

## Izmereno na robotu (WROOM-32, posle faze 1)
ekran do 35 ms, krug petlje do 45 ms, najduža pauza PING-a 158 ms (STM32 staje posle 500 ms).
