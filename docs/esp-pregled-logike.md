# ESP32 kod: pregled logike i smislenosti

> **Rešeno posle pregleda:** L1, L2, L7 (`lib/match.py`: meč samo na nov činč; stari meč na STM32 se
> resetuje preko NRST sa ESP-a ili se naoružavanje odbija; ESP sat meča zaustavlja posle 100 s; restart
> STM32 u meču: vraćanje poze (+25 ms procene) i MATCH_START, prekinut korak vraća False "RESTART";
> STM32 koji se ne javlja 1,5 s: NRST; restart ESP-a u meču: robot stoji i javlja). Testovi:
> `ESP32/tests/host/test_mec_zastita.py`, `simulator/tests/test_match_guard.py`.
> L6: protokol v3: STATUS nosi `last_seq`/`last_result` (ishod poslednje završene komande kretanja), pa
> ESP zna tačan ishod i kad se DONE/FAIL izgubi; sa starim STM32 (v1/v2) ostaje procena, označena u dnevniku.
> L3 (START sa 2 broja, tačna imena, nečitljiv START crven u PROVERA), L4 (NAZAD ne otkazuje; "otkazi" + drži OK;
> činč bez naoružavanja -> alarm), L5 (PROVERA prevodi ponovo kad se fajl promeni; prevod pri naoružavanju),
> L8 (meč zaključan do 100 s i kad taktika završi ranije; STOP namerno otključava), L9 (kraj meča = "MEC GOTOV",
> bez alarma i grešaka; MATCH_OVER odmah završava taktiku), L14 (odbijena START poza: STOP i ponovo do 3 puta,
> greške se brišu pri naoružavanju). Testovi: `ESP32/tests/host/test_mec_zastita.py`.
> L10 (test postavlja START pozu, podešavanje test_start), L11 (remaining/match_time i u testu, in_match, 0 posle
> kraja), L12 (attack_phase, deadline + TimeUp, go_home; obnova posle restarta ESP-a: `<taktika>_obnova.py`),
> L15 (actuator wait=False čeka ACK), L18 (uglovi -180..180, mm/s celi brojevi), L19 (turn_by > 170° u više
> okreta), L20 (speed 150..1500, 0 = greška), L21 (primer TOTAL). Testovi: `ESP32/tests/host/test_tac_api.py`.
> L13 (držanje OK na ugašenom ekranu ga samo pali; potvrda se zatvara posle 10 s i pri gašenju), L22 (ROBOT i
> izveštaj u koordinatama naše strane, teren posebno), L24 ("RADI" između koraka; u meču PROVERA bez otkazivanja),
> L25 (isto ime i prevedeni razlog u traci i dnevniku, greška van taktike bez vremena, izvor STOP-a), L28 (ko je
> zastareo), L30 (strana sa spiska, test pokazuje stranu, "WDT mec*", lista mečeva sa imenom i M/T).
> Testovi: `ESP32/tests/host/test_ekran_logika.py`.
> L16 (tools/tactic.py uvek šalje stranu, podrazumevano žuta), L17 (pad veze usred komande: False "VEZA" posle
> 300 ms; u meču sledeća komanda čeka povratak veze i taktika nastavlja), L23 (PROVERA proverava imena aktuatora;
> README: BlackPill bez aktuatora, vrednosti se ne ogledaju), L26 (README, primer, provera, rescue, config,
> protocol.yaml usklađeni sa kodom), L27 (auto poza pri svakom povezivanju STM32, ogledana po strani), L29
> (tools/tactic.py: pad mreže -> STOP i jasna poruka; LOG javlja preskočene redove).
> Testovi: `ESP32/tests/host/test_veza_alati.py`. **Svih 30 nalaza je obrađeno.**
>
> **Protokol v4 (posle pregleda, bolja rešenja za L1, L2, L17 i PROBLEMI 2/4):** komanda `RESET` (stari meč
> se čisti bez NRST pina; NRST ostaje za zaglavljen STM32), `uptime_ms` u STATUS-u (restart STM32 se vidi
> sigurno, ne po bitovima meča), `RESUME` (poza + meč od `elapsed_ms` jednom porukom; STM32 sam staje na
> 100 s), `reset_cause` u PONG-u (u dnevniku: watchdog, NRST, napajanje, softver), `Reason.LINK` (posle pada
> veze ESP čeka povratak i čita pravi ishod umesto da posle 300 ms proglasi neuspeh), `w` u STATUS-u (posle
> DONE čeka se da robot stane). Izbačene nekorišćene poruke (DEBUG_STREAMS, LIDAR_SCAN, CONTROL_DEBUG,
> TACTIC_EVENT) i bit LINK_LOST. Nucleo sam kreće meč na izvlačenje činča. Stari STM32 (v1-v3) radi kao ranije.

Datum: 2026-11-08. Obim: `ESP32/lib/*.py`, `ESP32/main.py`, `boot.py`, `config.py`, `ESP32/tactics/*.py`,
`ESP32/tests/goto_test.py`, `tools/*.py`, `protocol/protocol.yaml`, a za drugu stranu veze
`pogon-blackpill/Core/Lib/comm.c` i `comm_port.c`. Pravila: Eurobot 2027 (meč 100 s, faza napada od
85. s, robot mora da završi zaustavljen u svojoj startnoj zoni "throne room", 50 x 50 cm).

Cilj nije bio samo naći greške, nego i **nesmislena ili nedosledna rešenja**: ponašanje koje iznenadi na
stolu ili u meču, pogrešne pretpostavke, UX ekrana koji vodi u grešku, stvari koje rade "slučajno".

**Nije ponovljeno** (već postoji): sve iz `ESP32/PROBLEMI.md` (1-9) i `docs/esp-ciscenje-analiza.md`
(mrtav kod, RAM, WDT posle meča + FLASH/COMMIT, restart ESP-a u meču koji ostavlja robota da stoji,
"WiFi off mec" mimo `net.py`, taktika bez čekanja, lozinka u čistom tekstu, `esp_push` i `ERR` na LIST...).
Nisu analizirani ni `tactics/x100.py` ni `try` po servisu u `runner.Loop.step` (ispravljaju se odvojeno).
Gde se nalaz nadovezuje na postojeći, to je navedeno.

**Napomena o stanju repoa.** Tokom pregleda su u radnom stablu bile tuđe izmene (`try` po servisu u
`ESP32/lib/runner.py`, `ESP32/main.py`, `ESP32/tactics/x100.py`, `simulator/eurosim/esp.py`,
`ESP32/tests/host/test_runner.py`), koje su u međuvremenu commit-ovane kao `ecd9aba`. Eksperimenti su
rađeni nad tim stanjem; brojevi linija se odnose na `ecd9aba`. Ovaj pregled nije menjao nijedan fajl
osim ovog izveštaja.

## Kako je provereno

