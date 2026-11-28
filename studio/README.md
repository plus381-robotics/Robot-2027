# Gambit Studio (simulator taktika, paket eurosim)

Pušta taktike iz `ESP32/tactics/` bez robota, sa **istim ESP kodom** koji radi na robotu
(`tac.py`, `robot.py`, `runner.py`, `match.py`, `app.py`...) i simuliranim STM32-jem.

## Za tim: repo je radni prostor

Taktike (`ESP32/tactics/`) i profil robota (`studio/profiles/`) žive u repou, pa ih svi dele, a git čuva
istoriju. Aplikacija se zato pokreće **iz kloniranog repoa**:

1. Jednom: `git clone https://github.com/plus381-robotics/Robot-2027` (ili GitHub Desktop → Clone).
2. Pokretanje bez instaliranja Python-a: dvoklik na **`start.bat`** (Windows) ili `./start.sh` (Linux/Mac) u
   korenu repoa. Prvi put [uv](https://docs.astral.sh/uv/) skine Python i biblioteke (~1 min, pita pre
   skidanja uv-a); posle radi i bez interneta. Uvek je to verzija iz repoa: posle pull-a samo ponovo pokreni.
3. U aplikaciji stavka **Repo** u bočnoj traci (levo dole; značka ↓ novo / ! profil / ● izmenjeno): šta je novo na
   GitHub-u (i da li je promenjen profil robota), **Preuzmi najnovije**, i **Sačuvaj na GitHub** (commit + push
   samo taktika i profila, sa porukom šta je promenjeno). Treba Git
   (GitHub Desktop ili Git for Windows) i nalog sa pristupom repou.

Ako se aplikacija pokrene **van repoa**, na vrhu stoji crvena traka: taktike i profil se NE čuvaju u timski
repo (i stavke Repo u bočnoj traci nema). Dugmad: **Kloniraj repo…** (klonira u izabrani folder), **Otvori folder
repoa…** (postojeći klon; putanja se pamti u `~/.eurosim.json`, pa sledeći put radi bez pitanja) ili
**Nastavi bez repoa** (žuta traka: čuva se samo na tom računaru u `~/Eurosim/`).

Predlog pravila: taktike svako u svom fajlu; profil robota menja mehanika (najbolje preko PR-a); `ESP32/lib`
i `protocol/` samo preko PR-a.

Exe i GitHub Release se više ne prave: iz repoa je uvek najnovija verzija.

## Web interfejs

    pip install -r studio/requirements.txt      # jednom (aiohttp)
    python studio/sim.py serve                  # otvara http://localhost:8270

- Levo bočna traka: prostori **Taktike**, **Senzori**, **Vožnja** (SIM / ROBOT), **Snimci** (Alt+1 … 4), a dole
  Izvori, Repo, Profil i **Pomoć** (spisak prečica, i taster „?“). Gore statusna traka sa ■ STOP (i Esc).
- Ispod nje red komandi prostora; na njegovom desnom kraju je **poruka** (šta se upravo desilo; greška crveno, cela u
  oblačiću), u svakom prostoru, ponekad sa dugmetom (npr. „Otvori u Snimcima“ posle kraja sesije).
- Taktike: taktika, strana, režim (meč ili test), **▶ Pokreni** (Ctrl+Enter). Simulacija ide do kraja (meč od
  100 s za par sekundi), pa se snimak pušta.
- Sto u 3D ili **Odozgo**: robot, pređena putanja (bela), odometrija (narandžasto; robot-duh kad se
  razlikuje od stvarne poze), početak svakog koraka (broj, boja po ishodu), ciljevi GOTO komandi,
  protivnik. Miš: okretanje / pomeranje / zum; pozicija miša u koordinatama terena i taktike;
  **dupli klik kopira koordinate** za taktiku, **Alt+klik** ubacuje `goto(x, y)` u editor (Taktike).
  **Prikaz ▾**: „Šta crtam“ (odometrija, tačke i nazivi koraka, IR zraci, lidar, nacrt iz editora, legenda) i
  „Kako izgleda“ (crtež stola po pravilima, veličina oznaka, Kamera prati robota).
