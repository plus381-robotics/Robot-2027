# Status i odluke

Datum: 2026-11-26. Varijanta A (bočna traka sa režimima); jezik UI-ja srpski; radni prostor se menja i tokom sesije; maketa je van repoa (`~/makete-ui/varijanta-a.html`). Ovaj dokument zamenjuje `docs/plan-redizajn-interfejsa.md` i `docs/plan-arhitektura-interfejsa.md`.

## Odluke

- Izabrana maketa: **varijanta A** (bočna traka sa režimima), `~/makete-ui/varijanta-a.html` (van repoa). Iz B i C ništa.
- Jezik UI-ja: **srpski** (latinica), svuda.
- Radni prostor sme da se menja i dok sesija radi (danas su kartice zaključane); bezbednost čuva traka (STOP svuda).
- Stil: postojeći tamni, krupniji za laptop u jami (osnova 15–16 px, kontrole ≥ 40 px, STOP ≥ 54 px).
- Iz makete A: izbor SIM/ROBOT je u bočnoj traci ispod „Vožnja“ (ne poseban red); traka staje na 1366 px (poza
  `1240, 830 · 92°`, Korak i Detekcija se skraćuju sa „…“); u Upravljanju su aktuatori u donjem redu, uvek vidljivi.

# Spec

## Eurosim → jedan interfejs za robota (Eurobot 2027): režimi rada

### 1. Namera

Aplikacija u `simulator/` (eurosim + web) počela je kao simulator taktika. Treba da postane **jedini interfejs za
robota**: simulacija, praćenje pravog robota, lidar, ručno upravljanje, taktike, snimci i funkcije koje još ne
znamo. Funkcije su dodavane jedna na drugu, pa su informacije izmešane i interfejs nije intuitivan. Cilj je
trostruk:

- jasna podela po tome **šta korisnik radi**;
- isti interfejs za simulaciju i pravog robota;
- mesto gde nove funkcije lako ulaze.

### 2. Korisnici

- **Petar:** koristi sve (robot, testiranje delova, poređenje). Jedini pravi i održava aplikaciju.
- **Ostali u timu:** pišu taktike i gledaju simulaciju. Ne povezuju se na robota.

### 3. Faze sezone

Aplikacija je ista u sve tri faze, samo se izvor podataka pomera od simuliranog ka pravom.

1. **Pre robota:** taktike se pišu i proveravaju samo u simulaciji.
2. **Robot nastaje deo po deo:** testira se jedan deo, van meča i van taktike. Mešaju se pravi i simulirani
   delovi.
3. **Gotov robot:** cele taktike na pravom robotu, uživo, i poređenje sa simulacijom.

### 4. Ciljevi, ne-ciljevi, anti-ciljevi

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

### 5. Ograničenja (postojeće stanje)

- Simulator pokreće pravi ESP kod (`ESP32/lib`) nad simuliranim STM32. Granica je UART, a ESP kod se ne kopira.
- Simulacija, Live i telemetrija robota već daju isti oblik snimka: frame-ovi i događaji (`record.py`,
  `robotlink.TelemRecorder`).
- Telemetrija (`telem.py`, UDP 10 Hz) šalje samo pozu, brzinu, bitove stanja, korak i dnevnik. Lidar ide kao
  poseban paket. Ne šalje IR, `w`, zdravlje veze, aktuatore ni ekran.
- Upload server (TCP 8267) ima PUT/RUN/STOP/STAT/LOG, a nema ručnih komandi.
- Tim pokreće aplikaciju iz repoa (`start.bat` / `start.sh`), radi bez interneta.

### 6. Pristupi

- **A. Po zadatku:** radni prostori Taktike / Test dela / Vožnja / Snimci. **Izabrano.**
- **B. Po izvoru** (Robot | Simulator | Editor, `docs/plan-kontrolna-tabla.md`): najmanje posla, ali hibrid nigde ne
  pripada, a test dela i taktika ostaju izmešani.
- **C. Jedan ekran sa stolom i panelima po izboru** (kao IDE): najfleksibilnije, ali teret organizacije pada na
  korisnika. Bez dobrih rasporeda ponavlja današnji nered.

**Odluka:** A, iznutra sastavljen od panela kao u C. Nova funkcija je panel u nekom prostoru, a ređe novi prostor.

### 7. Radni prostori

#### 7.1 Taktike (faza 1, ceo tim; podrazumevani prostor)

Pisanje taktike: editor, provera dok kucaš, nacrt putanje. Brza simulacija meča ili testa, protivnici i scenariji
stola, puštanje rezultata. Izvor je uvek sim.

#### 7.2 Test dela (faze 2-3, Petar)

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

#### 7.3 Vožnja (faze 2-3)

