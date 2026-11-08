# Plan: simulator, editor i API taktika (sledeći krug)

Nacrt za budući rad, 2026-11-08. **Ništa nije menjano u kodu i ništa nije commit-ovano.** Uz svaku stavku:
šta je traženo, kako je sada (fajl:linija), predlog rešenja koje je dobro za ceo sistem, alternativa, kako
proveriti. Promptovi za nov chat su u `docs/promptovi-simulator-unapredjenja.md`.

Kako je ovo napravljeno: pročitan kod simulatora (`simulator/eurosim/*.py`, `simulator/web/*`), ESP API
(`ESP32/lib/tac.py`), repo Gambit (`plus381-robotics/Gambit`). Bag sa plavom stranom je **reprodukovan** u
pregledaču (Playwright). Dve nove taktike (dodatak A) su **proverene u simulatoru** na obe strane.
Nijedna izmena nije isprobana; procene veličine su okvirne.


> **Stanje (2026-11-08): urađeno i na `main`** S1-S10 (simulator), S11 (ime Gambit Micro, modul `gambit` na
> ESP-u, funkcije iste), S12 (protokol v5: `near=True` u `goto`/`move`), S13 (`sve_komande.py`,
> `kamenolomi.py`). Exe i GitHub Release se više ne prave (pokretanje iz repoa: `start.sh` / `start.bat`).
> **Ostalo / nije probano:** `start.bat` na Windows-u bez Python-a; "Save to GitHub" i kloniranje privatnog
> repoa iz aplikacije; STM deo (v4, v5) samo `gcc -fsyntax-only`, nije flešovan; na BlackPill-u nema IR koda,
> pa `near` tamo za sada samo ograničava brzinu (IR kod treba da zove `comm_port_set_obstacle`); opcija
> "pogled sa moje strane" (S14) i prevlačenje tačke nacrta (S8) nisu urađeni. Promptovi ispod su pisani pre
> implementacije: za nastavak koristiti samo ono što je ostalo.

---

## 0. Pregled i redosled

| # | Stavka | Gde | Prioritet | Veličina | Zavisi od |
|---|---|---|---|---|---|
| S1 | Bag: plava strana (robot ostaje na žutoj) | simulator | **visok** | mala | - |
| S2 | Save as (i Duplicate) za taktike | simulator | visok | mala | - |
| S3 | Autocomplete: Tab, lista na prvo slovo, cela komanda | simulator | visok | mala | - |
| S4 | API panel vidljiv i jasan, ime "Gambit Micro" u UI | simulator (+ opisi u tac.py) | visok | srednja | - |
| S5 | Tačke i ciljevi vidljiviji | simulator | visok | mala | - |
| S6 | IR zraci ispred/iza robota | simulator | srednji | mala | - |
| S7 | Putanja uživo dok se piše (bez Run) | simulator | **visok** | srednja-velika | S5 |
| S8 | Jasnije šta su x, y (pomoć pri pisanju, klik na mapu) | simulator | visok | srednja | S7 |
| S9 | Timeline: tačke po koraku, jasni koraci, činč | simulator | srednji | srednja | - |
| S10 | Sync: repo kao radni prostor, pokretanje bez instalacije | simulator + repo | **visok** | srednja | - |
| S11 | Ime API-ja: Gambit Micro (funkcije ostaju iste) | simulator UI (+ ESP modul uz odobrenje) | srednji | mala | - |
| S12 | Prilaz elementima: IR vidi kamenolom pa robot stane | ESP + protokol + STM (odobrenje) | **visok za meč** | srednja | - |
| S13 | Primer taktike: sve komande, kamenolom do kamenoloma | ESP32/tactics (odobrenje) | srednji | mala | S12 za pune prilaze |
| S14 | Pitanje: zašto postoje obe strane | objašnjenje + UX | - | mala | S1 |

Predlog redosleda:
1. **Faza A** (samo simulator, brzo): S1, S2, S3, S5, S6.
2. **Faza B** (pisanje taktika): S4, S7, S8, S9.
3. **Faza C** (tim): S10.
4. **Faza D** (ESP, protokol, STM, uz odobrenje): S11, S12, S13.

Svaka faza je jedan nov chat (promptovi).

---

## S1. Bag: na plavoj strani robot ostaje na žutoj, markeri se "sklone"