- Desno: stanje u trenutku (poza, odometrija i greška, v/ω i reference, točkovi, faza regulacije na
  STM32, IR, aktuatori, vreme meča), trenutni korak sa trakom do timeout-a, lista koraka i dnevnik
  (i poruke ESP<->STM32). Klik na korak ili red dnevnika skače na taj trenutak.
- Dole: pusti/pauza (razmak), brzina ×0.25..×25, frame napred/nazad (←/→), korak napred/nazad
  (Shift+←/→), klizač sa oznakama koraka, grafici brzine, okretanja, točkova i ugla (klik = skok; kartica Grafici je
  sklopljena, u Snimcima se sama otvori dok porediš sa referencom; tvoj izbor se pamti po prostoru).
- Prostor **Snimci**: **Sačuvaj snimak…** čuva snimak u `studio/runs/` (ide u git); lista sačuvanih snimaka
  (izvor S / R / H, taktika, strana, ime, datum, ishod; filter po izvoru i tekstu) ga učitava klikom.

### Editor taktika (radni prostor Taktike)

Otvara se sam kad uđeš u Taktike (ili „✎ Editor“ u redu komandi), sa taktikom iz `ESP32/tactics/` (ista kao u
izboru „Taktika“ gore) pored stola; „×“ ga zatvara i sto dobija celu širinu. U drugom prostoru je samo sakriven
(tekst i nesačuvane izmene ostaju). Red komandi Taktika: Taktika, Strana Žuta | Plava, meč | test, ▶ Pokreni.
- Isticanje sintakse, **dopuna** (Ctrl+Space) i **opis na prelaz mišem** za ceo `tac` API, plus imena
  aktuatora u `actuator("...")` i argumenti funkcije u kojoj si (`speed=`, `next=`...). Pomoć se pravi iz
  samog `ESP32/lib/tac.py` (potpisi i docstring-ovi), pa uvek odgovara kodu na robotu; kartica **Komande**
  (ispod koda, pored Problemi) ima ceo spisak sa pretragom i primerima („Ubaci u kod“).
- **Provera dok kucaš** (Problemi, i oznake u kodu): sintaksa; MicroPython kompajler (`mpy-cross`, ista
  verzija kao firmver); nepoznata imena; pogrešni ili nedostajući argumenti tac funkcija; nepoznat
  aktuator; tačke van stola i brzina iznad ~1200 mm/s; `while True` bez ijednog tac poziva (ESP bi se
  zaglavio, STM32 staje posle 500 ms bez PING-a); START koji ESP ne može da pročita bez izvršavanja.
- **▶ Pokreni** (Ctrl+Enter) proverava i simulira **tekst iz editora, sačuvan ili ne** (fajl se ne dira).
  Posle simulacije Problemi pokazuje i greške iz izvršavanja sa linijom (izuzetak u taktici, korak koji
  nije uspeo, TOTAL koji se ne slaže, START van startne zone). Live takođe koristi tekst iz editora.
- Tokom reprodukcije **linija koja se izvršava je istaknuta**, neuspeli koraci crveno; klik na korak
  skače i na njegovu liniju.
- **Sačuvaj** (Ctrl+S) upisuje `ESP32/tactics/<ime>.py`; ako je fajl u međuvremenu promenjen na disku (git,
  drugi editor), pita pre nego što prepiše. **Novo** pravi taktiku iz šablona; **Fajl ▾**: sačuvaj kao, preimenuj, obriši. Nesačuvane izmene se čuvaju u
  browseru i vraćaju posle osvežavanja stranice.

### Vožnja SIM: simulacija uživo