Pokretanje taktike, kao test ili kao meč (naoruži, činč, 100 s), uživo. ESP panel (ekran i tasteri) i praćenje.
Izvor po delu, od sve-sim (današnji Live) do sve-pravo (§ 8).

#### 7.4 Snimci

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

#### Podešavanja (nisu radni prostor)

Profil robota, repo (pull i save), veza sa robotom.

Robotski prostori se ne kriju. Kad robot nije povezan, jasno to kažu.

### 8. Izvor podataka po delu

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

### 9. Uvek vidljivo

Traka se vidi u svim prostorima čim nešto radi:

- **izvor**, krupno i u boji: SIM / ROBOT / HIBRID / SNIMAK;
- **poza**;
- **stanje:** miruje / naoružan / meč + vreme / korak i ime;
- **detekcija sada:** šta lidar i IR vide i da li to zaustavlja robota;
- **poslednja odluka i razlog;**
- **STOP** (i Esc), čim je povezan pravi robot ili nešto radi.

Pri puštanju snimka traka pokazuje stanje u tom trenutku snimka.

**9a. STOP** zaustavlja sve, i kretanje i taktiku, na robotu i u simulaciji, kao taster STOP na robotu.

### 10. Snimanje

- Svaka sesija sa pravim robotom (test dela i vožnja) snima se automatski, lokalno, van gita.
- U repo idu samo snimci sačuvani sa „Save run“ (`simulator/runs/`, kao danas).
- Simulacije se snimaju samo na zahtev.

### 11. Zahtevi prema robotu (ESP strana)

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

### 12. Odnos prema postojećim planovima

- **Zamenjuje strukturu** iz `plan-ui-senzori-kalibracija.md` (U1: kartice Simulate/Live/Robot) i
  `plan-kontrolna-tabla.md` (B3: Robot kao prva kartica).
- **Iz `plan-kontrolna-tabla.md` sadržajno ostaju:** A (lidar vidljiv), B1 (telemetrija v2), C (ručne komande),
  D (ekran na daljinu, push i flash iz UI-ja).

### 13. Za kasnije

- više robota (PAMI);
- joystick sa deadman-om;
- automatska kalibracija iz snimka (K0/K1);
- baterija (INA3221);
- flešovanje STM32 i slanje koda iz UI-ja;
- ESP ekran na daljinu, ako ne stigne u Vožnju.

### 14. Ostavljeno graditelju

- izgled i raspored panela (ux-expert, superdesign);
- arhitektura koda i model panela (architect-review);
- kako se tačno lažiraju delovi na robotu.

### Predlozi doneti tokom razgovora (nisu izričito tražene odluke)

- pravilo „taktika radi tamo gde je pogon“ (iz odluke da taktika radi na pravom ESP-u);
- ručne komande su koraci, ne vožnja, i svaka ima „kopiraj u taktiku“;
- izvor u traci krupno i u boji;
- automatsko snimanje svake sesije sa pravim robotom;
- automatski snimci ostaju lokalni, van gita;
- „simuliraj isto“ uz snimak sa robota;
- robotski prostori se ne kriju, a Taktike su podrazumevani prostor;
- UI mora da radi i bez ESP izmena;
- odbačene tačke lidara prikazuju se drugom bojom.

# Arhitektura

## Pregled arhitekture: eurosim + web, prema `docs/plan-redizajn-interfejsa.md`

**Ukratko:** temelj je dobar, jer simulacija, Live i robot već prave isti snimak. Fale tri stvari:

- **sloj „izvor“** između UI-ja i onoga što proizvodi podatke;
- **model panela** u web-u;
- **opis protokola prema laptopu.**

Predlog je prelazak u osam faza (F0–F7), tako da simulator radi posle svake.

### 1. Trenutno stanje

**Šta valja i ostaje:**

- Pravi ESP kod radi nad simuliranim STM32, uz procesnu izolaciju.
- Snimak ima jedan oblik: frame-ovi i događaji.
- `view3d.js`, `charts.js` i `esp.js` su već komponente sa `set*()` API-jem.
- `lidarsrc.py` je, u stvari, već obrazac „zamenljivog izvora dela robota“.
- Bez build koraka, radi bez interneta.

**Problemi:**