**Reprodukovano** (Live režim):
1. Live se pokrene sa izabranom žutom stranom.
2. Izabere se Blue, pa Arm match i Pull cord.
3. Pravi robot vozi po **žutoj** polovini, i to ogledano: završi na (601, 1200), ugao −90°.
4. Odometrija i ciljevi su na plavoj (2399, 800). Greška odometrije je **1842 mm**.
5. Brojevi koraka ostaju uz robota na žutoj, plavi prsten cilja je na plavoj. Zato izgleda kao da markeri
   "nestanu" sa mesta gde se vozi.

Brza simulacija (▶ Simulate) radi ispravno na obe strane.

**Uzrok** (iz koda):
- `simulator/eurosim/sim.py:109-110`: pravi robot se postavlja na START samo jednom, kad se Live pokrene,
  sa stranom izabranom u tom trenutku.
- Komande `arm` i `test` (`sim.py:345-349`) samo izaberu taktiku i stranu na ESP-u, robot se ne pomera.
  Komanda `place` postoji (`sim.py:358`), ali je UI nikad ne šalje.
- Sporedno:
  - `meta` (strana, boja robota, prikaz koordinata) ide u UI samo u prvoj poruci (`sim.py:409`), pa
    promena strane ne stiže do prikaza.
  - `#side` nema `change` handler (`web/app.js`), pa promena strane ne pokreće novu simulaciju; ostaje
    prikaz starog snimka.
  - ESP panel u 3D pogledu (dole desno) pokriva deo plave startne zone.

**Predlog:**
- U Live režimu, kad robot miruje (nije naoružan, ne vozi), promena strane ili Arm/Test sa drugom stranom
  postavi pravog robota na START te taktike, ogledano po strani. Isto bi uradio čovek koji robota prenese
  na drugu stranu stola.
  - Server: `command("arm"/"test")` poredi stranu sa poslednjim postavljanjem i zove `place`.
  - Dok meč traje, menjanje strane je zaključano (kao na ESP-u).
- `meta` slati i posle svake promene (strana, taktika), ne samo na početku.
- Brzi režim: promena strane označi prikazani snimak kao zastareo ("snimak je za žutu, Simulate za plavu")
  ili odmah pokrene novu simulaciju; simulacija traje 0,3-0,8 s.
- ESP panel: mogućnost da se skloni ili pomeri; 3D kamera da obuhvati ceo sto iznad panela.

**Alternativa:** u Live režimu zaključati izbor strane posle starta (mora End pa Live). Jednostavnije, ali
manje prirodno.

**Provera:**
- Playwright scenario iz ovog izveštaja: posle Arm sa plavom, robot je u plavoj zoni i greška odometrije
  je < 5 mm.
- Test servera: `arm` sa drugom stranom šalje `place`.

---

## S2. Save as za taktike

**Sada:** postoje Save (`/api/tactic/save`, provera konflikta po sha i HTTP 409, `eurosim/tactics.py:318-331`)
i "New" iz šablona (`web/app.js:503-512`). Nema Save as. Nesačuvani nacrti se čuvaju u localStorage
(`app.js:456`).

**Predlog:**
- Dugme **Save as** (Ctrl+Shift+S) i **Duplicate**: pita za ime.
  - Provera imena: malim slovima, slova/brojevi/_, ne sme da počinje brojem, jer ESP pravi
    `<ime>_obnova.py` i uvozi taktiku kao modul.
  - Ako ime postoji, traži potvrdu za prepisivanje.
- Server: `tactics.save(name, src, sha=None)` za nov fajl; ako fajl postoji, 409 dok korisnik ne potvrdi.
- Posle Save as editor prelazi na novi fajl, a nacrt starog se briše iz localStorage.
- Uz to (mala cena, korisno): **Rename** i **Delete** sa potvrdom.
  - Delete samo u radnom folderu.
  - `primer`/`provera` označiti kao primere, da se ne brišu slučajno.

**Provera:** test servera (Save as, konflikt, loše ime); Playwright: Save as pa izbor nove taktike u listi.

---

## S3. Autocomplete: Tab, lista na prvo slovo, cela komanda

**Sada** (`web/editor.js:31-62`, `89-97`):
- Predlozi dolaze iz tac API-ja. Funkcije se ubacuju kao snippet sa obaveznim argumentima, npr.
  `goto(${x}, ${y})`. Lista se otvara već na prvo slovo.
