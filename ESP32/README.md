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
| taster enkodera | 14 | klik = OK |
| taster NAZAD | 25 | nazad; dugi (≥ 0,6 s) = meni (zaključan dok je robot naoružan ili meč traje) |
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
- Dugi NAZAD: meni (Podešavanja: kontrast, okretanje 180°, smer enkodera, gašenje, auto SET_POSE,
  "test od START", "WDT mec*" (važi do restarta), **demo taktika** = lažni koraci samo za prikaz).
- ROBOT, izveštaj i dnevnik su u koordinatama **naše strane** (kao taktika); telemetrija (tools/watch.py)
  u koordinatama terena.
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

## Probna vožnja (POKREĆE MOTORE)
    mpremote connect /dev/ttyUSB0 run tests/goto_test.py
Postavi pozu na (0, 0, 0) i pošalje GOTO 300 mm napred na 200 mm/s; ispisuje STATUS dok ne stigne
DONE/FAIL. Ctrl+C, 10 s bez završetka ili pad veze šalju STOP. Pre pokretanja: slobodno ispred robota,
ruka na prekidaču za motore. Posle testa `mpremote connect /dev/ttyUSB0 reset` vraća ekran.

## Bez kabla (WiFi)
Na ESP-u radi upload server (TCP 8267; prijava izazovom, lozinka iz `webrepl_cfg.py` se ne šalje)
i telemetrija (UDP 8268). Server ne blokira glavnu petlju; dok taktika radi ili je meč naoružan,
prima samo LOG, STOP i STAT.

    python tools/esp_push.py                # šalje samo izmenjeno, atomično (STAGE + COMMIT), pa restart
    python tools/esp_push.py --list         # samo prikaži razlike
    python tools/esp_push.py --prune        # i obriši .py iz lib/ i tactics/ kojih lokalno nema
    python tools/watch.py [--csv log.csv]   # poza, stanje, korak taktike i dnevnik uživo
    python tools/flash_stm32.py pogon-blackpill/Debug/PogonskiSTM-2026-BlackPill.elf

`lib/` se šalje prekompajliran (`.mpy`); treba `pipx install mpy-cross==1.29.0.post2` (ista verzija
kao firmver). Razlog: kompajliranje `.py` na ESP-u pri uvozu uzme toliko RAM-a da MicroPython heap
"pojede" memoriju WiFi drajvera i WiFi umre bez greške (izmereno: 1 KB ostane drajverima).
`main.py` zato prvo uključi WiFi i UART, pa tek onda uveze ostatak koda. Memorija se vidi u STAT.

`esp_push` prvo pita ESP šta ima (LIST, sha256 po fajlu), pošalje samo izmenjene fajlove u `/.new/`
sa proverom sha256, pa ih COMMIT sve odjednom stavi na mesto i upiše `/version.txt` (git describe;
vidi se u Meniju i u STAT). Prekid usred slanja ne ostavlja pola starog, pola novog koda.
Prvi LIST posle restarta traje ~10 s (fajl sistem na WROOM-32 je spor: listdir ~0.4 s, stat ~0.05 s),
sledeći par sekundi. Ako program na ESP-u padne, ESP ulazi u rescue režim: greška na ekranu,
a `esp_push` i dalje radi (popravka bez kabla).

## Taktike (bez kabla)
Taktika je fajl u `ESP32/tactics/` (vidi `primer.py`, `sve_komande.py`, `kamenolomi.py`). API se zove
**Gambit Micro** (kod je u `lib/tac.py`; `lib/gambit.py` je samo ime, pa radi i staro `from tac import *`):

    from gambit import *
    START = (250, 1000, 0)      # startna poza: ESP je postavi na činč, a i u testu (podešavanje test_start)
    TOTAL = 4                   # broj koraka, za ekran "2/4"
    goto(600, 1000, speed=300)  # True/False; deg=90 za završni ugao, reverse=True unazad
    turn_to(90)                 # apsolutni ugao terena;  turn_by(-45) relativno
    move(-200)                  # mm, minus = unazad
    ir_off("F"); ir_on()        # IR senzori F1-F4 napred, B1-B4 nazad (iznad kutija); ir_sees("F2") (protokol v5)
    wait(1); wait_until(lambda: ..., 3); step("čekam"); log("..."); here(); remaining()
    actuator("hvataljka", 1)                  # čeka DONE sa STM32; imena u config.ACTUATORS
    h = actuator("lift", 300, wait=False)     # paralelno sa vožnjom...
    goto(800, 1000); wait_done(h)             # ...pa sačekaj kraj (done(h): None/True/False)
    remaining(); match_time(); in_match(); attack_phase()   # vreme meča (u testu: od starta taktike)
    deadline(12)                              # kad ostane 12 s: tekuća komanda staje, baca TimeUp
    try:
        ...                                   # glavni posao
    except TimeUp:
        go_home()                             # centar svoje startne zone (pravila: kraj u zoni)

