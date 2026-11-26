> Zamenjeno: vidi docs/redizajn-ui.md

# Eurosim → jedan interfejs za robota (Eurobot 2027): režimi rada

Datum: 2026-11-26. Nivo: režimi, zadaci, šta je uvek vidljivo, izvori podataka. Izgled i kod dolaze posle
(architect-review, ux-expert, superdesign). **Stanje: odobren spec, ništa još nije urađeno.**

## 1. Namera

Aplikacija u `simulator/` (eurosim + web) počela je kao simulator taktika. Treba da postane **jedini interfejs za
robota**: simulacija, praćenje pravog robota, lidar, ručno upravljanje, taktike, snimci i funkcije koje još ne
znamo. Funkcije su dodavane jedna na drugu, pa su informacije izmešane i interfejs nije intuitivan. Cilj je
trostruk:

- jasna podela po tome **šta korisnik radi**;
- isti interfejs za simulaciju i pravog robota;
- mesto gde nove funkcije lako ulaze.

## 2. Korisnici

- **Petar:** koristi sve (robot, testiranje delova, poređenje). Jedini pravi i održava aplikaciju.
- **Ostali u timu:** pišu taktike i gledaju simulaciju. Ne povezuju se na robota.

## 3. Faze sezone

Aplikacija je ista u sve tri faze, samo se izvor podataka pomera od simuliranog ka pravom.

1. **Pre robota:** taktike se pišu i proveravaju samo u simulaciji.
2. **Robot nastaje deo po deo:** testira se jedan deo, van meča i van taktike. Mešaju se pravi i simulirani
   delovi.
3. **Gotov robot:** cele taktike na pravom robotu, uživo, i poređenje sa simulacijom.

## 4. Ciljevi, ne-ciljevi, anti-ciljevi

- **Ciljevi:**
  - četiri radna prostora po zadatku;
  - isti prikaz za sim, pravog robota i snimak;
  - izvor podataka bira se posebno za svaki deo robota;
  - uvek vidljiva traka;
  - nova funkcija ulazi kao novi panel.
- **Ne-ciljevi (sada):** izgled, arhitektura koda, više robota (PAMI), vožnja joystick-om, automatska kalibracija.
- **Anti-ciljevi** (neuspeh i ako sve tehnički radi):
  - korisnik ne zna da li gleda simulaciju ili pravog robota;
  - robotske stvari smetaju onima koji samo pišu taktike;
  - nova funkcija opet „zalepljena“, bez svog mesta;
  - ručne komande moguće dok je robot naoružan ili meč traje.

## 5. Ograničenja (postojeće stanje)

- Simulator pokreće pravi ESP kod (`ESP32/lib`) nad simuliranim STM32. Granica je UART, a ESP kod se ne kopira.
- Simulacija, Live i telemetrija robota već daju isti oblik snimka: frame-ovi i događaji (`record.py`,
  `robotlink.TelemRecorder`).
- Telemetrija (`telem.py`, UDP 10 Hz) šalje samo pozu, brzinu, bitove stanja, korak i dnevnik. Lidar ide kao
  poseban paket. Ne šalje IR, `w`, zdravlje veze, aktuatore ni ekran.
- Upload server (TCP 8267) ima PUT/RUN/STOP/STAT/LOG, a nema ručnih komandi.
- Tim pokreće aplikaciju iz repoa (`start.bat` / `start.sh`), radi bez interneta.

## 6. Pristupi

- **A. Po zadatku:** radni prostori Taktike / Test dela / Vožnja / Snimci. **Izabrano.**
- **B. Po izvoru** (Robot | Simulator | Editor, `docs/plan-kontrolna-tabla.md`): najmanje posla, ali hibrid nigde ne
  pripada, a test dela i taktika ostaju izmešani.
- **C. Jedan ekran sa stolom i panelima po izboru** (kao IDE): najfleksibilnije, ali teret organizacije pada na
  korisnika. Bez dobrih rasporeda ponavlja današnji nered.

**Odluka:** A, iznutra sastavljen od panela kao u C. Nova funkcija je panel u nekom prostoru, a ređe novi prostor.

## 7. Radni prostori

### 7.1 Taktike (faza 1, ceo tim; podrazumevani prostor)