- Host testovi: `python -m pytest -q ESP32/tests/host` → **51 passed** (0,53 s), pre i posle eksperimenata.
- Male skripte (sve u `/tmp/claude-0/-home-user-Robot-2027/1c28f103-9ba4-505a-9d31-a07306e7d746/scratchpad/exp/`):
  - `hostenv.py`: isto okruženje kao `ESP32/tests/host/conftest.py` (pravi `App`, `Robot`, `runner`,
    lažni sat, `ESP32/sim/fakestm.py`); skripte `a1_*.py` ... `a7_*.py`.
  - `simenv.py`: simulator (`eurosim.sim.Sim`, live režim, komande kao u `simulator/tests/test_live.py`,
    plus funkcije koje u zadatom trenutku menjaju simulirani STM32); skripte `b1_*.py` ... `b7_*.py`,
    taktike za eksperimente u `exp/tac/` (`dugo.py`: GOTO tamo-amo dok ne istekne meč; `daleko.py`:
    jedan GOTO na 1500 mm).
- Rezultati su citirani uz svaki nalaz ("DOKAZ"). Gde piše "nije provereno", zaključak je iz koda.

---

## Tabela nalaza

| # | Ozbiljnost | Nalaz | Gde |
|---|---|---|---|
| L1 | **visoka** | Naoružavanje ne proverava da li STM32 već broji meč: taktika krene odmah, bez činča, i START poza pregazi odometriju | `match.py:50-63,80` |
| L2 | **visoka** | Restart STM32 usred meča: ESP ne primeti, robot vozi i posle 100 s sa odometrijom od 0,0,0 | `match.py:97-101`, `tac.py:126-131`, `comm_port.c:53-97` |
| L3 | **visoka** | `START` sa 2 broja ili promenljiva čije ime počinje sa `START`/`TOTAL`: meč ne krene (ili pogrešna poza) | `match.py:18-32,83` |
| L4 | **visoka** | Kratko NAZAD dok je robot NAORUZAN tiho otkazuje meč (bez potvrde); ESP sam vraća na tu stranicu | `pages.py:128-131,178-180`, `app.py:129` |
| L5 | srednja | PROVERA kešira rezultat prevođenja po imenu taktike: posle nove verzije fajla "OK" (ili "greška") je zastareo | `app.py:174-188` |
| L6 | srednja | "Kraj po STATUS-u" proglašava uspeh i kad je kretanje prekinuto (izgubljen FAIL, restart STM32) | `tac.py:181-192` |
| L7 | srednja | Posle isteka 100 s ponovni meč nije moguć bez restarta STM32, a PROVERA kaže OK i NAORUZAN čeka zauvek | `app.py:190-216`, `comm_port.c:92-97` |
| L8 | srednja | Kraj taktike pre 100 s = "kraj meča" za ESP: meni, "test odmah", RUN i upload (RESET/FLASH) se otključaju dok meč traje | `match.py:47-48,97-99`, `app.py:161-163` |
| L9 | srednja | Normalan kraj meča (taktika radi do 100 s) se prikazuje kao PREKID/PAO sa greškama | `app.py:236-258`, `match.py:100-101` |
| L10 | srednja | "test odmah"/RUN ne postavlja START pozu (meč postavlja): test i meč kreću od različite poze | `app.py:222-226`, `match.py:80-90` |
| L11 | srednja | `remaining()` je `None` van meča: taktika koja računa sa vremenom pada samo u testu | `tac.py:126-131` |
| L12 | srednja | API nema ništa za kraj meča po pravilima (povratak u zonu, faza napada od 85. s) | `tac.py` |
| L13 | srednja | "drži OK" na ugašenom ekranu izvršava potvrdu (npr. Test → motori) bez prikaza | `ui.py:464-468,348-353` |
| L14 | srednja | Odbijena START poza: taktika ipak krene, a greška se obriše čim taktika krene | `match.py:91-96`, `app.py:230-234` |
| L15 | srednja | `actuator(wait=False)` pa odmah komanda (primer iz dokumentacije): izgubljen okvir se ne ponavlja i ne prijavljuje | `robot.py:71-81,111-116`, `app.py:102`, `tac.py:11` |
| L16 | srednja | `tools/tactic.py` bez `--side` vozi na strani izabranoj na ekranu robota, ne na žutoj | `upload.py:450-458`, `app.py:225`, `tools/tactic.py:34` |
| L17 | srednja | Kratak pad veze u meču: taktika se prekida posle 1-2 s ili nastavlja "uspešno", zavisno od tajminga; nema nastavka | `tac.py:111-140,154-196` |
| L18 | niska | Argumenti: ugao bez svođenja radi na plavoj a puca na žutoj; `move()`/`speed` sa float-om pada | `tac.py:206-222,293-297` |
| L19 | niska | `turn_by(270)` okreće -90°, `turn_by(360)` ne radi ništa | `tac.py:231-234` |
| L20 | niska | Brzine: `speed=0` znači 1 m/s, nema gornje granice, podrazumevane 500/300/1000 mm/s | `tac.py:213,293`, `comm_port.c:25,101-103` |
| L21 | niska | `TOTAL` se ne poklapa sa brojem koraka (meč vs test): "GOTOVO 3/4" | `tactics/primer.py:9-12`, `pages.py:399` |
| L22 | niska | Ekran ROBOT, izveštaj i telemetrija su u koordinatama terena, a dnevnik i nazivi koraka u koordinatama "naše strane" | `pages.py:304-324`, `app.py:249` |
| L23 | niska | Aktuatori: BlackPill ih uvek odbija; ogledanje samo po imenu; pogrešno ime ruši taktiku tek u meču | `comm.c:136-138`, `tac.py:240-249` |
| L24 | niska | Mirni prikaz u meču piše "STOP"/"GOTOVO" između koraka; NAZAD u meču piše "otkazano" | `pages.py:272-279,128-131` |
| L25 | niska | Dnevnik/natpisi: vreme greške "t+<uptime>", sirovi razlozi, dva imena iste komande, "taster STOP" za WiFi STOP | `app.py:87`, `tekst.py:5-11`, `app.py:142` |
| L26 | niska | README, `primer.py`, `provera.py`, `rescue.py`, `config.py`, `protocol.yaml`: opisi ne odgovaraju kodu | razno |
| L27 | niska | Auto poza: šalje se samo jednom po pokretanju ESP-a (ne posle restarta/flešovanja STM32) | `app.py:107-112` |
| L28 | niska | "STM32 vN, flesuj" i kad je STM32 noviji od ESP-a | `tekst.py:24-26` |
| L29 | niska | `tools/tactic.py`: pad mreže tokom praćenja izlazi bez STOP-a; prsten dnevnika (40) tiho preskače redove | `tools/tactic.py:37-48`, `app.py:146` |
| L30 | niska | Sitni UX: strana se menja jednim klikom, "WDT u mecu" ne može da se isključi, test bez strane ide na žutu | `pages.py:145-149,165-171`, `app.py:358` |

**Ukupno: 30 nalaza: 4 visoka, 13 srednjih, 13 niskih.**

---

## Visoka

### L1. Naoružavanje ne proverava da li STM32 već broji meč — visoka

**Gde:** `ESP32/lib/match.py:50-63` (`arm`), `:80` (uslov za start), `ESP32/lib/app.py:190-216` (`check`).