| # | Problem | Gde |
|---|---|---|
| 1 | **UI zna odakle stižu podaci.** Postoje dva WebSocket-a sa različitim komandama: `/ws/live` prima torke iz `Sim.command`, a `/ws/robot` prima `push/run/stop`. Web ima dve paralelne putanje. | `server.py:280`, `:489`; `app.js:931` vs `:1037` |
| 2 | **Robot glumi simulaciju.** `TelemRecorder` popunjava polja lažnim vrednostima (`ox=x`, `w: None`, `reg: ""`, `ir: 0`), pa UI ne razlikuje „nema podatka“ od „nula“. Ishod koraka se pogađa parsiranjem teksta dnevnika. | `robotlink.py:85-91`, `:113` |
| 3 | **Hibrid je zakrpa unutar `Sim`-a.** `RobotLidar` otvara **svoju** UDP pretplatu ka robotu, odvojeno od `RobotLink`-a. Lozinka ide kroz query string. | `sim.py:72`, `lidarsrc.py:47`, `app.js:938` |
| 4 | **`app.js` drži sve u globalnim promenljivim.** To su `run`, `live`, `ed`, `info`, `opponents`, `tableEl`, `ref`… i svaki deo čita svaku. `main()` ima 246 redova i povezuje sve. `live` čita 11 različitih delova. | `app.js:15-20`, `:1206-1451` |
| 5 | **Live i Robot su duplirani.** `liveData` je „zajednički“, ali ga Live ne koristi i ima svoju kopiju sa **drugačijim** pravilom zastarelosti lidara (400 vs 800 ms). Postoje tri STOP-a, tri „kraj“, dva Follow-a. | `app.js:955-976` vs `:1022` |
| 6 | **`server.py` radi sve:** simulacije, snimke, scenarije, CRUD taktika, git, robota, virtuelnog robota, profil. `app[STATE]["last"]` upisuju četiri mesta. | `server.py` (690 redova) |
| 7 | **Live ponovo gradi ceo snimak na svaki tick.** `buildRun` prolazi sve događaje, pa posao raste kroz sesiju; najteži su krugovi lidara. | `app.js:914-929` |
| 8 | **Protokol prema laptopu nije opisan.** `protocol.yaml` najavljuje `e2h`, ali nema nijednu poruku. Ključevi telemetrije (`t ok v x y th sp st mm tac i n…`) su ad hoc u tri fajla: `telem.py`, `robotlink.py`, `tools/watch.py`. Komande upload servera su tekst bez šeme. | `protocol.yaml:2`, `telem.py:116` |

### 2. Da li protokol i server nose ono što spec traži

| Potreba iz spec-a | Danas | Šta fali |
|---|---|---|
| Poza, odometrija, brzina | ✔ telemetrija | – |
| `w`, IR raw i maska, uptime | STM32 ih šalje ESP-u (STATUS v5) | ESP ih **ne prosleđuje** laptopu |
| Zdravlje veze, krug petlje, RAM, verzija | samo u `STAT` (na zahtev) | periodično, u telemetriji |
| Stanje aktuatora | **nigde**, ni u STM32 protokolu (samo ACK/DONE) | ESP vodi stanje iz svojih komandi i šalje ga |
| Ishod koraka | parsiranje teksta dnevnika | strukturisan `step_end` |
| Odluka + razlog | ne postoji | tac API + događaj `decision` |
| Lidar sirovo | ✔ binarni `LIDR`, 360 binova | – |
| Rezultat detekcije sa robota | ne postoji | objekti + odluka u telemetriji |
| Ekran ESP-a | ne | kasnije (D1) |
| STOP, RUN, PUT, LIDAR ON/OFF, RESET | ✔ upload server | – |
| MOVE, ROTATE, GOTO, ACTUATOR, IR_MASK, SET_POSE ručno | STM32 ih **već** razume; ESP nema upload komande | samo prosleđivanje na ESP-u |
| Odbijanje u meču | ✔ `BUSY_OK = (LOG, STOP, STAT)` | ručne komande samo dodati van tog spiska |
| Čuvar veze za ručne komande | ne. TCP je jedna veza po komandi; `WATCH` traje 10 s, što je presporo | UDP „MAN“ keepalive na ~200 ms; bez njega ESP šalje STOP |
| Lažirani delovi na robotu | ne | config na ESP-u (kombinacija c) |

Dobra vest: protokol ESP↔STM32 je kompletan za ručno upravljanje. Sav posao je na granici ESP↔laptop.

### 3. Predlog

```
 ESP (pravi)        laptop: server                                        browser
┌──────────┐      ┌───────────────────────────────────────────────┐     ┌───────────────────────────┐
│ telem v2 │─UDP─▶│ RobotSource ─┐                                │     │ store (jedno stanje)      │
│ upload + │◀TCP──│              │   Session  ── /ws/session ────────▶│  ├ traka (uvek vidljiva)   │
│ MAN/ručno│      │ SimSource ───┤   (izvor + delovi + snimak +   │     │  ├ radni prostori          │
└──────────┘      │ ReplaySource ┘    capabilities + komande)     │     │  │   = lista panela        │
                  │ api/: tactics, runs, repo, profile, scenarios │     │  └ paneli: view3d, charts,│
                  └───────────────────────────────────────────────┘     │     esp, lidar, pogon…    │
                                                                         └───────────────────────────┘
```

#### 3.1 Izvor iza jednog interfejsa (server)

