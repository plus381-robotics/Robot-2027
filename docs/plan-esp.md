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
- [x] R-1 machine.WDT od NAORUZAN do restarta (podešavanje "WDT u mecu", faza 2)
- [x] A-2, T-1 (1) dok radi taktika upload prima samo LOG/STOP/STAT; timeout 0.5 s / 3 s
- [x] P-4 ESP prihvata protokol v1 i v2, `robot.can("bootloader")`
- [x] U-1 enkoder na hard IRQ (sa rezervom na soft)
- [x] T-2 merenje petlje: stranica VEZA (krug, PING) i upload `STAT`

## Faza 2: taktike i tok meča
- [x] A-1 podela app.py: pages.py (ekrani), match.py (tok meča), runner.py (petlja, taktika)
- [x] K-2 API: turn_to/turn_by, timeout iz dužine puta, here(), step(), wait_until(), remaining(), __all__, TOTAL
- [x] K-3 strana terena (x -> 3000 - x, ugao -> 180 - ugao), `--side` u tools/tactic.py
- [x] K-4 izbor taktike -> strana -> NAORUZAN (čeka činč) -> START poza -> taktika; simulirani činč; WDT
- [x] P-2 kraj kretanja i iz bita MOVING kad DONE ne stigne
- [x] W-4 opcija "WiFi off mec"
- [x] U-2 (deo) ekran "CEKA CINC", strana u naslovu
- [x] K-5 Abort je BaseException (`except Exception` u taktici ne guta STOP), "ponovi" u meniju,
      prevedena taktika se pamti dok se fajl ne promeni
- [x] K-6 aktuatori: actuator(ime, vrednost) čeka DONE; wait=False + done()/wait_done() paralelno sa
      vožnjom; imena u config.ACTUATORS, levo/desno se menja na drugoj strani (ACTUATOR_MIRROR).
      robot.py prati DONE i za aktuatore i pamti ishode; zamenjena komanda prihvata kasni ACK.
      Na BlackPill-u (bez aktuatora) STM32 odgovara FAIL INVALID, provereno na robotu.

## Faza 3: WiFi i alati
- [x] T-1 (2) upload server kao automat stanja (BUDGET po krugu, LIST u koracima od ~20 ms)
- [x] R-2 atomičan upload: STAGE u /.new sa sha256, COMMIT, LIST, DEL, /version.txt; rescue i bez lib.old
- [x] W-1 prijava izazovom (sha256(lozinka + nonce)), samo dozvoljene putanje, DEL samo .py
- [x] W-2 klijent: ponavljanje bezbednih komandi, jasne greške; WiFi bez štednje energije
- [x] R-4 WiFi se ponovo povezuje posle 5 s bez veze (ikonica opet trepće)
- [x] W-3 telemetrija UDP 8268 (tools/watch.py, i CSV)
- [x] Q-3, D-1, D-2 alati, README, konvencije
- [ ] (otkriveno) fajl sistem na WROOM-32 je spor (listdir ~380 ms, stat ~55 ms, open ~30 ms):
      proveriti na S3; ako ostane, keš sha preko restarta (fajl) ili LIST samo za lib/ i tactics/

## Faza 4: ESP32-S3 i lidar
- [ ] S-1, S-2, M-1..M-3, T-3, U-3, L-1..L-3

## Van ESP koda (predlog, ne radi se ovde)
- protokol v3: ✅ last_seq/last_result u STATUS (comm.c na BlackPill-u i Nucleo, ESP prima i stari STATUS);
  ostaje: caps u PONG, CORD_IN, P-1 na STM32,
  R-5 hardverski E-STOP, Nucleo protocol.h (Lea), "Resetuj STM32" (kad bude Nucleo sa NRST)

## Izmereno na robotu (WROOM-32)
- posle faze 1: ekran do 35 ms, krug petlje do 45 ms, najduža pauza PING-a 158 ms (STM32 staje posle 500 ms)
- posle faze 2: ekran do 41 ms, krug do 45 ms, PING do 200 ms; `provera` na žutoj strani: poza ogledana (2750, 180°)

## Rework ekrana (pregled ekrana, faza 1 i 2)
- [x] O-1 osnova: jedna tabela kontrola (I-1), traka radnje (I-3), nivoi poruka (G-1: toast, greške sa
      ! u traci, prekid preko celog ekrana), krupan tekst (P-1), puls i zastareli podaci (G-2), slanje
      slike samo na promenu (T-1), rečnik natpisa `lib/tekst.py` (P-3), pamćenje izbora
- [x] S-1, S-3 stranice u krugu: PROVERA (prva), TAKTIKA, KORACI, ROBOT, VEZA, DNEVNIK, IZVESTAJ;
      stanje meča bira stranicu, posle 10 s bez dodira u meču nazad na stranicu stanja
- [x] S-2 TAKTIKE -> STRANA -> PROVERA, izbor se pamti; meni na dugi NAZAD, zaključan u meču
- [x] M-1 ekran u meču: miran / ugasen / detaljan
- [x] V-1 IZVESTAJ (ishod, koraci, veza, kraj) posle svake taktike, čuva se u /mec (20), meni Mecevi
- [x] I-2 okret enkodera budi ekran i izvrši se; OK/NAZAD samo bude
- [ ] T-2 pun "model prikaza" (sada: crtanje u memoriju + poređenje slike); `ESP32/sim/render.py` crta sve ekrane
- [ ] K-1, K-2 NeoPixel i buzzer (na S3, vidi docs/faza4-esp32s3-lidar.md)
- [ ] baterija (INA3221) i činč (CORD_IN) na PROVERA: čekaju hardver / protokol v3

## Otkriveno na robotu (novembar 2026)
- Fajl sistem je bio oštećen ili zagušen (listdir ~380 ms): ponovo napravljen (mkfs), sada ~3 ms.
- Pravi uzrok zaglavljivanja WiFi-ja: RAM. Kompajliranje modula na ESP-u širi MicroPython heap na račun
  memorije drajvera (ostane 1 KB) -> WiFi bez memorije za prijem. Rešeno: lib/ kao .mpy (M-2), WiFi i
  UART pre uvoza koda, prijem fajla i poređenje ekrana bez novih alokacija, gc.threshold.
  Sada: heap ~25 KB slobodno, drajveri ~17 KB; STAT pokazuje oboje.
- [ ] Pri pokretanju taktike PING pauza do ~590 ms (prevođenje taktike na ESP-u): taktike slati kao .mpy
      ili prevesti pre naoružavanja, da STM32 ne proglasi pad veze na startu.
- [ ] RAM je tesan na WROOM-32 (~100 KB koda i podataka): S3 sa PSRAM-om rešava; do tada ne dodavati velike module.