Pisanje taktike: editor, provera dok kucaš, nacrt putanje. Brza simulacija meča ili testa, protivnici i scenariji
stola, puštanje rezultata. Izvor je uvek sim.

### 7.2 Test dela (faze 2-3, Petar)

Van meča i van taktike, jedan deo u fokusu. Svaki deo prati istu šemu: **sirovo → obrađeno → odluka**, plus
ručne komande.

- **Lidar:** uživo ili iz snimka krugova.
  - Lidar je fiksiran na robotu, pa se krug prebacuje u koordinate stola po trenutnoj pozi.
  - Tačke van stola se odbacuju (sudija pored stola ne sme da ispadne protivnik) i prikazuju se drugom bojom.
  - Koraci prikaza: sirove tačke → u stolu / van stola → grupe → „protivnik na 420 mm, 30°“ → robot bi: STANI.
    Uz to Hz, broj tačaka i starost kruga.
  - **Ko računa šta:** robot šalje svoj konačni rezultat (objekti, odluka). Laptop iz sirovih tačaka i poze istim
    ESP kodom računa međukorake. Prikaz jasno razlikuje „robot je odlučio“ od „laptop je izračunao“.
  - Bez poze: jasno piše „nema poze“, a prikaz je oko robota, ne na stolu.
  - **Snimi pa ponavljaj:** isti snimak krugova služi za razvoj algoritma. Algoritam je ESP kod, pa radi i na
    laptopu.
- **Pogon:** ručne komande u koracima, uz izbor brzine:
  - MOVE ±50 / 100 / 300 mm;
  - ROTATE ±15 / 90°;
  - GOTO klikom na sto.

  Prikaz: zadato vs. odometrija, grafik brzine i ugla. Svrha:
  - provera odometrije (meriš metrom i računaš ručno, bez čarobnjaka);
  - pronalaženje dobrih koraka;
  - posmatranje robota uživo.

  Svaka ručna komanda pokazuje svoj red taktike, uz „kopiraj u taktiku“.
- **Mehanizmi:** dugme ili klizač za svaki aktuator iz `config.ACTUATORS`, stanje i vreme izvršenja.
- **IR:** 8 senzora uživo (raw + maska), paljenje i gašenje.
- **Bezbednost:**
  - ručne komande se odbijaju kad je robot naoružan ili meč traje;
  - brzina je ograničena;
  - STOP je uvek tu (§ 9a);
  - ako veza padne tokom ručne komande, robot staje (čuvar veze na ESP-u);
  - nema deadman-a dok su komande koraci; potreban je tek uz joystick.

### 7.3 Vožnja (faze 2-3)

Pokretanje taktike, kao test ili kao meč (naoruži, činč, 100 s), uživo. ESP panel (ekran i tasteri) i praćenje.
Izvor po delu, od sve-sim (današnji Live) do sve-pravo (§ 8).

### 7.4 Snimci

Puštanje i poređenje dva snimka, tipično sim i pravi:

- tabela koraka: sim / pravi / razlika vremena;
- grafici ugla i brzine jedan preko drugog, poravnati po početku koraka;
- putanja preko putanje;
- istaknut korak koji postoji samo u jednom snimku.

Svaki snimak nosi verziju taktike, stranu, scenario i profil. Uz snimak sa robota ide akcija **„simuliraj
isto“**, a ručno se mogu izabrati bilo koja dva snimka.

Razlika ima dva smera:

- robot je loš → podesi PID;
- simulacija je loša → popravi profil. Automatski fit (K0/K1) je za kasnije.

### Podešavanja (nisu radni prostor)

Profil robota, repo (pull i save), veza sa robotom.

Robotski prostori se ne kriju. Kad robot nije povezan, jasno to kažu.

## 8. Izvor podataka po delu

- **Delovi:** pogon (poza, odometrija), lidar, IR, mehanizmi, protivnici.
- **Izvori:** sim / pravi / snimak.
- **Pravilo:** taktika se izvršava tamo gde je pogon.
- Izbor izvora je zajedničko stanje i prati korisnika iz jednog radnog prostora u drugi.