**Problem.** `Match.update` u stanju NAORUZAN kreće čim u STATUS-u vidi bit `MATCH_RUNNING`. Ne traži
**promenu** (0 → 1) posle naoružavanja, a ni `arm()` ni PROVERA ne gledaju da li je bit već postavljen.
STM32 (`comm_port.c:92-97`) meč pokreće samo jednom i ne vraća ga do restarta. Zato svako naoružavanje
dok STM32 već broji meč odmah: šalje START pozu (SET_POSE) i pokreće taktiku, **bez činča**.

**Scenariji (svi realni na stolu ili u pit-u):**
- vežba sa "simul. cinc": taktika se završi za 30 s, tim vrati robota na start i pritisne "naoruzaj" →
  robot krene u ruci;
- STOP usred meča (ili prekid taktike), pa ponovo "naoruzaj" → taktika kreće iz početka, a SET_POSE START
  pregazi odometriju dok je robot negde na sredini stola;
- restart ESP-a usred meča (vidi analiza čišćenja 5.3): neko vidi da robot stoji i naoruža → isto;
- činč slučajno izvučen pre naoružavanja (na novom robotu sa činčem) → robot krene čim se naoruža, sa
  satom meča koji već teče.

**DOKAZ.** `exp/b1_rearm.py` (simulator, live): arm 0,3 s, činč 1 s, `primer` završi u 4,17 s, robot
vraćen na start u 8 s, arm u 9 s, **činč se ne izvlači**:
```
    9.00s NAORUZAN primer (zuta)
    9.01s CINC: start
    9.03s START primer (zuta)
   10.34s GOTO 600,1000: OK 1.3s
```

**Predlog.** U `Match.arm` zapamtiti `match_ms`/bitove iz poslednjeg STATUS-a i: (a) odbiti naoružavanje
(PROVERA stavka "mec: vec traje / zavrsen → restartuj STM32") ako je `MATCH_RUNNING` ili `MATCH_OVER` već
postavljen; (b) u NAORUZAN krenuti tek na **ivicu** (prvi STATUS posle naoružavanja bez bita, pa sa bitom).
Dugoročno: komanda protokola "MATCH_RESET" (ili da `MATCH_START` od ESP-a važi samo kad STM32 nije u meču
i da STM32 javi FAIL ako jeste).

### L2. Restart STM32 usred meča: ESP ne primeti, robot vozi i posle 100 s — visoka

**Gde:** `ESP32/lib/match.py:97-101` (kraj meča se čeka samo kao `MATCH_OVER` iz STATUS-a),
`ESP32/lib/tac.py:126-131`, `pogon-blackpill/Core/Lib/comm_port.c:53-54,92-97` (stanje meča je samo u RAM-u).

**Problem.** Jedini sat meča je na STM32. Ako se STM32 restartuje (pad napona pri zaglavljenim motorima,
brownout, ESD), on zaboravi i meč i pozu (0,0,0), a ESP: ne prepoznaje restart (nema provere da je
`MATCH_RUNNING` nestao bez `MATCH_OVER`, ni da je poza skočila na 0,0), nastavlja taktiku sa pogrešnom
odometrijom i **nikad ne prekida taktiku**, jer `MATCH_OVER` više neće doći. STM32 posle restarta prihvata
GOTO (nije `match_over`), pa robot vozi i posle 100 s (diskvalifikujuće po pravilima). Usput, korak koji je
trajao u trenutku restarta se proglasi uspešnim (L6).

**DOKAZ.** `exp/b4_stmreset.py`: taktika `dugo`, u 40. s simuliran restart STM32 (novi `SimSTM`, isti fizički
robot, odometrija 0,0,0), bez elemenata igre:
```
[40000, 'sim', 'STM32 RESET (odometrija 0,0,0, mec zaboravljen)']
[40170, 'log', 'GOTO 800,1000: kraj po STATUS-u (DONE nije stigao)']
t, x, y, mec, radi, remaining:
   (39, 525, 1000, 'MEC', 'dugo', 62.049)
   (45, 1500, 1418, 'MEC', 'dugo', None)
   (104, 1512, 1407, 'MEC', 'dugo', None)
   (110, 1637, 1310, 'MEC', 'dugo', None)
   (119, 1590, 1347, 'MEC', 'dugo', None)
```
Robot je posle 100 s i dalje u pokretu, ESP je u stanju MEC, a stvarna poza je ~1 m od one koju taktika
misli. Sa elementima igre (isti scenario) robot je odmah udario u kamenolom i javljao BLOCKED u petlji.

**Predlog.** (1) ESP drži i svoj sat meča od trenutka činča (`Match._t_cord`): posle 100 s (minus mala
rezerva) `abort = "kraj meca"` i STOP, nezavisno od STATUS-a. (2) U MEC, ako `MATCH_RUNNING` nestane bez
`MATCH_OVER` ili `match_ms` krene unazad: `abort = "STM32 restart"`, STOP, alarm. (3) Na STM32 opciono
upisati početak meča u backup registar (kao `BOOT_MAGIC`), da restart ne zaboravi meč.

### L3. `START` sa 2 broja ili ime koje počinje sa `START`/`TOTAL` — visoka

**Gde:** `ESP32/lib/match.py:18-32` (`read_meta`: `line.startswith(key)`), `:83` (`x, y, deg = self.start`).

**Problem.** (a) `read_meta` prepoznaje svaki red koji **počinje** sa `START` ili `TOTAL`, pa
`START_ZONA = (0, 500)` ili `TOTAL_MS = 90000` napisani posle prave vrednosti je pregaze (pobeđuje poslednji
red). (b) `START = (250, 1000)` (bez ugla, prirodno za nekog ko ugao ne zna) se pročita kao 2 broja, PROVERA
kaže OK, ali na činč `x, y, deg = self.start` baci `ValueError` u svakom krugu petlje: taktika **nikad ne
krene**, a dnevnik se zatrpa sa "CINC: start" (300 puta za 1,5 s, prsten od 40 redova izgubi sve ostalo).
Bez `try` po servisu (stari `runner.py`) isto bi ugasilo `main.py`. Simulator ovo krije za START u
`Sim.__init__` (dopunjuje START nulama), ali pravi `Match` u simulatoru i dalje pada. Ovo je drugo od
PROBLEMI 7 (tamo: izrazi i više redova).

**DOKAZ.** `exp/a2_meta.py`:
```
a.py meta: {'START': [0.0, 500.0], 'TOTAL': 90000}      # START = (250, 1000, 0) + START_ZONA, TOTAL_MS
b.py meta: {'START': [250.0, 1000.0]}
check: True
servis robot: ValueError not enough values to unpack (expected 3, got 2)
stanje meca: NAORUZAN radi: None                          # 300 puta "CINC: start", taktika nije krenula
```

**Predlog.** Regex po imenu (`^START\s*=`, `^TOTAL\s*=`), dopuniti ugao nulom (`(x, y)` → `(x, y, 0)`), a sve
što nije 2-3 broja prijaviti u PROVERA kao "ne" ("START nečitljiv"), ne tek na činč. U `Match.update` na
grešku u START-u ipak pokrenuti taktiku (bez poze) uz grešku, umesto da stoji.