Prostor **Vožnja**, ispod njega u bočnoj traci **SIM**, pa **▶ Pokreni sesiju**: interaktivna simulacija u
stvarnom vremenu (brzina ×0.25..×5, Pauza): "robot je upaljen", ESP se poveže sa STM32 i čeka, kao na stolu.
Red komandi pokazuje samo ono što sesija ume (poruka `hello`, `capabilities`). Dok editor u Taktikama ima
nesačuvan tekst, sesija koristi taj tekst (napomena „koristi se tekst iz editora (nesačuvan)“).
- **ESP** (bočna kartica): pravi ekran robota (`ui.py`/`pages.py` crtaju u simulirani SSD1306) i tasteri
  enkoder ⟲ ● ⟳, BACK, OK, STOP. Tasteri idu kroz pravi `inputs.py` (lažni pinovi: debounce, dugi pritisak,
  kvadraturni enkoder), pa se meni, izbor taktike i strane, naoružavanje i "drži OK" ponašaju kao na
  robotu. Točkić miša na ekranu = enkoder.
  - **Buzzer**: zvuci i RTTTL melodije sa robota (`ESP32/lib/buzzer.py`, `config.SOUNDS`) se čuju u browseru
    (posle prvog klika na panel), iste note kao na robotu; trepće ♪ pored naslova, u dnevniku `[buzzer] greska`...
    Editor proverava `play("...")` istim parserom kao robot (`ESP32/lib/rtttl.py`).
  - **Lidar**: Meni → Lidar test radi sa lažnim RPLIDAR-om (`ESP32/sim/fakelidar.py`, isti bajtovi kao pravi)
    koji vidi ivice stola, kamenolome i protivnike sa stola (profil `[lidar]`: položaj, visina ravni).
    Dok lidar radi, poslednji krug (ono što je ESP izmerio) se crta na stolu kao plave tačke na visini
    lidara, najbliža tačka žutim prstenom (prekidač „lidar“ u Prikaz ▾ → Šta crtam); snima se i u snimak (događaj
    `lidar`, ~10 puta u sekundi), pa se vidi i pri puštanju. Tačke pored prepreka = pogrešan `LIDAR_MOUNT_DEG`.
- **Naoruži** (izabrana taktika i strana), **Povuci činč** (meč kreće, 100 s), **Test** (taktika odmah, bez meča).
- **■ STOP** je na statusnoj traci gore desno (i taster Esc), iz svakog prostora.
- **Prati**: vreme prati sesiju; isključi ga (ili klikni na klizač/korak) da se vratiš unazad dok
  simulacija radi dalje.
- **Završi**: kraj; sesija ostaje kao snimak (reprodukcija; **Otvori u Snimcima** uz poruku: sačuvaj, uporedi).
- Dok sesija radi, SIM/ROBOT se ne menja („Sesija radi: prvo je završi“).

### Hibridna simulacija: pravi lidar sa robota, ostalo simulirano

Odakle dolaze krugovi lidara bira se u bloku **Izvori** (stavka Izvori u bočnoj traci, ili **Izvori ▾** levo od
**▶ Pokreni sesiju** u Vožnji). Blok ima unapred zadate kombinacije **a** (sve sim), **b** (hibrid: lidar pravi ili
iz snimka), **d** (sve pravo = Vožnja ROBOT) i red po delu robota (pogon, lidar, IR, mehanizmi, protivnici: sim /
pravi / snimak / lažiran). Ono što još ne radi je sivo, sa razlogom (c i „lažiran“ dolaze sa Fazom 6; pravi pogon
traži pravi lidar i IR). Izbor se pamti (`eurosim.sources`), a dok sesija radi blok se samo čita i pokazuje šta
sesija stvarno koristi. Lidar u hibridu:
- **sim**: lažni lidar vidi sto iz simulacije (podrazumevano, a).
- **pravi**: pravi lidar na robotu. Simulator pošalje robotu `LIDAR ON` (host i lozinka iz istog bloka Izvori, deo
  „Veza sa robotom“), prima krugove iz telemetrije i daje ih simuliranom ESP-u kroz lažni RPLIDAR, pa ih ESP kod
  čita istim drajverom kao na robotu. Pogon, odometrija, IR i protivnici ostaju simulirani. Brzina je ×1 i
  nema pauze (pravi uređaj). Svaki krug se snima u `studio/lidar/<vreme>.jsonl.gz`; na kraju `LIDAR OFF`.
  Traka pokazuje **HIBRID**.