`Session` = **pogon** (`sim` | `robot` | `replay`) + **izvori delova** (lidar, IR, mehanizmi, protivnici). To direktno
sledi pravilo „taktika radi tamo gde je pogon“ i tabelu a–d iz spec-a.

- `SimSource` obuhvata `Sim` u procesu. Brza simulacija je sesija koja odmah završi, Live je ista sesija u
  stvarnom vremenu. Delovi dolaze kroz *provajdere*, i to je uopšten današnji `lidarsrc` (sim / robot / fajl).
- `RobotSource` obuhvata `RobotLink`. **Jedna** veza ka robotu, preko koje ide i lidar za hibrid.
- `ReplaySource` pušta sačuvan snimak.
- Svi izvori šalju isti tok: frame-ovi, događaji i **`capabilities`** (može pauzu, brzinu, ručnu vožnju, ESP
  ekran…). Postoji jedan rečnik komandi: `stop`, `run`, `arm`, `cord`, `move`, `act`, `ir_mask`, `btn`… Izvor koji
  nešto ne podržava odgovara „nepodržano“.
- **UI pali kontrole po `capabilities`, a ne po režimu.** Tako UI ne zna odakle podaci dolaze. Pravila
  bezbednosti (odbij u meču) proverava ESP ili server, a ne samo UI.

#### 3.2 Snimak v2

Jedan modul pravi snimak za sva tri izvora.

- Kad podatak ne postoji, polje je `null` ili ga nema. Nikad lažna vrednost.
- Meta nosi verziju taktike (git/sha), stranu, scenario, profil i konfiguraciju izvora. Od toga zavise
  „simuliraj isto“ i poređenje.
- Novi događaji: `decision`, `detect`, `manual`, strukturisan `step_end`.
- Učitavač čita i v1, pa stari `simulator/runs/` ostaju upotrebljivi.

#### 3.3 Paneli i radni prostori (web)

- **`store`:** jedan objekat stanja (sesija, snimak, kursor vremena, izbor, izvori) sa `subscribe`. Zamenjuje
  globalne promenljive.
- **Ugovor panela**, namerno mali:
  ```js
  export default { id, title, workspaces: ['test', 'voznja'], needs: ['lidar'],
                   mount(el, ctx), update(state) }   // ctx.command(...) za akcije
  ```
  Nova funkcija = novi fajl u `web/panels/` i jedan red u registru. Panel čita samo iz `store`-a i šalje samo
  `ctx.command`.
- **Radni prostor** = lista panela + početni raspored. **Traka** je fiksni deo okvira, nije panel.
- `view3d`, `charts` i `esp` ostaju i postaju unutrašnjost panela.
- Snimak se dopunjava (append), ne gradi ponovo na svaki tick.
- I dalje ES moduli bez build koraka. Bez framework-a, jer aplikaciju održava jedan čovek.

#### 3.4 Server po modulima

`session.py` (WebSocket + izvori) i `api/` za taktike, snimke, repo, profil i scenarije. Procesni radnik ostaje.

#### 3.5 Protokol prema laptopu u `protocol.yaml`

- odeljak `e2h`: polja telemetrije v2, lidar paket, `detect`, `decision`;
- odeljak `h2e`: upload komande i `MAN`.

`gen.py` iz toga pravi jednu definiciju koju dele `telem.py`, `robotlink` i `tools/watch.py`. Telemetrija nosi
verziju; stari firmver se i dalje čita, kao danas STATUS v3/v4/v5. Spora polja (RAM, verzija) idu 1 Hz, da se ne
optereti petlja na ESP-u.

### 4. Šta skloniti

| Šta | Gde | Postupak |
|---|---|---|
| Dvostruka putanja Live/Robot (UI i server) | `app.js:931`/`:1037`, `server.py:280`/`:489` | jedna `Session` |
| `liveColumns` = `columns()` | `app.js:906`, `server.py:124` | jedno mesto |
| `RobotLidar` sa svojom UDP pretplatom | `lidarsrc.py:47` | deo `RobotSource`-a |
| Lažna polja u `TelemRecorder`-u, ishod iz teksta dnevnika | `robotlink.py:85`, `:113` | `null` + strukturisan događaj; parser ostaje samo za stari firmver |
| Kartice Simulate/Live/Robot, `#mode`, `rowSim/rowLive/rowRobot`, 3× STOP, 2× Follow, 3× „kraj“ | `index.html` | traka + radni prostori |
| Ogledanje strane kopirano 4× u JS-u, 4 varijante u Python-u | `app.js:692, 1243, 1252, 1258`; `preview.py:59`, `field.py:40`, `opponents.py:31` | jedan `side.js` / `tac.mirror_xy` |
| Lista taktika (glob) 5×, provera imena 3×, `dumps` 4× | `server.py` | pomoćne funkcije |
| Lozinka: regex kopiran | `robotlink.py:28` vs `tools/espnet.py:19` | koristiti espnet |
| Sto u SVG-u sa ručno upisanim 3000×2000 | `app.js:814` | iz `info.field` |
| Mrtvo: `#logcard`, `button.live-on`, `#stepscard .tablewrap`, `mk` u `view3d.js:447`, `tab` u `app.js:643`, grana `stat` | | obrisati |
| **Greška, ne mrtvo:** virtuelni robot se nikad ne gasi (`action: stop` niko ne šalje) | `server.py:577`, `app.js:1310` | ugasiti na Disconnect |
| **Greška:** `openProfile` menja aktivni profil samo da bi ga pročitao | `app.js:1098` | odvojiti čitanje od izbora |
| `preview.py`: treća verzija tac API-ja (lažni tac) | `preview.py:128-260` | ostaje za sada (brz nacrt); rizik razilaženja, vidi 5.6 |