### L4. Kratko NAZAD dok je robot NAORUZAN tiho otkazuje meč — visoka

**Gde:** `ESP32/lib/pages.py:128-131` (`Provera.back` → `do_cancel`), `:178-180`, `ESP32/lib/app.py:129`
(u NAORUZAN posle 10 s ESP sam vraća na PROVERA), `ESP32/lib/inputs.py:122-126`.

**Problem.** Na stranici PROVERA kratak pritisak NAZAD otkazuje naoružan meč, bez potvrde, sa porukom
"otkazano" od 1,5 s. Opasno jer: (1) ESP posle 10 s bez dodira **sam vraća** na PROVERA baš u NAORUZAN;
(2) dugi NAZAD (≥ 600 ms) otvara meni (koji je zaključan), pa pokušaj da se otvori meni pritiskom od 500 ms
otkaže meč; (3) README kaže da je NAZAD "podešavanja / nazad" (L26), ne "otkaži meč"; (4) za "test odmah"
i "simul. cinc" traži se "drži OK", a za otkazivanje meča ništa. Posle otkazivanja činč pokrene STM32
(sat teče), a ESP ne radi ništa ceo meč. Ako se naoruža ponovo, važi L1.

**DOKAZ.** `exp/b3_back.py`: arm u 0,3 s, NAZAD 100 ms u 2 s, činč u 5 s:
```
    0.30s NAORUZAN primer (zuta)
    2.13s otkazano
    5.00s [sim] cinc izvucen
posle NAZAD: {'m': 'NEMA', 'page': 'PROVERA', 'alarm': False} | na kraju: NEMA | taktika pokrenuta: False
```

**Predlog.** Otkazivanje samo preko stavke "otkazi" sa `Confirm` ("drži OK"), a NAZAD u NAORUZAN ne radi
ništa (ili samo pokaže "drži OK na otkazi"). Ako je otkazano, PROVERA naslov treba jasno da kaže "NIJE
NAORUZAN", a činč u stanju NEMA da podigne alarm ("CINC, a nije naoruzan").

---

## Srednja

### L5. PROVERA kešira prevođenje po imenu taktike — srednja

**Gde:** `ESP32/lib/app.py:174-188` (`tactic_ok`: `if c is None or c[0] != name`), `:169`.

**Problem.** Rezultat prevođenja (OK ili greška) se čuva po **imenu** dok se taktika ponovo ne izabere u
meniju. Posle `PUT`/`esp_push --no-reset`/simulator servera nove verzije istog fajla PROVERA i dalje kaže
staro: pokvarena taktika prolazi PROVERA i pada tek na činč; ispravljena taktika i dalje blokira
naoružavanje ("SyntaxError") i tim misli da ispravka nije stigla. `runner._compiled` ima ključ
(veličina, vreme izmene), ali `app._compiled` ga ne koristi (dva keša, analiza čišćenja S4; ovde je bitna
posledica). Usput: ako fajl sistem ne vodi vreme izmene, i `runner` bi izvršio stari kod za izmenu iste
dužine (nije provereno na ploči).

**DOKAZ.** `exp/a1_cache.py`:
```
pre izmene: (True, '') check: True
posle izmene (SyntaxError u fajlu): (True, '') check: True
[taktika] CINC: start
[taktika] GRESKA: SyntaxError("expected ':'", ('t', 3, 8, 'if True\n', 3, 9))
izvestaj: (False, 'greska SyntaxError')
```

**Predlog.** U `tactic_ok` ključ = `(ime, veličina, mtime)` (isti kao `runner`) ili jedan keš u `runner`
(S4); `upload` posle `PUT/COMMIT/DEL` u `tactics/` da poništi keš. Prevesti i pri `arm()`.

### L6. "Kraj po STATUS-u" proglašava uspeh i kad je kretanje prekinuto — srednja

**Gde:** `ESP32/lib/tac.py:181-192`.

**Problem.** Rezerva za izgubljen DONE: 3 STATUS-a bez `MOVING` posle `MOVING` → korak OK. Ali STM32 skida
`MOVING` (`motion_seq = 0`) i kad kretanje **ne uspe** (FAIL BLOCKED/TIMEOUT/STOPPED), i kad se restartuje.
Ako se izgubi FAIL (isti CRC razlog zbog kog postoji rezerva), ili STM32 restartuje, `goto()` vrati `True`
iako robot nije stigao. Taktika nastavlja kao da je na cilju.

**DOKAZ.** `exp/a5_lostfail.py` (FakeSTM: prepreka posle 1,5 s, okvir FAIL izgubljen):
`['GOTO 600,1000: kraj po STATUS-u (DONE nije stigao)', 'goto vratio True']`. Isto u L2:
`GOTO 800,1000: kraj po STATUS-u` odmah posle restarta STM32.

**Predlog.** Kraj po STATUS-u ne proglašavati uspehom bez provere cilja: uporediti poslednju pozu sa
ciljem (GOTO: rastojanje < ~30 mm; ROTATE: ugao < ~2°; MOVE: pređeni put), inače `False` sa razlogom
"NEPOZNATO". Ili protokolom: STM32 da u STATUS-u drži i "poslednji ishod" (seq + DONE/FAIL), pa se izgubljen
DONE/FAIL rekonstruiše tačno.

### L7. Posle isteka 100 s ponovni meč nije moguć bez restarta STM32, a PROVERA kaže OK — srednja

**Gde:** `ESP32/lib/app.py:190-216` (`check` ne gleda bitove meča), `pogon-blackpill/Core/Lib/comm_port.c:92-97,105-131`.

**Problem.** Posle `MATCH_OVER` STM32 odbija svako kretanje (`REASON_MATCH_OVER`) i ignoriše `MATCH_START`
dok se ne restartuje. ESP to nigde ne kaže: PROVERA je zelena, "naoruzaj" radi, NAORUZAN čeka činč koji ne
može da dođe ("simul. cinc" STM32 tiho prihvati i ne uradi ništa), a "test odmah" se završi sa
"GRESKA GOTO: kraj meca". Na takmičenju se robot obično ugasi između mečeva, ali u pit-u i pri vežbi
ovo troši vreme i zbunjuje. U meniju nema ni "restartuj STM32".

**DOKAZ.** `exp/b2_over.py`: prvi meč (činč 1 s), 101 s "100 s: kraj meca", arm 103,5 s, činč 105 s,
"simul. cinc" 106 s; stanje u 110 s:
```
PROVERA posle 100 s: {'check': (True, [('ceka', 'cinc', 'izvuci'), ('ok', 'STM32', 'v2'), ('ok', 'STATUS', '40ms'),
                       ('ok', 'taktika', 'primer'), ('ok', 'strana', 'zuta')]), 'state': 'NAORUZAN'}
  113.02s GRESKA GOTO: kraj meca          # "test odmah" posle STOP-a
```

**Predlog.** U `check()` stavka "ne": "STM32: mec zavrsen → restart" kad je `MATCH_OVER`, i "STM32: mec
traje" kad je `MATCH_RUNNING` van NAORUZAN/MEC (to rešava i L1). Na STM32 (dogovor): `MATCH_START` posle
`match_over` = novi meč, ili posebna komanda "MATCH_RESET" + stavka u meniju.