- **snimak** (izbor snimka pored): ponavlja snimljene krugove (u krug), bez robota; radi na svakoj brzini.
- Iz terminala: `python studio/sim.py run <taktika> --lidar file:<snimak>`.

Tačke pokazuju okolinu **pravog** robota, nacrtanu oko **virtuelnog**: poklapaju se sa stolom samo kad pravi
robot stoji na stolu na istom mestu. Za proveru drajvera i prepoznavanja protivnika (kutija ispred robota)
robot može da stoji bilo gde.

### Vožnja ROBOT: pravi robot uživo

Prostor **Vožnja**, u bočnoj traci **ROBOT** (ili Izvori → **d**), pa **▶ Pokreni sesiju** otvara blok Izvori sa
vezom sa robotom (host, lozinka, **Poveži**, **Virtuelni robot**; ✕ ili Esc zatvara). Veza preko postojećeg ESP upload servera (TCP 8267) i telemetrije (UDP 8268), kao `tools/tactic.py` i
`tools/watch.py`; laptop mora biti na mreži robota. Host je `eurokik.local` ili IP sa ekrana VEZA, lozinka
iz `ESP32/webrepl_cfg.py` (ili upiši).
- **Pošalji** šalje taktiku (tekst iz editora ako je otvoren, inače fajl), **Pošalji i pokreni** je i pokreće
  odmah (test, bez meča; pita pre pokretanja jer robot kreće), **■ STOP** na statusnoj traci (i taster Esc).
- Telemetrija (10 Hz) crta robota, korake (ishod iz dnevnika), dnevnik, brzinu i stanje meča, isto kao
  simulacija; stanje veze je na statusnoj traci (Veza); **Prati** / klizač za vraćanje. **Prekini vezu**: sesija
  ostaje kao snimak (**Otvori u Snimcima**: sačuvaj, uporedi).
- Robot šalje odometriju (ne zna stvarnu pozu) i ne šalje ekran; koraci kraći od 100 ms mogu da promaknu.
- **Lidar robota**: dok lidar na robotu radi, krugovi se crtaju na stolu (plave tačke) oko poze iz telemetrije.
- **Virtuelni robot**: na ovom računaru pokrene virtuelnog robota (pravi ESP kod sa upload serverom i
  telemetrijom nad simuliranim STM32) i poveže se na njega. Isto iz terminala: `python studio/sim.py robot`,
  pa `python tools/tactic.py primer --host 127.0.0.1 --password eurosim` i `python tools/watch.py --host 127.0.0.1`.

### Senzori

Prostor **Senzori** (bočna traka ili Alt+2) pokazuje 10 blokova: lidar odozgo, skica robota sa IR, brzine, regulacija
(zadato/stvarno), napajanje, aktuatori, enkoderi, činč i tasteri, meč i taktika, veza i zdravlje. Svaki ima oznaku
izvora **PRAVO** (sa robota), **SIM** ili **SNIMAK**, ili „nepovezano“ sa razlogom (npr. „Nucleo ga ne šalje“).
Klik na blok otvara detalj (vrednosti, šta fali, kako proveriti); „← Svi senzori“ vraća na pregled.
- Zaglavlje kaže šta se prikazuje: pravi robot, virtuelni robot, simulacija, hibrid, snimak ili „Ništa nije povezano“.
  Bez veze tu je i dugme **Poveži robota**.
- **Poveži robota** je i na statusnoj traci (host, lozinka, **Poveži**, **Virtuelni robot**). Pravi robot danas šalje
  poziciju, brzinu v, stanje meča i krugove lidara (posle **Upali lidar**); IR, ω, aktuatori, činč, napajanje, PID i
  enkoderi stižu kad ESP i Nucleo počnu da ih šalju.