| | Pogon | Lidar | IR | Mehanizmi | Protivnici | Taktika radi na | Stanje |
|---|---|---|---|---|---|---|---|
| a | sim | sim | sim | sim | sim | laptopu | postoji |
| b | sim | pravi / snimak | sim | sim | sim | laptopu | postoji (hibrid) |
| c | pravi | pravi | pravi | pravi ili lažiran | stvarni na stolu | pravom ESP-u | novo |
| d | sve pravo | | | | | pravom ESP-u | novo (isto kao c) |

Lažiran mehanizam na robotu odgovori „gotovo“ posle zadatog vremena. **Ne podržava se:** pravi pogon uz
simulirani lidar, IR ili protivnika.

## 9. Uvek vidljivo

Traka se vidi u svim prostorima čim nešto radi:

- **izvor**, krupno i u boji: SIM / ROBOT / HIBRID / SNIMAK;
- **poza**;
- **stanje:** miruje / naoružan / meč + vreme / korak i ime;
- **detekcija sada:** šta lidar i IR vide i da li to zaustavlja robota;
- **poslednja odluka i razlog;**
- **STOP** (i Esc), čim je povezan pravi robot ili nešto radi.

Pri puštanju snimka traka pokazuje stanje u tom trenutku snimka.

**9a. STOP** zaustavlja sve, i kretanje i taktiku, na robotu i u simulaciji, kao taster STOP na robotu.

## 10. Snimanje

- Svaka sesija sa pravim robotom (test dela i vožnja) snima se automatski, lokalno, van gita.
- U repo idu samo snimci sačuvani sa „Save run“ (`simulator/runs/`, kao danas).
- Simulacije se snimaju samo na zahtev.

## 11. Zahtevi prema robotu (ESP strana)

Deo su ovog plana, ali svaka ESP faza traži posebno odobrenje. UI mora da radi i bez njih:

- Test dela bez ručnih komandi;
- traka bez „poslednje odluke“;
- IR samo u simulaciji.

Zahtevi:

- **Telemetrija v2:** `w`, IR raw i maska, zdravlje veze sa STM32, krug petlje, RAM, RSSI, uptime, verzija, stanje
  aktuatora, konačni rezultat detekcije lidara.
- **Odluke sa razlogom:** nova funkcija u tac API-ju, telemetrija je prenosi. Primer: „idem na kamenolom 3 jer je
  lidar video protivnika kod 5“.
- **Ručne komande** preko upload servera: MOVE, ROTATE, GOTO, aktuator, IR maska, SET_POSE. Odbijaju se u meču.
- **Čuvar veze:** robot staje kad veza padne tokom ručne komande.
- **Lažiranje delova** koji fale kad taktika radi na robotu.
- **Lidar** u koordinatama stola, sa filtriranjem tačaka van stola.

## 12. Odnos prema postojećim planovima

- **Zamenjuje strukturu** iz `plan-ui-senzori-kalibracija.md` (U1: kartice Simulate/Live/Robot) i
  `plan-kontrolna-tabla.md` (B3: Robot kao prva kartica).
- **Iz `plan-kontrolna-tabla.md` sadržajno ostaju:** A (lidar vidljiv), B1 (telemetrija v2), C (ručne komande),
  D (ekran na daljinu, push i flash iz UI-ja).

## 13. Za kasnije

- više robota (PAMI);
- joystick sa deadman-om;
- automatska kalibracija iz snimka (K0/K1);
- baterija (INA3221);
- flešovanje STM32 i slanje koda iz UI-ja;
- ESP ekran na daljinu, ako ne stigne u Vožnju.

## 14. Ostavljeno graditelju

- izgled i raspored panela (ux-expert, superdesign);
- arhitektura koda i model panela (architect-review);
- kako se tačno lažiraju delovi na robotu.

## Predlozi doneti tokom razgovora (nisu izričito tražene odluke)

- pravilo „taktika radi tamo gde je pogon“ (iz odluke da taktika radi na pravom ESP-u);
- ručne komande su koraci, ne vožnja, i svaka ima „kopiraj u taktiku“;
- izvor u traci krupno i u boji;
- automatsko snimanje svake sesije sa pravim robotom;
- automatski snimci ostaju lokalni, van gita;
- „simuliraj isto“ uz snimak sa robota;
- robotski prostori se ne kriju, a Taktike su podrazumevani prostor;
- UI mora da radi i bez ESP izmena;
- odbačene tačke lidara prikazuju se drugom bojom.