### L8. Kraj taktike pre 100 s otključava sve dok meč još traje — srednja

**Gde:** `ESP32/lib/match.py:47-48` (`armed` ne uključuje KRAJ), `:97-99`, `ESP32/lib/app.py:161-163`
(`busy`), `:291-295` (`open_menu`), `ESP32/lib/pages.py:477-480`.

**Problem.** Čim se taktika završi (npr. u 40. s), `Match` prelazi u KRAJ i za ESP je meč gotov: otključa
se meni, PROVERA nudi "naoruzaj" (→ L1) i "test odmah" (motori, u meču!), upload dozvoljava `RUN`, `RESET`,
`COMMIT`, `FLASH` (STM32 u bootloader usred meča), WiFi sme da se ponovo povezuje, a naslovna traka
prestaje da prikazuje preostalo vreme. Po pravilima meč traje 100 s i robot mora da ostane zaustavljen u
zoni; slučajan "test odmah" ili `esp_push` iz pit-a pomera robota usred meča.

**DOKAZ.** `exp/` (inline skripta posle `b5`): `primer` u meču, stanje u 10. s:
`{'mec': 'KRAJ', 'busy': False, 'upload_busy': False, 'stm_match': True, 'remaining': 91, 'menu_before': 1, 'menu_after': 2}`.

**Predlog.** Zaključavanje (meni, PROVERA, `busy()` za upload/net) držati dok STM32 javlja `MATCH_RUNNING`
(ili dok ESP-ov sat iz L2 ne pokaže 100 s), ne dok radi taktika. Vreme u naslovu prikazivati dok meč traje.
`busy()` da gleda i `robot.status` (pokriva i restart ESP-a usred meča).

### L9. Normalan kraj meča se prikazuje kao PREKID/PAO — srednja

**Gde:** `ESP32/lib/match.py:100-101`, `ESP32/lib/app.py:236-258`, `ESP32/lib/pages.py:397`.

**Problem.** Taktika koja koristi ceo meč (uobičajeno: radi dok ima vremena) dobije na 100 s FAIL
`MATCH_OVER` za tekuće kretanje, pa `abort = "kraj meca"`. Rezultat: alarm preko celog ekrana "PREKID /
kraj meca", izveštaj "PAO", dve "greške" i "!" u traci. Posle svakog dobrog meča tim vidi "PAO". Usput,
posle FAIL `MATCH_OVER` taktika stigne da pošalje još jednu komandu (i ona padne) pre nego što prekid stigne.

**DOKAZ.** `exp/b5_end.py` (`dugo`, činč 1 s):
```
[101000, 'log', 'GRESKA GOTO: kraj meca']
[101010, 'log', 'GRESKA GOTO: kraj meca']
[101020, 'log', 'PREKID: kraj meca']
{'alarm': ('PREKID', 'kraj meca'), 'rep': (False, 'kraj meca', (42, 'GOTO 400,1000', 'MATCH_OVER')), 'unseen': 2}
```

**Predlog.** Kraj meča nije greška: `how = "KRAJ"` koji se u izveštaju prikazuje kao "MEC GOTOV"
(bez alarma), FAIL `MATCH_OVER` ne upisivati u greške; u `_cmd` na `MATCH_OVER` odmah podići
`Abort("kraj meca")` umesto `return False`.

### L10. "test odmah"/RUN ne postavlja START pozu — srednja

**Gde:** `ESP32/lib/app.py:222-226` (`start_tactic`), `ESP32/lib/match.py:80-90`; idiom u `tactics/primer.py:11-12`.

**Problem.** U meču ESP postavi START pre taktike; u testu ne. Taktika koja ne ponovi
`if not remaining(): pose(*START)` (kao `primer`) u testu kreće od poslednje odometrije: posle prvog testa
tim rukom vrati robota na start, pokrene ponovo, a robot "misli" da je na kraju prethodne vožnje. Test i meč
se ponašaju različito, a to je baš ono što test treba da proveri.

**DOKAZ.** `exp/b7_test_start.py` (`daleko`: jedan GOTO na 1500 mm): drugi test posle vraćanja robota na
250,1000:
```
    8.03s GOTO 1500,1000: OK 0.0s
(14.0, 'stvarno', 250, 1000, 'odometrija', 1500, 1000)
```
Robot se ne pomeri, a korak je "OK".

**Predlog.** `start_tactic` da pre taktike pošalje START (ogledan po strani), isto kao meč (opciono
prekidač "test od START-a", podrazumevano uključen). Idiom u `primer.py` tada ide napolje.

### L11. `remaining()` je `None` van meča — srednja

**Gde:** `ESP32/lib/tac.py:126-131`.

**Problem.** Dokumentovano je ("None ako meč ne traje"), ali posledica je da svaka taktika koja odlučuje po
vremenu (`if remaining() < 15: idi_kuci()`) u testu padne sa `TypeError`, a u meču radi. Takođe posle
`MATCH_OVER` vraća `None` (STM32 tada skida `MATCH_RUNNING`), pa "test" i "meč gotov" izgledaju isto; na
samom kraju vraća `0`, a `if not remaining()` (idiom iz `primer.py`) tada misli da je test.

**DOKAZ.** Inline skripta (`exp/`, taktika `if remaining() < 15: ...`):
`mec True None []` / `test False greska TypeError ['taktika: TypeError']`.

**Predlog.** U testu meriti vreme od starta taktike kao "simulirani meč" (`100 - t`), a za proveru režima
dati posebnu funkciju (`in_match()`); posle `MATCH_OVER` vraćati 0.

### L12. API nema ništa za kraj meča po pravilima — srednja (dizajn)

**Gde:** `ESP32/lib/tac.py` (ceo API), pravila E.3 (robot zaustavljen u svojoj zoni, 5/10 poena) i E.4
(faza napada od 85. s).

**Problem.** Taktika je linearan skript; jedino sredstvo je `remaining()` između koraka. Dugačak `goto`
(timeout iz dužine puta, do desetak sekundi), `wait_until` ili zaglavljivanje ne mogu da se prekinu kad dođe
vreme za povratak u zonu ili za akciju od 85. s. Svaka taktika mora sama da raspoređuje provere, a
greška znači 0 poena za povratak. Timeout-i komandi ne znaju za preostalo vreme meča.

**DOKAZ.** Nije provereno eksperimentom; zaključak iz koda (`_cmd`, `wait`, `wait_until` čekaju samo
svoj timeout).

**Predlog.** U `tac`: `at(sekunda, fn)` ili `HOME_AT = 88` u zaglavlju taktike: kad `remaining()` padne
ispod praga, `_pump()` podigne `Abort("VREME")`, runner pozove funkciju `home()` iz taktike (ako postoji)
sa posebnim, kratkim timeout-ima. Timeout svakog `_cmd` ograničiti na `remaining()` u meču.

### L13. "drži OK" na ugašenom ekranu izvršava potvrdu — srednja

**Gde:** `ESP32/lib/ui.py:464-468` (`UI.hold`: probudi ekran, pa ipak prosledi držanje), `:348-353`.

