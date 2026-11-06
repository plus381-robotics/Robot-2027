# ESP (eurokik)

## Prvi put (preko USB-a)
    mpremote connect /dev/ttyUSB0 mip install ssd1306
    mpremote connect /dev/ttyUSB0 fs cp -r lib :
    mpremote connect /dev/ttyUSB0 fs cp config.py secrets.py webrepl_cfg.py boot.py main.py :
    mpremote connect /dev/ttyUSB0 reset

Ekran treba da pokaže `eurokik.local`, IP adresu i na koju mrežu se povezao.
Mreže su u `secrets.py` (YU.net kod kuće, `.` u labu). Ako ne nađe nijednu, pravi svoju mrežu `eurokik`.

## Posle toga (preko WiFi-ja)
- `ping eurokik.local`
- Thonny → Run → Configure interpreter → MicroPython (ESP32) → port: WebREPL,
  URL `ws://eurokik.local:8266`, lozinka iz webrepl_cfg.py
- Ako ruter nije dostupan: poveži laptop na mrežu `eurokik`, ESP je na `192.168.4.1`.

## Ako mpremote javi "could not enter raw repl"
Ploča je zauzeta (radi main.py). Pokreni `mpremote connect /dev/ttyUSB0 repl`, pritisni Ctrl+C,
izađi sa Ctrl+] i odmah ponovi komandu.

## main.py: meni + veza sa STM32
ESP svakih 150 ms šalje PING (heartbeat), a STM32 (Nucleo ili BlackPill) odgovara sa PONG
i svakih 50 ms šalje STATUS. Komanda se ponavlja do 3 puta ako ACK ne stigne za 60 ms.

### Povezivanje (WROOM-32, sve na GND sa internim pull-up)
| Šta | ESP pin | Napomena |
|---|---|---|
| enkoder A / B | 32 / 33 | ako se okreće naopako: Podešavanja → obrni smer |
| taster enkodera | 14 | dugi klik = podešavanja / nazad |
| taster NAZAD | 25 | podešavanja / nazad, dugi = početni ekran |
| taster OK | 26 | |
| taster STOP | 27 | šalje STOP odmah, i kad je ekran ugašen |

Pinovi su u `config.py`. Ako enkoder pravi 2 koraka po kliku (ili 1 na 2 klika), promeni `ENC_STEPS`.

### Ekran (telemetrija na robotu)
Okret enkodera menja stranicu; crta ispod naslova pokazuje na kojoj si.
- **TAKTIKA**: trenutni korak (`3/12 GOTO kocka B`), traka trajanja u odnosu na timeout
  (trepće kad ga pređe), sledeći korak, ishod i trajanje prethodnog. Kad taktika krene,
  ekran sam prelazi ovde. Bez taktike: poslednji korak, pozicija i stanje robota.
- **KORACI**: poslednja 4 koraka sa ishodom i trajanjem.
- **ROBOT**: x, y (mm), ugao (°), v (mm/s), stanje (`VOZI`, `BLOK`, `MEC`...) i starost STATUS-a.
- **VEZA**: STM32 i verzija, okvira/s, CRC greške, ponavljanja, komande bez odgovora, IP.
- Gore desno: preostalo vreme meča (inverzno poslednjih 10 s), WiFi i veza sa STM32 (trepće `x` kad nema).
- Dugi klik enkodera ili NAZAD: podešavanja ekrana (kontrast, okretanje 180°, smer enkodera,
  gašenje, auto SET_POSE, **demo taktika** = lažni koraci samo za prikaz, ništa se ne šalje robotu).
- Greške sa STM32 (FAIL, komanda bez odgovora) iskaču u traci na dnu.

Taktike javljaju korake preko `lib/tactic.py`:

    from tactic import tracker
    tracker.start("Plava", total=12)
    tracker.step("GOTO kocka B", timeout=3.0, next="ROTATE 90")
    tracker.fail("BLOCKED")    # ili tracker.ok(); sledeći step() zatvara prethodni kao OK
    tracker.finish()

Posle povezivanja ESP jednom pošalje SET_POSE iz `config.START_POSE` (250, 1000, 0°);
isključuje se u Podešavanjima → auto poza.

Ako na početnom ekranu piše `cekam STM32...`: proveri TX/RX (ESP 17 → PA10, ESP 16 ← PA9),
zajednički GND, i da je na STM32 flešovan kod sa comm.c. Oba su na 115200 baud-a.

## Prvo podešavanje
Kopiraj `secrets_example.py` u `secrets.py` i `webrepl_cfg_example.py` u `webrepl_cfg.py`,
pa upiši prave mreže i lozinke. Ta dva fajla se ne commit-uju.
