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
| taster enkodera | 14 | klik = OK, dugi klik = nazad |
| taster NAZAD | 25 | dugi = početni ekran |
| taster OK | 26 | |
| taster STOP | 27 | šalje STOP odmah, i kad je ekran ugašen |

Pinovi su u `config.py`. Ako enkoder pravi 2 koraka po kliku (ili 1 na 2 klika), promeni `ENC_STEPS`.

### Ekrani
- **Početni**: x, y (mm), ugao (°), brzina (mm/s), kompas sa smerom robota i stanje
  (`spreman`, `VOZI`, `BLOK`, `MEC`...). Desno gore: WiFi i veza sa STM32 (trepće `x` kad nema veze).
  Kad meč traje, gore piše koliko je sekundi ostalo. Klik ili okret otvara meni.
- **Meni**: Kretanje (STOP, GOTO, ROTATE, MOVE), Pozicija (SET_POSE), Meč, Debug,
  Veza STM32 (okviri, greške, ponavljanja, poslednji LOG), WiFi, Podešavanja, O uređaju.
- Broj se menja klikom pa okretanjem (brže okretanje = veći korak); OK potvrđuje, NAZAD vraća staru vrednost.
- **Komande kretanja traže držanje OK ~1 s** (traka se puni); puštanje ili NAZAD otkazuje.
- Odgovori STM32 se vide u traci na dnu: `GOTO OK`, `GOTO gotovo`, `OKRET: prepreka`, `POZA: nema odg.`
- Podešavanja (kontrast, okretanje ekrana, smer enkodera, gašenje ekrana, automatski SET_POSE
  posle povezivanja) se pamte u `settings.json` na ESP-u.

Posle povezivanja ESP jednom pošalje SET_POSE iz `config.START_POSE` (250, 1000, 0°);
isključuje se u Podešavanjima → auto poza.

Ako na početnom ekranu piše `cekam STM32...`: proveri TX/RX (ESP 17 → PA10, ESP 16 ← PA9),
zajednički GND, i da je na STM32 flešovan kod sa comm.c. Oba su na 115200 baud-a.

## Prvo podešavanje
Kopiraj `secrets_example.py` u `secrets.py` i `webrepl_cfg_example.py` u `webrepl_cfg.py`,
pa upiši prave mreže i lozinke. Ta dva fajla se ne commit-uju.