### 5. Rizici

1. **Prepisivanje svega odjednom usred sezone** pokvari alat timu. → Postepena zamena: nova sesija i okvir idu
   pored starog, a stari putevi ostaju kao tanki alijasi dok novo ne pokrije sve.
2. **Previše arhitekture za jednog održavaoca.** → Ugovor panela od četiri polja, bez framework-a i build-a. Sesija
   ima tri izvora, ne opšti sistem plugin-ova.
3. **Bezbednost pravog robota.** Ako se ručne komande zabrane samo u UI-ju, greška u UI-ju pokreće robota u meču.
   → Provera na ESP-u (`busy()`), keepalive koji samo zaustavlja (njegov izostanak staje, pa ne treba lozinka), a
   STOP ide i mimo sesije.
4. **Petlja na ESP-u** (MicroPython, JSON na 10 Hz). Nova polja produžavaju krug. → Meriti krug petlje pre i posle,
   spora polja na 1 Hz.
5. **Format snimka:** sačuvani snimci su u gitu. → v2 čita v1; test sa postojećim `simulator/runs/`.
6. **Razilaženje** `preview.py` / `apidoc.py` / `tac.py`. → Test koji poredi potpise sa `tac.py`.
7. **UI testovi** (Playwright) vezani za id-jeve. → Prepravljaju se po fazama, svaka faza završava sa zelenim
   testovima.
8. **Mitigacija za ESP rizike:** virtuelni robot (`sim.py robot`) pokreće **pravi** `telem.py` i `upload.py`.
   Svaka ESP izmena se prvo proba na njemu, bez robota.

### 6. Faze prelaska (simulator radi posle svake)

| Faza | Šta | Gde | Odobrenje |
|---|---|---|---|
| **F0** | Čišćenje bez promene ponašanja: mrtvo, duplikati (ogledanje, glob, lozinka, `dumps`), Live koristi `liveData`, gašenje virtuelnog robota, `openProfile`. Plan A iz kontrolne table: lidar crtan i bez poze. | simulator | „da“ |
| **F1** | Snimak v2 (jedan modul, `null`, bogata meta, čita v1). `server.py` podeljen na module, ponašanje isto. | simulator | „da“ |
| **F2** | `Session` + `SimSource` / `RobotSource` / `ReplaySource` + `capabilities` na `/ws/session`. `/ws/live` i `/ws/robot` ostaju kao alijasi. Lidar za hibrid ide kroz `RobotSource`. | simulator | „da“ |
| **F3** | Okvir u web-u: `store`, registar panela, traka, radni prostori. Prvi prostor je **Taktike**, sastavljen od postojećih delova; tok za tim ostaje isti. | simulator | „da“ + ux-expert/superdesign pre ovoga |
| **F4** | Prostori **Vožnja** i **Snimci**: poređenje (tabela koraka, poravnati grafici, „simuliraj isto“), automatsko snimanje sesija sa robotom. Uklanjaju se stare kartice. **Test dela → Lidar** (međukorake računa laptop iz sirovih krugova; radi već sa današnjim firmverom). | simulator | „da“ |
| **F5** | Telemetrija v2 + `e2h` u `protocol.yaml` + `gen.py`: IR, `w`, zdravlje, aktuatori, strukturisan `step_end`, `decision`. Paneli IR, Zdravlje i Odluke. | **ESP** + simulator | posebno „da“ za ESP |
| **F6** | Ručne komande na upload serveru + `MAN` keepalive + provera u meču. **Test dela → Pogon, Mehanizmi, IR**; „kopiraj u taktiku“. | **ESP** + simulator | posebno „da“ |
| **F7** | Lažirani delovi na robotu (kombinacija c), rezultat detekcije lidara u telemetriji. | **ESP** + simulator | posebno „da“ |

Posle F7 sledi sve iz „Za kasnije“ u spec-u. Više robota je već pokriveno, jer svaki robot dobija svoju `Session`.