**Problem.** `ui.input` pazi da prvi OK posle spavanja samo upali ekran (`:437`), ali držanje OK ide drugim
putem i odmah puni traku potvrde. Ako je ostao otvoren ekran "Test? POKRECE MOTORE" (ili "Simul. cinc"), a
ekran se ugasio (spavanje 1/5 min), uobičajen pokret "drži OK da se upali ekran" pokrene motore bez da je
operater video šta potvrđuje. `Confirm` ekrani nemaju ni sopstveni istek.

**DOKAZ.** `exp/a4_sleep.py`: Confirm "Test" otvoren, 61 s bez dodira, pa držanje OK 0/300/600/900 ms:
```
vrh: Confirm
ekran spava: True
zahtev/taktika: t | ekran spava: False
```

**Predlog.** U `UI.hold`: ako je ekran spavao, ignorisati to držanje do puštanja (kao `input`).
`Confirm` da se sam zatvori posle ~10 s i pri gašenju ekrana.

### L14. Odbijena START poza: taktika ipak krene, a greška se obriše — srednja

**Gde:** `ESP32/lib/match.py:91-96`, `ESP32/lib/app.py:230-234` (`on_tactic_start`: `self.errors, self.unseen = [], 0`).

**Problem.** Ako STM32 odbije SET_POSE na činč (npr. robot je još u pokretu ili je komanda izgubljena),
ESP čeka 500 ms i krene sa pogrešnom pozom ("POZA nije potvrdjena, krecem"). Greška "POZA: odbijeno" je
zabeležena, ali `on_tactic_start` sekund kasnije **briše sve greške i "!"**, pa jedini trag pogrešne
startne poze nestane sa DNEVNIK-a pre nego što bilo ko pogleda. Isto važi za sve greške iz faze NAORUZAN.
Usput, kad stigne FAIL (a ne ACK), nema razloga čekati punih 500 ms.

**DOKAZ.** `exp/a7_pose.py` (FakeSTM "vozi" u trenutku činča):
```
greske pre starta taktike: [[(100305, 'POZA: odbijeno')]] unseen: 1
posle starta: [('tokom', [], 0), ('tokom', [], 0)]
log: ['GRESKA POZA: odbijeno', 'POZA nije potvrdjena, krecem']
```

**Predlog.** Greške brisati pri naoružavanju, ne pri startu taktike. Na FAIL START poze: STOP, kratka
pauza i ponovni SET_POSE (robot na činč stoji), pa tek onda krenuti uz trajnu grešku u izveštaju.

### L15. `actuator(wait=False)` pa odmah komanda: izgubljen okvir se ne ponavlja — srednja

**Gde:** `ESP32/lib/robot.py:71-81` (nova komanda prebacuje staru u `_late`, bez ponavljanja),
`:111-116`, `ESP32/lib/app.py:102` (SUPERSEDED se ne prijavljuje), primer u `ESP32/lib/tac.py:11`.

**Problem.** Ponavlja se samo poslednja komanda (ispravno zbog duplikata na STM32). Ali baš primer iz
dokumentacije (`h = actuator("lift", 300, wait=False); goto(...)`) znači da se okvir aktuatora, ako se
izgubi, nikad ne ponovi: aktuator se ne pokrene, ishod je "SUPERSEDED" (u dnevniku neprevedeno), a na ekranu
nema greške ni "!". Paralelan rad (glavna namena `wait=False`) je tako najmanje pouzdan put.

**DOKAZ.** `exp/a6_act.py` (`stm.drop = 1`, izgubi se prvi okvir posle starta):
```
STM32 izvrsio: ['SET_POSE', 'GOTO']
['lift 300: poslato', 'lift 300: SUPERSEDED', 'wait_done: False'] greske: []
```

**Predlog.** `actuator(wait=False)` da sačeka ACK (≤ 180 ms, kratko) pre povratka, pa tek onda sledeća
komanda; ili da `robot.send` ne potiskuje nepotvrđen ne-kretni ACTUATOR. SUPERSEDED za nepotvrđenu komandu
prijaviti kao grešku.

### L16. `tools/tactic.py` bez `--side` vozi na strani izabranoj na ekranu — srednja

**Gde:** `tools/tactic.py:34` (šalje `RUN ime ` bez strane), `ESP32/lib/upload.py:450-458`,
`ESP32/lib/app.py:225` (`side or st["sel_side"] or REF_SIDE`).

**Problem.** Uputstvo (`tools/tactic.py` i README: "`--side plava` # druga strana") podrazumeva da je bez
opcije žuta. Stvarno je strana ona koja je poslednja izabrana na robotu. Ako je na ekranu ostala "plava",
`python tools/tactic.py primer` vozi ogledano: robot na žutoj startnoj zoni krene ka x = 2400 preko stola.

**DOKAZ.** Nije pokretano preko mreže; zaključak iz koda (put `RUN` → `start_tactic(name, None)` →
`st["sel_side"]`).

**Predlog.** `tools/tactic.py` uvek da šalje stranu (`--side` podrazumevano `zuta`) i da je ispiše; ili
`RUN` bez strane da vrati `ERR` sa izabranom stranom.

### L17. Kratak pad veze u meču: ishod zavisi od tajminga, nema nastavka — srednja

**Gde:** `ESP32/lib/tac.py:111-123` (`here()` čeka 1 s), `:134-140` (`_robot()` čeka 2 s), `:154-196`
(`_cmd` ne gleda `robot.alive`).

**Problem.** STM32 staje posle 500 ms bez PING-a (ispravno). ESP-ova reakcija zavisi od trenutka: ako veza
padne usred `goto`, `_cmd` čeka ceo timeout tog koraka (bez provere veze); ako se veza vrati pre isteka,
korak se proglasi uspešnim po STATUS-u (L6); ako ne, sledeća komanda posle 2 s (ili `goto` bez timeout-a
posle 1 s, preko `here()`) podigne `Abort` i **taktika je gotova do kraja meča**, čak i kad se veza
(labav konektor) vrati za 3 s. Nema "nastavi od sledećeg koraka".

**DOKAZ.** Delimično: `exp/b6_link.py` (simulator bafiruje odgovore dok je "kabl" izvučen, pa vidi
FAIL STOPPED: `GOTO 1500,1000: STOPPED`; na pravoj žici bi ti bajtovi bili izgubljeni). Ostalo iz koda.

**Predlog.** U `_cmd`: ako `not robot.alive` duže od ~300 ms, korak = False sa razlogom "VEZA" (ne čekati
timeout, ne proglašavati uspeh po STATUS-u posle povratka). `_robot()` u meču da čeka duže (npr. do
povratka veze ili kraja meča) umesto `Abort`; jedan prag "svežeg STATUS-a" (analiza S9).

---

## Niska

### L18. Argumenti komandi: opseg ugla i tipovi — niska

**Gde:** `ESP32/lib/tac.py:206-210` (`pose`), `:213-222` (`goto`: `int(mirror_deg(deg) * 100)` bez `_wrap`),
`:293-297` (`move`: `dist` i `speed` bez `int`).