- **Snimak**: učitan snimak se ne prikazuje; čim ga pustiš (▶), blokovi pokazuju šta su senzori javljali u tom
  trenutku (SNIMAK, zaglavlje „snimak <ime> · <vreme> s“). Pauza ostaje na snimku. Dugme **Uživo** (ili kraj snimka,
  drugi snimak, nova sesija) vraća na uživo. Grafici pokazuju poslednjih 15 s pre kursora.
- Klik na **Odozgo · lidar** otvara postojeće panele lidara (isto kao ranije Test dela → Lidar):

#### Lidar

Jedan krug lidara korak po korak: sirove tačke → u stolu / van stola (sudija pored stola nije protivnik; odbačene tačke sivo i prazno) → grupe
(krstić, udaljenost od centra robota; najbliža crveno). Međukorake računa **laptop** (`eurosim/lidarview.py`, POST
`/api/lidar/stages`), jer ESP danas ima samo binove i najbližu tačku; kartica Lidar to i piše („izračunao laptop“) i
odvojeno pokazuje ESP-ovu najbližu tačku.
- **Sto** (koordinate stola, po pozi robota) i **radar** oko robota (napred gore; domet 1 / 2 / 4 m). Bez poze
  (STM32 nije povezan, snimak bez poze) piše „nema poze“ i radi samo radar.
- Kartica **Lidar**: slojevi (sirovo / van stola / grupe), Hz, broj tačaka (u stolu / van), starost kruga, poza,
  najbliža grupa (laptop), najbliža tačka (ESP), spisak grupa.
- Izvor **Sesija**: krugovi sesije koja radi. SIM: na ESP-u Meni → Lidar test (ili hibrid iz Izvora). ROBOT:
  **Upali lidar** / **Ugasi lidar** (postojeća komanda `LIDAR ON` / `LIDAR OFF` upload servera; ESP je odbija dok
  taktika radi, dok je robot naoružan ili dok meč traje, pa je dugme tada sivo sa razlogom; lidar sam gasi i kad niko ne
  gleda telemetriju; natpis prati stanje lidara iz telemetrije) i **● Snimi krugove** (u
  `studio/lidar/<vreme>.jsonl.gz`, isti format kao snimak hibrida, uz pozu iz telemetrije).
- Izvor **Snimak**: snimak iz `studio/lidar/` pušta se svojim tempom (▶/⏸, u krug).

### Poređenje (Snimci: 📌 Referenca / Uporedi sa…)

U redu komandi prostora Snimci: **📌 Referenca** (snimak koji gledaš) ili **Uporedi sa…** (sačuvan snimak; u listi
dobija 📌), pa pokreni ili učitaj drugi (simulacija, Live ili robot); ✕ uklanja referencu. Referentna
putanja i robot-duh (ljubičasto) se crtaju preko, poravnato po početku taktike. Npr. simulacija
kao referenca, pa ista taktika na robotu.

### Profil robota (stavka Profil u bočnoj traci)

Sve vrednosti iz `profiles/*.toml` (dimenzije, pogon, odometrija, regulacija, IR, aktuatori) sa komentarima;
**(P)** = pretpostavka. **Sačuvaj i koristi** upisuje u fajl (komentari ostaju) i sledeća simulacija ga koristi.

### Sto i elementi igre 2027

Izgled stola je slika iz pravila 2027 (dodatak G.1, slika 8; `web/table2027.jpg`, x nadesno, y nagore);
„crtež stola po pravilima“ (Prikaz ▾ → Kako izgleda) prebacuje na običnu mrežu. Taktike se pišu za **žutu** stranu (`tac.REF_SIDE`, startna zona
x 0..500), na plavoj se ogledaju.

**Elementi igre** (`eurosim/field.py`, položaji izmereni sa slike 8, 1 px = 1 mm): 10 kamenoloma po 3 kamena
(320 x 110 x 110 mm, 330 mm visoko). IR senzori su iznad njih (340 mm), pa ih ne vide; robot koji naleti
na kamenolom ga **gura** (sporije, `[elements] push_resist`), osim kad iza nema mesta (ivica, druga prepreka):
tada se zaglavi (BLOCKED). Zone bedema (kule, zidovi), kapije i štale su u `field.ZONES`. Prekidač
„elementi igre“ u kartici Postavka stola (ili `--no-elements`) ih isključuje.