Redosled: F0 i F1 odmah, jer su mali i bez rizika. Između F2 i F3 ide ux-expert/superdesign, jer F3 je prvo mesto
gde se izgled stvarno menja.

# IA audit

Kontekst: jedna stranica, ~60 kontrola i prikaza. Petar koristi sve, kroz tri faze sezone; tim samo piše taktike i
gleda simulaciju. Režimi cilja: **Tk** Taktike · **TD** Test dela · **Vo** Vožnja · **Sn** Snimci · **Pod** Podešavanja ·
**Tr** traka.

## Popis (sažeto, sa oznakama D duplirano · PM pogrešno mesto · SK skriveno a treba vidljivo · V višak)

| Šta | Gde sada | Režim | Oznaka |
|---|---|---|---|
| Tactic ▾, Side ▾ | gornja traka red 1 | Tk, Vo | ✓ |
| ✎ Editor | gornja traka | Tk | PM: editor je dugme, ne radni prostor |
| Simulate / Live / Robot | gornja traka | – | PM: podela po izvoru, ne po zadatku |
| ⋯ Runs (Save run, Load run) | gornja traka | Sn | SK: ceo režim iza „⋯“ |
| ⎇ Repo, ⚙ Profile | gornja traka | Pod | ✓ |
| Mode ▾ (Match/Test), ▶ Run | red 2, Simulate | Tk | D: isto kao Arm/Run test u Live-u |
| Lidar ▾ (sim/robot/snimak) | red 2, Live | Vo, TD | PM + SK: host i lozinka su u drugoj kartici |
| Start Live, Arm, Pull cord, Run test | red 2, Live | Vo | D: Pull cord i na timeline-u |
| ■ STOP | Live, Robot, ESP panel | Tr | D: 3 STOP-a + Esc |
| ×0.25..×5, ⏸, Follow, End | red 2, Live | Vo | D: druga brzina na timeline-u; ▶/⏸ u Live-u znači Follow; Follow ×2 + „follow the robot“ (kamera); End/Disconnect/Start |
| Connect… (host, lozinka, Virtual robot) | red 2, Robot | Pod, Tr | PM: host služi i hibridu |
| pill stanja robota | red 2, Robot | Tr | SK: malo, bez poze, izvora, greške |
| Push / Push & Run | red 2, Robot | Vo | ✓ |
| msg (poruka) | red 2 | Tr | SK: jedan red se prepisuje, nema istorije |
| 3D / Top | sto | svi | ✓ |
| Show ▾ (11 prekidača) | sto | svi | V: iste težine; „game elements“ menja simulaciju, ne prikaz |
| + Opponent, + PAMI, scenario, Reset table | sto | Tk | V u robotu; PM: postavka pomešana sa prikazom |
| kartice kamenoloma i protivnika | sto | Tk | ✓ |
| 📌 Pin, compare with ▾ | sto | Sn | PM: glavni alat faze 3 je mala kartica preko stola |
| ESP panel | sto | Vo | V: stalno vidljiv i ugašen u brzoj sim i u Robot-u |
| kartica rezultata, kursor | sto | Tk, Sn | ✓ |
| dupli klik = koordinate; Alt+klik = tačka u kod | sto | Tk | SK: samo u tooltip-u |
| fioka Gambit Micro komandi | preko stola | Tk | PM + D sa „📖 Commands“ |
| State: 18 ćelija | desna kolona | Tr + TD | V + SK: sve iste težine; kod robota „–“ i lažna „odom err 0.0“ |
| IR panel (klik = maska u Live-u) | desna kolona | TD, Vo | ✓, klik skriven |
| trenutni korak + traka | desna kolona | Tr | ✓ |
| Steps, Log (+ ESP↔STM32) | desna kolona | Tk, Sn, Vo | ✓ |
| ⏮ ◀ ▶ ▶| ⏭, ×0.25..×25, vreme, traka koraka, zastavice, ⏵ PULL CORD, klizač | timeline | Sn, Tk, Vo | D: brzina i ▶ menjaju značenje u Live-u; PM: Pull cord u alatu za puštanje |
| 3 grafika (brzina, ω, točkovi) | timeline | Sn, TD | SK + V: nema grafika ugla; kod robota 2 od 3 prazna; nema grafika jedan preko drugog |
| editor: New, File ▾, Save, auto-sim, 📖 Commands, Problems, Draft | levo | Tk | ✓ (D: Commands = fioka) |
| Repo traka i prozor, Profile prozor | prozori | Pod | ✓ |
| prečice | nigde nabrojane | svi | SK |

## Nalazi po težini

**Critical**
- Izvor podataka (SIM / pravi / hibrid / snimak) se ne vidi; posle End/Disconnect sesija tiho postaje snimak u istom
  prikazu. → Traka sa izvorom krupno i u boji. (Every page is a front door)