**Problem.** `turn_to` svodi ugao na ±180°, a `goto`/`pose` samo kad je strana ogledana (`mirror_deg` tada
radi `_wrap`). `goto(..., deg=400)` zato radi na plavoj, a na žutoj pravi `struct.error` (CPython) ili
**tiho pogrešan ugao** na ESP-u (MicroPython `struct.pack` ne proverava opseg i odseče na 16 bita; nije
provereno na ploči). `move(150.0)` i `speed=0.5*600` padaju (`goto` x/y pretvara u `int`, `move` ne).

**DOKAZ.** `exp/a3_types.py`:
```
deg400  zuta  ok=False how=greska error poslato=[]
deg400  plava ok=True how=None poslato=[('GOTO', {'x': 2500, 'y': 1000, 'theta': 14000, ...})]
movef   zuta  ok=False how=greska error
speedf  zuta  ok=False how=greska error
```

**Predlog.** Sve komande: `int(round(...))` za mm i mm/s, `_wrap` za svaki ugao pre slanja.

### L19. `turn_by` svodi ugao — niska

**Gde:** `ESP32/lib/tac.py:231-234`.

**Problem.** `turn_by(deg)` je `turn_to(_wrap(h + deg))`: `turn_by(270)` okrene -90° (u drugu stranu),
`turn_by(360)` ne uradi ništa, a korak se zove "OKRET za 270". Dokumentacija kaže "okreni se za deg".

**DOKAZ.** `exp/a3_types.py`: `turnby zuta ... ('ROTATE', {'theta': -9000})` za `turn_by(270)` iz 0°.

**Predlog.** Dokumentovati "najkraćim putem, |deg| ≤ 180" i odbiti veće, ili okret preko više koraka.

### L20. Brzine: `speed=0` = 1 m/s, bez gornje granice, različiti podrazumevani — niska

**Gde:** `ESP32/lib/tac.py:213` (goto 500), `:293` (move 300), `:29` (`MIN_SPEED`), `comm_port.c:25,101-103`
(`max_speed = 0` → `V_DEFAULT` 1,0 m/s), `control.c:66-67,342` (stvarno `clamp(v, 0,15, 1,5)` m/s).

**Problem.** `speed=0` (npr. "najsporije") znači 1000 mm/s. Iznad 1500 mm/s STM32 tiho seče, pa
`_drive_timeout` računa sa brzinom koju robot nikad ne dostigne. Tri različita podrazumevana broja
(500, 300, 1000) bez objašnjenja.

**DOKAZ.** `exp/a3_types.py`: `speed0 ... ('GOTO', {..., 'max_speed': 0})` prolazi bez upozorenja; ostalo iz koda.

**Predlog.** U `tac`: `MAX_SPEED = 1500`, `speed = max(MIN_SPEED, min(MAX_SPEED, speed))` pre slanja i
pre računanja timeout-a; `0` odbiti.

### L21. `TOTAL` ne odgovara broju koraka — niska

**Gde:** `ESP32/tactics/primer.py:9-12`, `ESP32/lib/pages.py:399`, `ESP32/lib/app.py:244`.

**Problem.** `TOTAL` se piše ručno, a broj koraka zavisi od režima (`pose()` je korak samo u testu). U meču
izveštaj kaže "GOTOVO 3/4", što izgleda kao preskočen korak.

**DOKAZ.** Inline (`exp/`): `mec ok True done/total 3 4 steps 3`, `test ok True done/total 4 4 steps 4`.

**Predlog.** Ne računati `pose()` kao korak, ili izveštaj da prikazuje "3 koraka OK" bez imenioca kad je
taktika uspela; `TOTAL` samo za traku napretka.

### L22. Dva koordinatna sistema na ekranu i u dnevniku — niska

**Gde:** `ESP32/lib/pages.py:304-324` (ROBOT), `ESP32/lib/app.py:249` (izveštaj `pose`), `ESP32/lib/telem.py:58-63`,
naspram `tac.here()` i naziva koraka (`"GOTO %d,%d" % (x, y)` u koordinatama naše strane).

**Problem.** Na plavoj strani dnevnik kaže "poza na kraju: (602, 804, 89)", a izveštaj i ekran ROBOT
"2398, 804, 91". Pri traženju greške na stolu nije jasno koji broj je koji.

**DOKAZ.** Inline (`exp/`, `primer`, plava): `['GOTO 600,1000: OK 1.3s', 'poza na kraju: (602, 804, 89.45)']`,
`izvestaj pose: [2398, 804, 91]`.

**Predlog.** Na ROBOT i u izveštaju dodati oznaku ("teren") ili prikazivati obe; nazive koraka pisati
sa "(nasa)" ili u koordinatama terena.

### L23. Aktuatori: BlackPill ih odbija, ogledanje i provera imena — niska

**Gde:** `pogon-blackpill/Core/Lib/comm.c:136-138` (samo `__weak` verzija vraća `REASON_INVALID`;
`comm_port.c` je nema), `ESP32/lib/tac.py:240-249`, `ESP32/config.py:23-26`.

**Problem.** (1) Na sadašnjem robotu svaki `actuator()` dobije FAIL "odbijeno", iako `config.ACTUATORS`,
README i primeri govore kao da rade. (2) Ogledanje važi samo za ime (`ruka_l` ↔ `ruka_r`); broj
(`actuator(3, ...)`) i vrednost (npr. ugao ruke ±45°) se ne ogledaju. (3) Pogrešno ime podiže `Abort`
cele taktike tek kad se taj red izvrši (u meču), PROVERA imena ne proverava.

**DOKAZ.** Nije pokretano; zaključak iz koda (FakeSTM ima `act_fail` baš za "BlackPill bez njih").

**Predlog.** PROVERA: statička provera imena u `actuator("...")` iz teksta taktike; u dokumentaciji
naglasiti da BlackPill nema aktuatore; `ACTUATOR_MIRROR_VALUE` ili dokumentovati da se vrednosti ne ogledaju.

### L24. Natpisi u meču koji zbunjuju — niska

**Gde:** `ESP32/lib/pages.py:272-279` (`draw_calm`), `:128-131` + `:178-180` (NAZAD/"otkazi" u MEC).

**Problem.** (1) Mirni prikaz između dva koraka (npr. tokom `wait()` ili posle neuspelog koraka koji
taktika obrađuje) piše "STOP" ili "GOTOVO", iako taktika radi. (2) U MEC stranica PROVERA i dalje nudi
"simul. cinc" i "otkazi"; NAZAD ili "otkazi" ne rade ništa, ali ispišu "otkazano", pa operater misli da
je prekinuo meč.

**DOKAZ.** (2) Inline (`exp/`, `dugo` u meču, okret na PROVERA, NAZAD):
`{'page': 'PROVERA', 'toast': 'otkazano', 'mec': 'MEC', 'run': 'dugo'}`. (1) iz koda.

**Predlog.** (1) Između koraka "RADI". (2) U MEC redovi PROVERA bez "otkazi"/"simul. cinc", NAZAD bez
poruke (ili "STOP taster prekida").

### L25. Dnevnik i natpisi nedosledni — niska