- **Tab nije vezan** za prihvatanje (prihvata se Enter-om); Tab samo skače između polja snippeta.
- Opisi u listi su kratki.

**Predlog:**
- Keymap pre podrazumevanog: `Tab` → `acceptCompletion` kad je lista otvorena, inače skok na sledeće polje
  snippeta, inače uvlačenje.
- Ctrl+Space: sve komande, grupisane: Kretanje, Čekanje, Aktuatori, Vreme meča, Pozicija, Ostalo.
- Snippet sa imenovanim poljima i jedinicama, npr. `goto(${x_mm}, ${y_mm})`, a za `goto` i varijanta sa
  uglom `goto(${x_mm}, ${y_mm}, deg=${ugao})`.
- U listi uz svaku komandu jedna rečenica običnim jezikom (iz S4), a sa strane mali panel sa primerom.
- Rangiranje: prvo komande koje počinju slovom, zatim one koje ga sadrže.

**Provera:** Playwright: kucanje `g` → lista ima goto, go_home; Tab ubaci `goto(x_mm, y_mm)` i kursor je
na `x_mm`; Tab prelazi na `y_mm`.

---

## S4. API panel: vidljiv, jasan, "Gambit Micro"

**Sada:**
- "tac API" je kartica pored "Problems" u istom panelu ispod editora (`web/index.html:80-85`,
  `style.css:124-127`), pa se ne vidi da postoji.
- Sadržaj se pravi iz `ESP32/lib/tac.py` preko `ast` (`eurosim/tactics.py:40-79`): `__all__`, potpisi,
  docstring-ovi.

**Predlog:**
- Dugme **📖 Komande** u traci editora, desni panel koji može da se skloni, sa pretragom.
- Za svaku komandu:
  - (1) jedna rečenica običnim jezikom;
  - (2) tabela parametara sa jedinicama i podrazumevanim vrednostima;
  - (3) šta vraća;
  - (4) primer;
  - (5) za komande sa x, y mala SVG slika stola sa osama i tačkom.
- Klik na komandu je ubacuje u kod.
- Ime u UI: **Gambit Micro** (naslov panela, šablon taktike, pomoć). Ime modula u kodu je S11.
- Opisi ostaju u `tac.py` kao docstring-ovi, jedan izvor istine.
  - Provereno: `mpy-cross` docstring-ove izbacuje (funkcija sa ~1200 znakova opisa: 39 B .mpy, bez opisa
    38 B), pa duži opisi ne troše RAM na ESP-u.
  - Format docstring-a: prvi red rečenica; zatim `x: ...`, `y: ...`; zatim `Vraća: ...`; zatim `Primer: ...`.
  - Test u simulatoru proverava da svaka komanda iz `__all__` ima sve delove (kao Gambit `api/gambit/init.luau`).
- Primer novog opisa za `goto`:

  > **goto(x, y)**: vozi robota do tačke na stolu. Robot se prvo okrene ka tački, pa vozi pravo.
  > `x`: koliko mm od **leve** ivice stola (žuta strana), 0..3000. `y`: koliko mm od **donje** ivice, 0..2000.
  > `deg` (nije obavezno): u kom pravcu robot gleda kad stigne: 0 = desno, 90 = gore, 180 = levo, −90 = dole.
  > `speed`: mm/s (podrazumevano 500). `reverse=True`: vozi unazad.
  > Vraća `True` ako je stigao, `False` ako ga je nešto zaustavilo (protivnik, vreme, greška).
  > Primer: `goto(600, 1000)`: 35 cm desno od startne zone, u visini sredine stola.

- Izmena docstring-ova je izmena u `ESP32/`, pa traži odobrenje (samo tekst, ponašanje se ne menja).

---

## S5. Tačke i ciljevi vidljiviji

**Sada** (`web/view3d.js:241-293`, `445-453`):
- Tačke koraka su krug r = 18 mm sa brojem; ciljevi GOTO su plavi prsten r = 22-30 mm sa natpisom.
- Putanja je bela, providnost 0,18. Na celom stolu (3 m) to su sitni detalji, a natpisi se gube iza
  elemenata.