**Menjanje stola** (bočna kartica **Postavka stola**, u Taktikama i u Vožnji SIM): klik na kamenolom -> uređivač
u kartici (− / + kamen, okreni 90°, ukloni), prevlačenje mišem, **Resetuj sto** = po pravilima, „elementi igre“
uključuje/isključuje kamenolome. **Sačuvaj scenario / učitaj scenario…** čuva kamenolome i protivnike u
`studio/scenarios/<ime>.json` (deli se kroz git). U snimku se vidi kako je kamenolom gurnut.

**IR senzori** (`[ir]` u profilu): u svakom od 4 ugla po dva, donji D (`low_z`, 40 mm, vidi kamenolome) i gornji U
(`high_z`, 340 mm, iznad kutija, vidi protivnika). Imena: F/B napred/nazad, L/R levo/desno, D/U: FLD FLU FRD FRU BLD
BLU BRD BRU. Taktika ih gasi i pali po imenu ili grupi slova: `ir_off("FD")` (donji prednji), `ir_on()`,
`ir_sees("FU")` (protokol v5). U panelu STATE: u svakom uglu dugme za gornji i donji; isključeni su isprekidani, crveni vide nešto.

### 3D model robota (CAD)

Profil `[model] file` pokazuje GLB koji se crta umesto kutije; ostatak robota je providna kutija iz `[body]`.
Sada: pogonska ploča iz Fusion-a (`web/models/pogon2027.glb`). Iz STEP-a:

    pip install cascadio trimesh
    python studio/tools/cad_to_glb.py robot.step --out studio/web/models/robot.glb --front +y

`--front` = CAD osa koja gleda napred (pretpostavka za ploču: +y; ako je robot okrenut obrnuto, `-y`).

### Protivnik

**+ Protivnik** (Postavka stola) dodaje protivnika (300 x 300 mm, visina 350); prevlači se mišem po stolu, a dimenzije,
ugao, visina i oblik (pravougaonik ili krug) menjaju se u panelu dole levo. IR senzori ga vide (zavisno
od visine), sudar zaustavlja robota. U brzom režimu simulacija se sama ponovi kad pustiš protivnika (ostaje
isti trenutak); u Live režimu protivnik se pomera dok robot vozi. Protivnici se pamte u browseru.

**Taktika protivnika:** u panelu protivnika `tactic` (fajlovi u `studio/opponents/`, vidi tamošnji README):
`patrola`, `ka_kamenolomu` (blokira naš srednji kamenolom), `nasumicno` (seme u panelu), `pami_napred`.
Piše se kao naša taktika, za žutu stranu; simulator je ogleda na protivnikovu stranu i kreće od činča.
Protivnik stoji kad bi udario u naš robot, a kamenolome gura. **+ PAMI** dodaje mali robot (150 x 120, 130 mm)
na protivnikovoj strani koji kreće u poslednjih 15 s meča (IR na 340 mm ga ne vidi, sudar ga vidi).

## Komandna linija

    python studio/sim.py run primer                     # meč na plavoj (naoružan -> činč -> 100 s)
    python studio/sim.py run primer --side zuta --test  # odmah, kao tools/tactic.py
    python studio/sim.py run primer --opp 800,1000      # protivnik 300x300 mm na (800, 1000)
    python studio/sim.py run primer -v                  # i sve poruke ESP <-> STM32
    python studio/sim.py run primer --out run.json.gz   # sačuvaj snimak

Komandna linija treba samo Python 3.11+. Testovi: `python -m pytest studio/tests`
(posebno od `ESP32/tests/host`, jer oba imaju svoj `conftest.py`).

## Kako radi

