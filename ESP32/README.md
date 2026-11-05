# ESP (eurokik) – koraci 1–3

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

## main.py: test protokola sa Nucleom
ESP svakih 150 ms šalje PING (heartbeat), a Nucleo odgovara sa PONG i svakih 50 ms šalje STATUS.
Na ekranu:
- `Nucleo OK v1`: veza radi i verzije protokola se poklapaju
- `x=… y=… th=…`: pozicija iz Nucleo odometrije (posle starta ESP pošalje SET_POSE 250, 1000, 0)
- `greske: N`: odbačeni paketi (CRC/COBS); treba da ostane 0

Ako piše `Nucleo: nema`: proveri TX/RX (ESP 17 → PA10, ESP 16 ← PA9), zajednički GND,
i da je na Nucleu flešovan kod sa comm.c. Oba su na 115200 baud-a.

## Prvo podešavanje
Kopiraj `secrets_example.py` u `secrets.py` i `webrepl_cfg_example.py` u `webrepl_cfg.py`,
pa upiši prave mreže i lozinke. Ta dva fajla se ne commit-uju.