- Lažni podaci izgledaju kao pravi (kod robota „odom err 0.0 mm“, prazni grafici, „–“ isto kao nula). → Prikazivati
  samo ono što izvor ima; ostalo „nema sa robota“. (Information scent)

**Major**
- Organizacija po izvoru, ne po zadatku; Test dela ne postoji; Snimci iza „⋯“; poređenje mala kartica. → Četiri
  radna prostora.
- Nedosledni nazivi: Follow (vreme) vs follow the robot (kamera); ▶/⏸ = Follow u Live-u; pet glagola za „pokreni“;
  End/Disconnect/⋯ Runs/Show ▾ bez mirisa; mešan engleski/srpski; „Gambit Micro“ vs „tac API“. → Pokreni, Naoruži,
  Činč, Test, Završi, Poveži, Prati (= vreme), „Kamera prati robota“; jedan jezik.
- Skrivena zavisnost hibrida (lidar u Live-u, host u Robot kartici). → Jedan blok Izvori.
- Duplikati: 3× STOP, 3× kraj, 2× Follow, 2× brzina, Mode vs Arm/Test, 2× Pull cord, 2× pomoć. → Po jedan.
- State kartica: 18 ćelija iste težine. → Poza/meč/korak na traku; dijagnostika u Test dela → Pogon i Snimke.
- Postavka stola svuda, i uz pravog robota. → Samo Taktike (i Vožnja sa sim izvorom).

**Minor**
- ESP panel ugašen tamo gde ne radi; poruke se prepisuju; prečice skrivene; snimci bez pregleda (test rasta);
  Show meša sadržaj i izgled.

**Radi dobro:** jedna lista taktika; klik na korak/dnevnik/grafik skače na trenutak; kartica rezultata; repo traka;
zaključavanje kartica tokom sesije (sada se zamenjuje trakom).

**Top 3:** (1) traka sa izvorom, pozom, stanjem i jednim STOP-om, bez lažnih vrednosti; (2) četiri radna prostora;
(3) jedan sistem naziva i jedan blok Izvori.

# UX spec

## Režimi → radni prostori

| Ranije | Sada | Zašto |
|---|---|---|
| taktike | Taktike | pisanje + brza simulacija su jedan ciklus |
| sim | Taktike (brza) i Vožnja (stvarno vreme, izvor SIM) | brza sim proverava tekst; Live je „robot je upaljen“ |
| live / robot | Vožnja | isto mesto za sim, hibrid i robota; razlikuje ih izvor |
| upravljanje | Test dela | ručno je van meča, po delu robota |
| replay | Snimci | puštanje + poređenje |
| podešavanje | Izvori / Repo / Profil / Pomoć (nisu radni prostor) | retko |

## Okvir (varijanta A)

```
┌──────┬──────────────────────────────────────────────────────────────────────────────────────┐
│ Tak  │ TRAKA ▌ROBOT eurokik▐ ● povezan │ 1240, 830 · 92° │ MEČ 62.8 s │ 7/15 ka_… ▓▓░ │ 👁 … │ ⚠1 │ ■ STOP │
│ Test ├──────────────────────────────────────────────────────────────────────────────────────┤
│ Vož  │ kontekstna traka komandi radnog prostora                                              │
│ [SIM]├──────────────────────────────────────────────────────────┬───────────────────────────┤
│ [ROB]│ GLAVNI PROSTOR (fiksan po radnom prostoru)               │ BOČNA KOLONA: sklopive     │
│ Snim │                                                          │ kartice po prioritetu      │
│      ├──────────────────────────────────────────────────────────┴───────────────────────────┤
│ Izv  │ DONJA ZONA: vreme ili grafici ili aktuatori                                          │
│ Repo │                                                                                      │
└──────┴──────────────────────────────────────────────────────────────────────────────────────┘
```

**Traka** (8 polja, polje bez podatka se ne prikazuje): Izvor (najveće; SIM plavo #1f5f99, ROBOT crveno #c62828,
HIBRID amber, SNIMAK sivo; i tanka linija preko vrha) · Veza · Poza · Meč (miruje / NAORUŽAN / MEČ t odbrojava /
KRAJ; drugo po veličini u meču) · Korak n/N + ime + traka do timeout-a · Detekcija · ⚠ n (klik = dnevnik grešaka) ·
■ STOP (uvek kad radi sesija sa robotom ili Live; Esc isto, iz svakog prostora). Traka uvek prati sesiju uživo, i
dok gledaš snimak; bez sesije pokazuje SNIMAK u trenutku kursora. Klik na traku vodi u prostor sesije.