**Predlog:**
- Tačke r ≈ 40 mm, debeo obod; natpisi uvek iznad svega (`depthTest: false`, `renderOrder`) sa tamnom
  podlogom.
- Natpis: broj + ime koraka (npr. `2 kamenolom 9`).
- Strelica smera na cilju kad je zadat ugao (`deg`).
- Putanja obojena po koraku (svaki korak svoja nijansa), deblja linija (u three.js `Line2` / `LineMaterial`).
- Veličina markera: klizač (mali/srednji/veliki).
- Isto u Top pogledu.
- Prelazak mišem preko tačke ističe red u tabeli koraka i liniju u editoru (veza sa S7, S9).

---

## S6. IR zraci ispred i iza robota

**Sada:**
- Senzori su u modelu: 4 napred, 4 nazad, nisko/visoko (`eurosim/plant.py:215-257`, profil `[ir]`,
  domet 250 mm).
- U snimku su samo bitovi `ir`, kao tekst u panelu State (`stm.py:409`, `app.js:85`).
- `ir_hits` se računa (`plant.py:143`), ali se ne snima. Zraci se ne crtaju.

**Predlog:**
- Snimati `ir_hits` (udaljenost pogotka ili domet).
- Crtati zrake iz stvarnih položaja senzora:
  - siva linija do dometa kad nema pogotka; crvena do tačke pogotka kad ga ima;
  - nisko i visoko različitom debljinom.
- Kutija "IR" u traci prikaza (uključeno podrazumevano).
- Domet i visine iz profila, pa promena profila odmah menja prikaz.
- Bitno za S12: pokazuje zašto robot stane ispred kamenoloma.

---

## S7. Putanja uživo dok se piše (bez Run)

**Sada:** `static_check` (`eurosim/tactics.py:180-276`) daje samo greške. Putanja postoji tek posle
simulacije.

**Predlog** (dva sloja):
1. **Brz nacrt (< 50 ms) na svaku izmenu teksta** (debounce ~200 ms).
   - Server izvršava taktiku sa **lažnim tac modulom** koji samo beleži komande i računa idealnu putanju:
     - `goto` je okret pa prava linija; `move` je prava; okreti se beleže; aktuatori postaju oznaka;
       `wait` je vreme;
     - komande vraćaju `True`; `wait_until` vraća `True`; ograničenje 200 komandi / 100 s.
   - Radi sa promenljivama, petljama, funkcijama i ogledanjem po strani (isti `mirror_xy`), što
     AST-parsiranje ne može.
   - Za svaku komandu se pamti broj reda u kodu.
   - Prikaz: isprekidana linija i numerisane tačke ("nacrt"), druga boja od snimka.
2. **Prava simulacija u pozadini kad se stane sa kucanjem** (~1 s), jer kratka taktika traje 0,3-0,8 s.
   - Prikazuje stvarne prepreke, BLOCKED, vreme. Prethodna se prekida kad stigne nova izmena.
   - Kutija "auto-sim" (podrazumevano uključena za taktike kraće od ~20 s simulacije).
- **Veza kod ↔ mapa:** kursor u redu sa `goto` ističe tu tačku na mapi; klik na tačku skače na red.
- Greška u kodu: ostaje poslednji dobar nacrt, posiveo, uz poruku.

**Alternativa:** samo AST (pronađi `goto(broj, broj)`). Jednostavno, ali puca na promenljivama
(`goto(750, GORE_Y)`) i petljama. Ne preporučuje se kao glavni put; može kao rezerva kad kod ne može da se
izvrši.

**Za ceo sistem:** isti lažni tac služi i za **procenu trajanja** taktike (za `TOTAL`, vreme do kraja meča i
biranje šta stigne do kraja meča).

---

## S8. Jasnije šta su x i y

**Sada:**
- Postoji prikaz koordinata ispod miša (`app.js:771-778`); dvoklik kopira koordinate taktike (`:779-785`).
- Mreža sa oznakama postoji samo u izgledu "grid"; podrazumevano je slika pravila, bez lenjira.

**Predlog:**
- **Uvek vidljiv lenjir** po ivicama stola (podeoci 100 mm, brojevi na 500 mm), **oznaka 0,0 u donjem
  levom uglu** i strelice "x →" i "y ↑", u 3D i Top pogledu.