```
taktika.py -> tac.py -> runner/match/app -> robot.py ==UART bajtovi (COBS+CRC)==> SimSTM
             (pravi ESP kod iz ESP32/lib, nepromenjen)                            ├ comm.c      (eurosim/stm.py)
                                                                                  ├ comm_port.c (eurosim/stm.py)
                                                                                  ├ control.c   (eurosim/control.py)
                                                                                  └ model robota (eurosim/plant.py)
```

- **Granica je UART.** `robot.py` ne zna da li priča sa pravim ili simuliranim STM32. ESP kod se ne kopira
  i ne menja; simulator ga uvozi iz `ESP32/` kao `ESP32/tests/host`.
- **Virtuelno vreme.** Sat iz `compat.py` (`compat.fake`); STM32 deo se pomera u koracima od 1 ms (kao
  1 kHz petlja na STM32). Simulacija je brža od stvarnog vremena (meč od 100 s za par sekundi) i uvek
  daje isti rezultat za istu taktiku.
- **SimSTM** prati `comm.c` i `comm_port.c`: duplikat samo po poslednjem seq, PREEMPTED, STOP, pad veze
  posle 500 ms, STATUS na 50 ms, SET_POSE samo kad robot stoji, GOTO = vožnja pa okret na theta,
  ROTATE timeout 5 s, meč 100 s, statusi regulacije -1/-3/-4/-5 -> DONE/BLOCKED/TIMEOUT.
  Aktuatori (AX, pumpe): ACK pa DONE posle zadatog vremena, nikad FAIL.
- **Regulacija** (`control.py`) je Python prepis BlackPill `control.c` + `signal.c` (iste faze, isti
  profil brzine, tolerancije, "stacked"), parametri u profilu. Kad se regulacija na novom robotu promeni,
  menja se ovaj fajl i profil.
- **Model robota** (`plant.py`): diferencijalni pogon (razmak točkova iz profila), kašnjenje i ograničeno
  ubrzanje točkova, odometrija sa pasivnih točkova (sa opcionom greškom: tada se stvarna poza i ono što
  STM32 misli razilaze), sudar sa ivicom ili preprekom (robot stoji -> BLOCKED), IR senzori (4 napred,
  4 nazad) vide prepreku -> robot staje -> BLOCKED.
- **Snimak** (`record.py`): stanje na 20 ms (stvarna poza, odometrija, brzine, reference, stanje taktike
  i meča), poruke ESP <-> STM32, dnevnik, koraci. Iz njega crta web interfejs.
- **Server** (`server.py`, aiohttp): svaka simulacija u posebnom procesu (taktika sa beskonačnom petljom
  bez `wait()` se prekine posle 60 s). Frontend (`web/`) je običan JavaScript bez build koraka;
  three.js i uPlot su u `web/vendor/` (radi bez interneta).
- UI testovi: `node studio/tests/ui_smoke.js`, `ui_f2.js`, `ui_f3.js` dok radi `sim.py serve`
  (treba Playwright).
- **Live** (`/ws/live`, WebSocket): simulacija u posebnom procesu prima komande (tasteri, činč, STOP,
  protivnik, brzina) i šalje nove frame-ove, događaje i sliku ekrana ~20 puta u sekundi.

## Profil robota

`profiles/robot2027.toml`: dimenzije, pogon, odometrija, regulacija, IR, aktuatori. Vrednosti označene sa
**(P)** su pretpostavke (nema još merenja); kad stignu merenja ili snimak sa robota, menjaju se tu.

## Teren

`eurosim/field.py`: Eurobot 2027 (pravila, dodatak G.1): x 0..3000, y 0..2000, žuta startna zona
x 0..500, plava x 2500..3000 (y 750..1250). Elementi igre dolaze kasnije.

## CodeMirror (editor)

`web/vendor/codemirror.bundle.js` je CodeMirror 6 spakovan u jedan fajl, da tim ne treba Node. Pravi se samo
kad se menja verzija: `cd studio/web/vendor/codemirror-src && npm ci && npm run build`.