**Navigacija:** prostor se uvek menja (u meču ostali samo čitaju); svaki prostor pamti šta je na stolu; veze:
Vožnja Završi → Otvori u Snimcima; Snimci „Simuliraj isto“; Test dela „kopiraj u taktiku“ → editor; rezultat
„NOT OK korak 7“ → skok; ⚠ → dnevnik grešaka. Prečice: Alt+1..4 prostori, Esc STOP, Ctrl+Enter Pokreni/Naoruži,
Space/←/→/Shift+←/→ vreme, ? spisak prečica.

## Radni prostori

- **Taktike** (podrazumevan, tim): editor (Novo · Sačuvaj · Fajl ▾, Problemi | Komande) + sto (nacrt ljubičasto,
  poslednja simulacija, kartica rezultata); gore Taktika ▾, Strana, ▶ Pokreni [meč | test], auto-sim; bočno Koraci
  (otvoreno), Postavka stola (protivnici, PAMI, kamenolomi, scenariji, „elementi igre“), Dnevnik.
- **Test dela** (Petar): podkartice Lidar · Pogon · Mehanizmi · IR; šema sirovo → obrađeno → odluka + ručno.
  Lidar: sto + radar (radi i bez poze), slojevi (sirovo / van stola / grupe), rezultat sa oznakom robot/laptop, Hz,
  tačke, starost, Snimi krugove. Pogon: zadato vs odometrija, dijagnostika, MOVE ±50/100/300, ROTATE ±15/90, GOTO
  klikom, brzina, poslednja komanda + „kopiraj u taktiku“. Mehanizmi: lista aktuatora. IR: 8 senzora, maska.
- **Vožnja**: Taktika, Strana, Naoruži, Činč, Test, brzina/pauza (samo sim), Završi; sto prati robota; bočno Korak
  sada, Odluke, Dnevnik (filter samo greške, ESP↔STM), ESP (samo ako izvor ima ekran), Zdravlje; dole Prati (= vreme),
  traka koraka, klizač, zastavice, grafici sklopljeni. Bez sesije: „Pokreni sesiju“ sa izborom izvora.
- **Snimci**: A vs B, lista (datum, izvor R/S/H, taktika, ishod, filter), tabela koraka A/B/Δ, grafici jedan preko
  drugog poravnati po koraku, Simuliraj isto, Sačuvaj u repo. Jedan snimak = obično puštanje.

**Izvori ▾**: unapred a (sve sim), b (hibrid lidar), c (robot + lažiran mehanizam), d (sve pravo); po delu sim /
pravi / snimak / lažiran; nedozvoljeno sivo sa razlogom; veza sa robotom (host, lozinka, Poveži, Virtuelni robot);
tokom sesije samo čitanje.

## Stanja

| Stanje | Traka | Prostori |
|---|---|---|
| ništa ne radi | SIM · spremno; nema STOP-a (ili siv) | sve |
| povezivanje | ROBOT · povezivanje… + Otkaži | čekam telemetriju |
| robot nije povezan | – | „Robot nije povezan“ + Poveži / Virtuelni robot; bez praznih panela |
| povezan bez STM32 | „nema poze (STM32)“ žuto | lidar radar; ručna vožnja siva sa razlogom |
| podaci kasne > 1.5 s | „podaci stari 2.3 s“ žuto | poslednje vrednosti posivljene |
| veza izgubljena > 5 s | crveno; STOP i dalje šalje | zamrznuto; sesija se ne završava sama |
| greška | ⚠ n crveno | zastavica na timeline-u; red u editoru |
| naoružan | NAORUŽAN · čeka činč | ručno, Izvori, Push zaključani sa razlogom |
| meč traje | MEČ t odbrojava | sve što menja robota zaključano; STOP radi |
| kraj meča | KRAJ · rezultat | Otvori u Snimcima |
| puštanje snimka | SNIMAK · ime | – |
| hibrid | HIBRID · pogon sim · lidar pravi | brzina ×1 |
| podatka nema u izvoru | polje se ne prikazuje | „nema sa robota“ umesto „–“ ili nule |

## Nova funkcija = novi panel

1. Panel se prijavljuje: ime, radni prostor(i), zona (bočna | donja | deo), prioritet, šta mu treba.
2. Glavni prostor je zaključan po prostoru. 3. Bočna kolona: novi panel ulazi sklopljen; najviše tri otvorena
podrazumevano; stanje se pamti po prostoru. 4. Izvor nikad ne daje podatak → panel se ne prikazuje; privremeno fali →
siv sa razlogom. 5. Nov deo robota = podkartica Test dela. 6. Nov radni prostor samo uz sopstveni glavni objekat i
nedeljnu upotrebu. 7. Traka ima budžet od 8 polja.

## Ostalo

Komponente: bez novih biblioteka (three.js, uPlot, CodeMirror ostaju). Ekran: cilj 1920×1080, minimum 1366×768;
ispod 1500 px bočna kolona se sužava; ispod 850 px visine grafici sklopljeni; traka nikad ispod polja Izvor, Meč, STOP.