- **Dok je kursor u komandi sa x, y:** na mapi se pojavi krst na toj tački, sa isprekidanim linijama do
  ivica i natpisom "x = 600 mm od leve ivice, y = 1000 od donje".
- **Biranje tačke klikom:** dugme "📍 tačka sa mape" (ili Alt+klik na mapu) ubacuje `goto(x, y)` na
  kursor, odnosno menja brojeve u komandi u kojoj je kursor.
- **Prevlačenje tačke nacrta** (S7) menja brojeve u kodu, ako su brojevi upisani direktno.
- Uz komandu u editoru (CodeMirror inlay) tihi natpisi `x=` `y=` `ugao=` ispred brojeva. Može se isključiti.
- **Na plavoj strani** i dalje se pišu koordinate žute strane; to se jasno kaže uz prikaz (vidi S14).

---

## S9. Timeline: tačke, koraci, činč

**Sada:**
- Ispod klizača su crtice na početku svakog koraka, crvene za neuspeh, sa nazivom u tooltip-u
  (`app.js:211-221`), plus tri grafika (`charts.js`).
- Činč se vidi samo u dnevniku (`stm.py:271-275`).
- U Live režimu postoji dugme "Pull cord" (`index.html:23`).

**Predlog:**
- **Traka koraka iznad klizača:** svaki korak je pravougaonik od početka do kraja, obojen po ishodu,
  sa brojem i imenom kad stane; klik skače na početak koraka.
- Tačke na grafiku brzine na početku/kraju svakog koraka.
- Posebne trake (uže): aktuatori (paralelno sa vožnjom), događaji (pad veze, restart STM32, prepreka).
- **Činč:** zastavica "ČINČ" na vremenu činča, i oznaka "NAORUŽAN" pre nje. Os vremena može da se
  prebaci na "vreme meča" (0 = činč, 100 s = kraj) sa senkom faze napada od 85 s.
- **Live:**
  - veliko dugme ČINČ na samoj traci i natpis "čeka činč" dok je naoružan; robot kreće tek na klik
    (tako već radi u režimu Match, samo nije jasno);
  - za pravog robota (Robot panel) ista traka sa stvarnim događajima iz telemetrije.
- Hover na korak ističe tačku na mapi i red u kodu (zajedničko sa S5 i S7).

---

## S10. Sync: repo kao radni prostor, bez instalacije

**Problem:**
- Svako skine aplikaciju; taktike i profil robota žive lokalno (u samostalnom režimu `~/Eurosim/`,
  `eurosim/paths.py:55-66`).
- Kad mehanika promeni profil, ostali to ne dobiju.
- Verzija aplikacije se ne zna.

**Šta već postoji:** `paths.find_repo` (`paths.py:22-35`) traži repo od foldera exe-a naviše. Ako se exe
pokrene **iz kloniranog repoa**, aplikacija već radi nad `ESP32/tactics` i `simulator/profiles` (režim
repoa).

**Opcije:**

| | Zajednički server | Deljeni folder (Drive) | **Repo kao radni prostor** |
|---|---|---|---|
| Istorija i povratak | treba napraviti | slabo | **git** |
| Rad bez interneta (takmičenje) | ne | delimično | **da** |
| Konflikti | treba rešiti | tiho prepisivanje | git ih pokaže |
| Najnovija verzija aplikacije | da | ne | **da (kod iz repoa)** |
| Održavanje | server, nalozi | malo | malo |