Jedinice: mm, stepeni (0° = +x, pozitivno = levo), mm/s, s. Timeout se sam računa iz dužine puta.
Taktika se piše za **žutu** stranu (leva, startna zona x 0..500 po pravilima 2027); na plavoj se koordinate same
ogledaju (x -> 3000 - x, ugao -> 180 - ugao).

Ako se ESP restartuje usred meča, a postoji `<taktika>_obnova.py` (npr. samo `go_home()`), ESP posle
restarta pokreće nju sa preostalim vremenom; bez nje robot stoji do kraja.

Ako se STM32 restartuje usred meča (watchdog, napajanje), ESP to vidi (v4: po `uptime_ms` u STATUS-u) i
jednom porukom RESUME mu vrati poslednju pozu i meč (STM32 nastavlja svoj sat od pravog trenutka); korak koji
je bio u toku vraća `False` ("RESTART"), taktika ide dalje. Kratak pad veze u meču: korak čeka povratak veze
i vraća pravi ishod (`True` ako je robot stigao, `False` "VEZA" ako je STM32 stao). Posle svakog kretanja
tac sačeka da robot stvarno stane (najviše 150 ms), pa `here()` vraća konačnu pozu.

Pokretanje odmah, kao test (sa laptopa preko WiFi-ja; šalje fajl, pokreće, ispisuje dnevnik):

    python tools/tactic.py primer [--side plava]  # Ctrl+C = STOP
    python tools/tactic.py --stop

Na robotu, početni ekran PROVERA (okret enkodera bira red, OK izvršava):
- **taktika** (spisak) -> **strana** (spisak, sa x startne poze) -> **provera** (šta ne valja: STM32, STATUS,
  taktika, START, aktuatori, stari meč na STM32...).
- **naoruzaj**: NAORUZAN, čeka **nov** činč (STM32 koji je ostao u starom meču se restartuje komandom RESET,
  pa preko NRST-a ako ga ima; stari STM32 bez NRST-a: naoružavanje se odbija). Na činč: START poza (do 3 pokušaja), pa taktika; meč traje 100 s po satu ESP-a.
  Bez činča (BlackPill): **simul. cinc** (drži OK). **otkazi**: drži OK (NAZAD više ne otkazuje).
- **test odmah**: drži OK; START poza kao u meču (podešavanje "test od START"), vreme teče od starta taktike.
- Posle kraja taktike pre 100 s meč i dalje traje: meni, test i upload ostaju zaključani do kraja.
Taster STOP uvek prekida taktiku i završava meč (otključava). Od NAORUZAN radi watchdog (ESP se sam
restartuje ako se zaglavi; isključuje se tek restartom), a opciono se gasi WiFi ("WiFi off mec").

Aktuatori: imena u `config.ACTUATORS`, levo/desno se menja na drugoj strani (`ACTUATOR_MIRROR`); **vrednost**
(npr. ugao ruke) se ne ogleda. BlackPill nema aktuatore: svaki `actuator()` tamo dobije "odbijeno".

## Provera na laptopu
    python -m pytest ESP32/tests/host     # host testovi (lažni STM32 i ekran iz ESP32/sim/)

## Konvencije (ESP kod)
- Komentari i tekst na ekranu na srpskom (latinica, bez kvačica na ekranu jer ih font nema).
- Jedinice: mm, stepeni u taktikama (cdeg u protokolu), mm/s, sekunde u taktikama, ms u kodu.
- Ništa ne sme da blokira glavnu petlju duže od ~100 ms (STM32 staje posle 500 ms bez PING-a):
  dugi poslovi se rade u delovima po krugu petlje (vidi upload.py LIST). Meri se: Meni/VEZA, STAT.
- Vreme samo iz `compat.py` (radi i na laptopu); hardver (machine, network) samo u modulima
  koji ga stvarno koriste, da bi ostalo moglo da se testira (`ESP32/sim/`, `ESP32/tests/host/`).
- Posle izmene: `python -m pytest ESP32/tests/host` i mpy-cross (CI radi oba).
- `protocol.py` se ne menja ručno (protocol/gen.py).