**Gde:** `ESP32/lib/app.py:87` (vreme greške van taktike = ms od paljenja ESP-a → "t+3600s"),
`ESP32/lib/tekst.py:5-11`, `ESP32/lib/tac.py:176-179` (u dnevnik ide sirov razlog), `ESP32/lib/app.py:142`.

**Problem.** Ista greška se vidi dvaput različito: "GRESKA PRAVO: kraj meca" (traka, `T.SHORT`) i
"MOVE -100: MATCH_OVER" (dnevnik, sirovo; isto "SUPERSEDED", "BLOCKED"). STOP preko WiFi-ja
(`tools/tactic.py --stop`) na ekranu piše "taster STOP".

**DOKAZ.** `exp/b2_over.py`: `GRESKA PRAVO: kraj meca` uz korak "MOVE -100"; `exp/a6_act.py`:
`lift 300: SUPERSEDED`.

**Predlog.** Jedan rečnik naziva (`MOVE` svuda ili `PRAVO` svuda), `T.reason` i u `tac.log`; vreme greške
van taktike kao "-"; `app.stop(izvor)`.

### L26. Dokumentacija i komentari ne odgovaraju kodu — niska

**Gde i šta:**
- `ESP32/README.md:29-31,46`: "dugi klik enkodera = podešavanja", "NAZAD: podešavanja / nazad, dugi =
  početni ekran". Kod (`inputs.py:4-5`): dugi klik enkodera ne radi ništa, dugi NAZAD = meni, kratki NAZAD
  na PROVERA u NAORUZAN = otkaži meč (L4).
- `ESP32/README.md:120-123` i `tactics/primer.py:3`: "dugi klik -> Taktike -> `zuta: mec` / `zuta: test`",
  "CEKA CINC". Takvih stavki više nema (izbor je PROVERA → taktika → strana → "naoruzaj"/"test odmah").
- `tactics/provera.py:1`: "Bezbedno za pokretanje bilo kad", a radi `pose(250, 1000, 0)`, tj. pregazi
  odometriju (na plavoj 2750).
- `lib/rescue.py:2`: "(samo PUT, RESET, LOG)", a `upload.RESCUE_OK` dozvoljava i STAGE, COMMIT, DEL, LIST.
- `config.py:5` "UART2 ka Nucleu", `protocol.yaml:1-2,37` "ESP32 <-> Nucleo": robot je BlackPill.

**DOKAZ.** Poređenje teksta i koda (navedene linije).

**Predlog.** Ispraviti tekst; README odeljak "Na robotu" napisati po stvarnom toku PROVERA.

### L27. Auto poza samo jednom po pokretanju ESP-a — niska (samo razvoj)

**Gde:** `ESP32/lib/app.py:107-112` (`_pose_sent` se postavlja jednom).

**Problem.** Dopuna PROBLEMI 5 (tamo: ne zna za stranu). Auto poza se šalje samo posle prvog povezivanja
od paljenja ESP-a: posle restarta ili flešovanja STM32 (`upload._flash` postavlja `version = None`)
odometrija je 0,0,0 i ostaje tako. Obrnuto, posle svakog restarta ESP-a (`esp_push`, RESET) poza se tiho
vrati na (250, 1000, 0) i kad robot stoji negde drugde.

**DOKAZ.** Nije pokretano; zaključak iz koda.

**Predlog.** Slati auto pozu kad STM32 "dođe" (nova veza posle pada ili promene verzije), ne kad ESP
startuje; ili je potpuno izbaciti kad L10 uvede START pozu za test.

### L28. "STM32 vN, flesuj" i kad je STM32 noviji — niska

**Gde:** `ESP32/lib/tekst.py:24-26`, `ESP32/lib/robot.py:23`.

**Problem.** Kad je STM32 na protokolu v3, a ESP zna samo (1, 2), poruka kaže da treba flešovati STM32,
a treba ažurirati ESP. Parametar `want` se ne koristi (analiza D17), a baš on bi rešio poruku.

**DOKAZ.** Iz koda.

**Predlog.** `"ESP zastareo (STM v3)"` kad je `have > want`, "flesuj STM32" samo kad je `have < want`.

### L29. `tools/tactic.py`: pad mreže i prsten dnevnika — niska

**Gde:** `tools/tactic.py:37-48`, `tools/espnet.py:58-73`, `ESP32/lib/app.py:146` (40 redova).

**Problem.** Ako mreža pukne tokom praćenja, `query` posle 3 pokušaja izađe sa `SystemExit` bez STOP-a,
a korisnik koji drži Ctrl+C kao "STOP" misli da skript još kontroliše robota. Ako taktika napiše više od 40
redova između dva čitanja (0,3 s), redovi se tiho preskoče (nema oznake "izgubljeno N").

**DOKAZ.** Iz koda (L3 pokazuje kako brzo se prsten napuni: 300 redova za 1,5 s).

**Predlog.** Na grešku mreže probati STOP i jasno ispisati "veza pukla, robot NIJE zaustavljen";
`LOG` da vrati i broj preskočenih redova.

### L30. Sitni UX — niska

**Gde:** `ESP32/lib/pages.py:145-149` (strana jednim klikom, pamti se), `:165-171` (test bez strane: Confirm
ne piše stranu, a ide na žutu), `ESP32/lib/app.py:358` ("WDT u mecu": jednom uključen WDT ne može da se
ugasi, prekidač to ne kaže), `ESP32/lib/app.py:328-332` ("Mecevi" lista i testove, samo broj fajla).

**DOKAZ.** Iz koda.

**Predlog.** Strana preko izbora sa potvrdom; Confirm uvek sa stranom; uz WDT napomena "do restarta";
u listi mečeva ime taktike i "test"/"mec".

---

## Šta je proveravano, a nije nalaz

- **seq 255 → 1 i duplikati:** `robot.send` ponavlja samo poslednju komandu, STM32 duplikat prepoznaje po
  poslednjem seq i resetuje ga posle pada veze (`comm.c:158-159`); omotavanje 255 → 1 ne pravi sudar jer
  isti seq dolazi tek posle 254 druge komande. Kasan ACK posle 3 pokušaja se tiho odbaci (NOREPLY pre toga
  već pošalje STOP za kretanje). U redu.
- **Restart ESP-a i `last_seq` na STM32:** restart ESP-a traje duže od 500 ms, pa STM32 vidi pad veze i
  kreće seq ispočetka. U redu (osim ponašanja u meču, vidi L1/L8 i analizu 5.3).
- **STOP u svakoj fazi:** NAORUZAN/POZA → otkazivanje (uz alarm), MEC → prekid taktike i STOP, i ugašen
  ekran ne smeta. Radi; problemi su posle (L1, L8).
- **Naoružavanje bez STM32:** PROVERA to sprečava (`check` traži `robot.ok` i svež STATUS).
- **Ogledanje `move()`:** relativno kretanje se ispravno ne ogleda; `turn_by` ispravno menja smer na plavoj.
- **`here()` i staro STATUS:** traži STATUS ≤ 300 ms, inače `Abort` posle 1 s; problem ne-konačne poze
  posle DONE je PROBLEMI 2.