**Predlog** (repo kao radni prostor, dva načina pokretanja):
1. **Iz koda, bez instalacije Python-a:** u korenu repoa `start.bat` (Windows) i `start.sh` (Linux/Mac),
   preko [uv](https://docs.astral.sh/uv/).
   - uv je jedan izvršni fajl, bez admin prava; sam skine odgovarajući Python i zavisnosti iz
     `simulator/pyproject.toml` (sa zaključanim verzijama).
   - Skripta, ako uv ne postoji, ponudi da ga skine u `.tools/` u repou (gitignore).
   - Pokretanje: `git clone` jednom, posle toga dvoklik na `start`.
   - Verzija aplikacije = commit, pa ne mora da se čeka release.
2. **Exe kao do sada**, za laptop bez repoa (demo, pregled snimka). Ako se exe stavi u koren repoa (ili ga
   `start` skine iz Release-a), radi u režimu repoa.
   - Repo je privatan, pa skidanje Release-a traži prijavu; u tom slučaju exe ostaje ručni.

**Kad aplikacija nije u repou: jasno upozorenje i izbor** (dogovoreno):
- Osnovno uputstvo je jedno: **exe se stavlja u koren kloniranog repoa** (pored `ESP32/` i `simulator/`), ili
  se repo pokreće preko `start`.
- Ako se exe pokrene van repoa (`paths.find_repo` ne nađe `ESP32/lib/tac.py`), na vrhu aplikacije stoji
  **crvena traka koja se ne može zatvoriti**:
  > ⚠ Aplikacija nije u repou Robot-2027. Taktike i profil se NE čuvaju u timski repo i niko ih neće videti.
  > Stavi ovaj fajl u koren kloniranog repoa, ili izaberi:
  > **[Kloniraj repo…]** **[Otvori folder repoa…]** **[Nastavi bez repoa]**
- **Kloniraj repo…:**
  1. izbor foldera, pa `git clone https://github.com/plus381-robotics/Robot-2027` (prijava preko Git
     Credential Manager-a; repo je privatan);
  2. aplikacija zapamti putanju i odmah radi nad njim;
  3. ponudi da kopira sebe u koren repoa, da sledeći put radi bez pitanja.
- **Otvori folder repoa…:** izbor postojećeg klona.
  - Provera da je to zaista Robot-2027 (postoji `ESP32/lib/tac.py`, a `git remote` pokazuje na repo).
  - Putanja se pamti u maloj konfiguraciji korisnika (npr. `~/.eurosim.json`). Pri sledećem pokretanju
    aplikacija sama ide tamo; traka nestaje.
- **Nastavi bez repoa:** traka ostaje (žuta) i na svakom Save piše gde je fajl sačuvan.
  - **Odlučeno:** čuva se lokalno u `~/Eurosim/` kao sada, uz upozorenje "samo na ovom računaru";
    kasnije "Premesti u repo" kopira taktike u repo.
- Isto upozorenje na početnoj strani i u naslovu prozora ("Eurosim (BEZ REPOA)"), da se ne previdi.
- Test: pokretanje iz praznog foldera → traka; "Otvori folder repoa" sa privremenim klonom → traka nestaje,
  taktike se čitaju iz klona; ponovno pokretanje pamti izbor.

**Git u aplikaciji** (panel "Repo"):
- grana, koliko commit-a ispred/iza, izmenjeni fajlovi (taktike, profili);
- dugmad **Povuci najnovije** (`git pull --ff-only`) i **Sačuvaj na GitHub** (`git add` taktike/profile,
  commit sa porukom, `git push`);
- upozorenje "profil robota je promenjen na GitHub-u" posle `git fetch`;
- konflikt: aplikacija ne pokušava da ga reši, nego pokaže fajl i uputi na GitHub Desktop;
- radi preko `git` komande; potreban je Git (GitHub Desktop ili Git for Windows), prijava preko Git
  Credential Manager-a.

**Pravila za tim** (predlog):
- taktike: svako u svom fajlu, direktno na main ili preko PR;
- `simulator/profiles/*`: menja mehanika, preko PR sa pregledom;
- `ESP32/lib`, `protocol/`: samo preko PR.

**Provera:**
- čist Windows nalog: `git clone` + `start.bat` → aplikacija radi bez instaliranog Python-a;
- izmena profila na drugom računaru → "Povuci najnovije" → nov profil u simulaciji.

**Otvoreno:** da li svi članovi tima imaju GitHub nalog sa pristupom org-u (repo je privatan).

---

## S11. Ime "Gambit Micro"

**Odlučeno:** API taktika se zove **Gambit Micro**. Funkcije i njihova imena ostaju kakve jesu (`goto`,
`turn_to`, `move`...); ništa se ne preuzima iz repoa Gambit (`plus381-robotics/Gambit`, za sada samo
specifikacija za ROS 2).

- Simulator: "Gambit Micro" umesto "tac API" (naslov panela, pomoć, šablon taktike).
- ESP strana (kasnije, uz odobrenje): modul može da dobije ime `gambit` (`from gambit import *`), a `tac`
  ostaje kao omotač da stare taktike rade. Nije neophodno: ime u UI-ju je ono što je traženo.

---

## S12. Prilaz elementima: IR vidi kamenolom i robot stane (novo, nađeno pri pisanju taktike)

**Nađeno:** taktika koja prilazi kamenolomu na ~40 mm dobija **BLOCKED** na svakom prilazu (simulator,
profil: IR domet 250 mm, `see_elements = true`, visok senzor na 320 mm, a kamenolom je visok 330 mm). Robot
zato ne može bliže od ~270 mm. Kamenolomi 2 i 6 (x 1250) se ne mogu prići ni tada, jer IR na prilazu vidi
srednji kamenolom (x 1445).

**Zašto je bitno:** u meču robot mora da priđe elementima. Ako pravi robot ima iste visine senzora, ponašaće
se isto.

**Opcije:**
1. **Mehanika:** visoki senzori iznad 330 mm (vide protivnika, ne vide kamenolome). Najčistije, ako
   konstrukcija dozvoli. Simulator to može da proveri odmah (profil `[ir] high_z`).
2. **Protokol v5, zastavica u GOTO/MOVE:** `IGNORE_LOW` / `NEAR` = za ovu komandu ignoriši niske senzore
   (ili sve senzore poslednjih N mm).
   - API: `goto(x, y, prilaz=True)` ili `approach(x, y)`.
   - STM: `comm_port.c` (deo protokola) prosleđuje zastavicu regulaciji (`goal.obstacle`).
3. **Samo spori prilaz:** IR ostaje, ali se prag dometa smanji u prilazu.

**Preporuka:** prvo proveriti u simulatoru (1) sa stvarnim visinama sa crteža; ako ne može, (2) sa
zastavicom koja ignoriše samo **niske** senzore, da protivnik i dalje zaustavlja robota.

Izmena protokola, STM-a i ESP-a: odobrenje.

---

## S13. Primer taktike

Nacrti su u dodatku A, provereni u simulatoru (u privremenom folderu, nisu u repou):
- **`sve_komande.py`:** svaka komanda API-ja bar jednom, sa komentarom šta radi. Žuta i plava: OK
  (14 koraka, 14 s).
- **`kamenolomi.py`:** od kamenoloma do kamenoloma na našoj polovini, pa kući. Žuta i plava: OK
  (kamenolomi 1, 9, 5).
  - Prilaz je ~270 mm od kamenoloma zbog S12; kamenolomi 2 i 6 su izostavljeni dok se S12 ne reši.
  - "Bunt" je shvaćen kao kamenolom (gomila od 3 kamena, `field.py` QUARRIES). Ako se misli na nešto
    drugo, ispraviti.

Ubacivanje u `ESP32/tactics/` je izmena u `ESP32/`: odobrenje.

---

## S14. Zašto postoje obe strane, kad je sto simetričan?

Taktika se zaista **piše samo jednom** (za žutu), a za plavu je ESP sam ogleda: x → 3000 − x,
ugao → 180° − ugao, i levi i desni aktuator se zamene (`config.ACTUATOR_MIRROR`). Strana se ipak bira iz tri
razloga:

1. **Robot ne zna gde stoji.** Odometrija kreće od START poze. Ako ESP ne zna da je robot na plavoj, misli
   da je na x = 250 umesto na x = 2750.
2. **Ogledanje nije okretanje.** Sto je simetričan kao u ogledalu (levo ↔ desno). Okretanjem robota za 180°
   dobija se drugačije preslikavanje: x → 3000 − x **i** y → 2000 − y.
   - Tačka uz gornju ivicu tada postaje tačka uz donju.
   - Okreti levo postaju okreti desno.
   - Zato se ista taktika na drugoj strani ne može dobiti samo fizičkim postavljanjem robota; ESP mora da
     ogleda koordinate.
3. **Elementi i zone po boji:** svoje zone i elementi su na svojoj polovini; njih određuje strana.

**Šta se može pojednostaviti u simulatoru:**
- Opcija **"pogled sa moje strane"**: kad je izabrana plava, sto se prikaže okrenut, pa je naša strana
  uvek levo, kao u editoru. Koordinate u editoru su uvek žute; uz prikaz piše "plava: ESP ogleda".
- Izbor strane samo na jednom mestu, sa jasnim stanjem.
- U Live režimu promena strane premešta robota (S1).

---

## Dodatak A: nacrti taktika (provereno u simulatoru, nisu u repou)

### A1. `sve_komande.py`

```python
# Sve komande tac API-ja na jednom mestu (pregled, ne za meč). Piše se za ŽUTU stranu; na plavoj se samo ogleda.
from tac import *

START = (250, 1000, 0)        # x, y [mm], ugao [°]: odavde robot kreće (ESP je postavlja na činč)
TOTAL = 14                     # koliko koraka očekujemo (za traku napretka na ekranu)

deadline(15)                   # kad do kraja meča ostane 15 s, tekuća komanda baca TimeUp
try:
    log("strana %s, u mecu %s" % (side(), in_match()))
    pose(250, 1000, 0)                              # ručno postavi odometriju (u meču to radi START)
    step("priprema")                                # korak bez kretanja, samo natpis na ekranu
    h = actuator("lift", 100, wait=False)           # aktuator radi dok robot vozi
    goto(600, 1000, speed=400)                      # vozi do tačke (x, y)
    wait_done(h)                                    # sačekaj aktuator pokrenut sa wait=False
    turn_to(90)                                     # okreni se ka 90° (apsolutno, ka +y)
    turn_by(-45)                                    # okreni se za -45° od trenutnog ugla
    rotate(0)                                       # staro ime za turn_to
    move(200)                                       # pravo 200 mm napred
    move(-200, speed=200)                           # 200 mm nazad, sporije
    goto(500, 1200, deg=180, name="tacka B", next="nazad")   # do tačke i na kraju okret na 180°
    goto(700, 1000, reverse=True)                   # do tačke vožnjom unazad
    actuator("hvataljka", 1)                        # aktuator, čeka da završi (True/False)
    h2 = actuator("ruka_l", 50, wait=False)
    wait_until(lambda: done(h2) is not None, 2, name="ruka")  # čekaj uslov, najviše 2 s
    wait(0.5)                                       # pauza
    x, y, ugao = here()                             # gde je robot (u koordinatama naše strane)
    log("here %d %d %d" % (x, y, ugao))
    log("status %s" % (status(),))                  # sirov STATUS sa STM32 (teren, cdeg)
    log("vreme %s, ostalo %s, napad %s" % (match_time(), remaining(), attack_phase()))
except TimeUp:
    log("malo vremena: kuci")
go_home()                                           # u startnu zonu (pravila: kraj u svojoj zoni)
```

### A2. `kamenolomi.py`

```python
# Od kamenoloma do kamenoloma na našoj (žutoj) polovini, pa kući. Kamenolom = 3 kamena (field.py QUARRIES).
# Prilaz: robot (165 mm dug) stane ~270 mm ispred lica kamenoloma, okrenut ka njemu. Bliže ne može: IR senzori
# (domet 250 mm) vide kamenolom kao prepreku i robot stane (BLOCKED). Vidi plan: goto(..., ignore_ir=True).
from tac import *

START = (250, 1000, 0)
TOTAL = 7

GORE_Y = 1538          # ispred kamenoloma uz gornju ivicu (y 1945, lice na 1890)
DOLE_Y = 500           # ispred kamenoloma uz donju ivicu (y 55, lice na 110); 462 je dovoljno daleko po proračunu, ali ugaoni senzor na okretu vidi kamenolom
SREDINA_X = 1093       # ispred kamenoloma u sredini (1500, 1500), okrenut 90°: lice na x 1445


def uzmi(ime):
    actuator("hvataljka", 1, label="uzmi " + ime)      # na novom robotu: hvataljka; ovde samo pokazuje mesto


deadline(12)
try:
    goto(750, GORE_Y, deg=90, name="kamenolom 1")
    uzmi("1")
    goto(SREDINA_X, 1500, deg=0, name="kamenolom 9")
    uzmi("9")
    goto(750, DOLE_Y, deg=-90, name="kamenolom 5")
    uzmi("5")
    # Kamenolomi 2 i 6 (x 1250) za sada ne mogu: na prilazu IR vidi i srednji kamenolom (x 1445) i robot stane.
except TimeUp:
    log("malo vremena")
go_home()
```

Rezultat simulacije (`python -m eurosim run <ime> --dir <folder> --side zuta|plava`): obe taktike `ishod: OK`
na obe strane, kraj u svojoj startnoj zoni.
