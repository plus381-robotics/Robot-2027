# Simulator taktika (eurosim)

Pušta taktike iz `ESP32/tactics/` bez robota, sa **istim ESP kodom** koji radi na robotu
(`tac.py`, `robot.py`, `runner.py`, `match.py`, `app.py`...) i simuliranim STM32-jem.

## Jedan fajl, bez instalacije (Linux; Windows kasnije)

Na GitHub-u: **Releases** (poslednja verzija: `eurosim-…-linux` i `eurosim-…-windows.exe`). Release se pravi
sam na svaki push na `main` (`sim-v0.2.<n>`) i za svaki tag `sim-v*`; fajl sa druge grane je u
**Actions → Simulator → run → Artifacts**. To je jedan fajl (~23 MB) sa svim unutra (Python, server, interfejs, ESP kod, mpy-cross):

    chmod +x eurosim && ./eurosim          # otvara browser na http://localhost:8270

- Pokrenut **unutar repoa** (ili `EUROSIM_ROOT=/put/do/repoa`): koristi ESP kod, taktike, profile i snimke iz
  repoa, kao `python simulator/sim.py`.
- Pokrenut **bilo gde drugde**: ESP kod je iz fajla, a taktike, profili i snimci su u `~/Eurosim/`
  (prvi put se tamo kopiraju primeri). Gore levo (Eurosim) piše koji je režim.
- Isti argumenti kao `sim.py`: `./eurosim run primer --side zuta`, `./eurosim robot`, `./eurosim serve --port 8300`.
- Pravljenje lokalno: `pip install pyinstaller -r simulator/requirements.txt && pyinstaller simulator/eurosim.spec`
  (rezultat u `dist/`).

## Web interfejs

    pip install -r simulator/requirements.txt      # jednom (aiohttp)
    python simulator/sim.py serve                  # otvara http://localhost:8270

- Gore: taktika, strana, režim (meč ili test), **Simulate** (Ctrl+Enter). Simulacija ide do kraja (meč od
  100 s za par sekundi), pa se snimak pušta.
- Sto u 3D ili odozgo (**Top**): robot, pređena putanja (bela), odometrija (narandžasto; robot-duh kad se
  razlikuje od stvarne poze), početak svakog koraka (broj, boja po ishodu), ciljevi GOTO komandi,
  protivnik. Miš: okretanje / pomeranje / zum; pozicija miša u koordinatama terena i taktike;
  **dupli klik kopira koordinate** za taktiku.
- Desno: stanje u trenutku (poza, odometrija i greška, v/ω i reference, točkovi, faza regulacije na
  STM32, IR, aktuatori, vreme meča), trenutni korak sa trakom do timeout-a, lista koraka i dnevnik
  (i poruke ESP<->STM32). Klik na korak ili red dnevnika skače na taj trenutak.
- Dole: pusti/pauza (razmak), brzina ×0.25..×25, frame napred/nazad (←/→), korak napred/nazad
  (Shift+←/→), klizač sa oznakama koraka, grafici brzine, okretanja i točkova (klik = skok).
- **Save run** čuva snimak u `simulator/runs/` (ide u git), **Saved runs** ga učitava.

### Editor taktika (✎ Editor)

Otvara taktiku iz `ESP32/tactics/` (ista kao u izboru gore) pored stola.
- Isticanje sintakse, **dopuna** (Ctrl+Space) i **opis na prelaz mišem** za ceo `tac` API, plus imena
  aktuatora u `actuator("...")` i argumenti funkcije u kojoj si (`speed=`, `next=`...). Pomoć se pravi iz
  samog `ESP32/lib/tac.py` (potpisi i docstring-ovi), pa uvek odgovara kodu na robotu; kartica **tac API**
  ima ceo spisak sa pretragom.
- **Provera dok kucaš** (Problems, i oznake u kodu): sintaksa; MicroPython kompajler (`mpy-cross`, ista
  verzija kao firmver); nepoznata imena; pogrešni ili nedostajući argumenti tac funkcija; nepoznat
  aktuator; tačke van stola i brzina iznad ~1200 mm/s; `while True` bez ijednog tac poziva (ESP bi se
  zaglavio, STM32 staje posle 500 ms bez PING-a); START koji ESP ne može da pročita bez izvršavanja.
- **▶ Run** (Ctrl+Enter) proverava i simulira **tekst iz editora, sačuvan ili ne** (fajl se ne dira).
  Posle simulacije Problems pokazuje i greške iz izvršavanja sa linijom (izuzetak u taktici, korak koji
  nije uspeo, TOTAL koji se ne slaže, START van startne zone). Live takođe koristi tekst iz editora.
- Tokom reprodukcije **linija koja se izvršava je istaknuta**, neuspeli koraci crveno; klik na korak
  skače i na njegovu liniju.
- **Save** (Ctrl+S) upisuje `ESP32/tactics/<ime>.py`; ako je fajl u međuvremenu promenjen na disku (git,
  drugi editor), pita pre nego što prepiše. **New** pravi taktiku iz šablona. Nesačuvane izmene se čuvaju u
  browseru i vraćaju posle osvežavanja stranice.

### Live režim (● Live)

Interaktivna simulacija u stvarnom vremenu (×0.25..×5, pauza): "robot je upaljen", ESP se poveže sa
STM32 i čeka, kao na stolu.
- **ESP panel** (dole desno): pravi ekran robota (`ui.py`/`pages.py` crtaju u simulirani SSD1306) i tasteri
  enkoder ⟲ ● ⟳, BACK, OK, STOP. Tasteri idu kroz pravi `inputs.py` (lažni pinovi: debounce, dugi pritisak,
  kvadraturni enkoder), pa se meni, izbor taktike i strane, naoružavanje i "drži OK" ponašaju kao na
  robotu. Točkić miša na ekranu = enkoder.
- **Arm match** (izabrana taktika i strana), **Pull cord** (činč: meč kreće, 100 s), **Run test**, **STOP**.
- **Follow**: prikaz prati robota; isključi ga (ili klikni na klizač/korak) da se vratiš unazad dok
  simulacija radi dalje.
- **End**: kraj; sesija ostaje kao snimak (reprodukcija, Save run).

### Robot (🤖 Robot): pravi robot uživo

Veza preko postojećeg ESP upload servera (TCP 8267) i telemetrije (UDP 8268), kao `tools/tactic.py` i
`tools/watch.py`; laptop mora biti na mreži robota. Host je `eurokik.local` ili IP sa ekrana VEZA, lozinka
iz `ESP32/webrepl_cfg.py` (ili upiši).
- **Push** šalje taktiku (tekst iz editora ako je otvoren, inače fajl), **Push & Run** je i pokreće odmah
  (test, bez meča; pita pre pokretanja jer robot kreće), **■ STOP** (i taster Esc).
- Telemetrija (10 Hz) crta robota, korake (ishod iz dnevnika), dnevnik, brzinu i stanje meča, isto kao
  simulacija; **Follow** / klizač za vraćanje. **Disconnect**: sesija ostaje kao snimak (Save run).
- Robot šalje odometriju (ne zna stvarnu pozu) i ne šalje ekran; koraci kraći od 100 ms mogu da promaknu.
- **Virtual robot**: na ovom računaru pokrene virtuelnog robota (pravi ESP kod sa upload serverom i
  telemetrijom nad simuliranim STM32) i poveže se na njega. Isto iz terminala: `python simulator/sim.py robot`,
  pa `python tools/tactic.py primer --host 127.0.0.1 --password eurosim` i `python tools/watch.py --host 127.0.0.1`.

### Poređenje (📌 Pin as reference / compare with…)

Trenutni snimak postaje referenca (ili izaberi sačuvan), pa pokreni drugi (simulacija, Live ili robot):
referentna putanja i robot-duh (ljubičasto) se crtaju preko, poravnato po početku taktike. Npr. simulacija
kao referenca, pa ista taktika na robotu.

### Profil robota (⚙ Robot profile)

Sve vrednosti iz `profiles/*.toml` (dimenzije, pogon, odometrija, regulacija, IR, aktuatori) sa komentarima;
**(P)** = pretpostavka. Save upisuje u fajl (komentari ostaju) i sledeća simulacija ga koristi.

### Sto

Izgled stola je slika iz pravila 2027 (dodatak G.1, slika 8; `web/table2027.jpg`, x nadesno, y nagore);
"rules table" prebacuje na običnu mrežu.

### Protivnik

**+ Opponent** dodaje protivnika (300 x 300 mm, visina 350); prevlači se mišem po stolu, a dimenzije,
ugao, visina i oblik (pravougaonik ili krug) menjaju se u panelu dole levo. IR senzori ga vide (zavisno
od visine), sudar zaustavlja robota. U brzom režimu simulacija se sama ponovi kad pustiš protivnika (ostaje
isti trenutak); u Live režimu protivnik se pomera dok robot vozi. Protivnici se pamte u browseru.

## Komandna linija

    python simulator/sim.py run primer                     # meč na plavoj (naoružan -> činč -> 100 s)
    python simulator/sim.py run primer --side zuta --test  # odmah, kao tools/tactic.py
    python simulator/sim.py run primer --opp 800,1000      # protivnik 300x300 mm na (800, 1000)
    python simulator/sim.py run primer -v                  # i sve poruke ESP <-> STM32
    python simulator/sim.py run primer --out run.json.gz   # sačuvaj snimak

Komandna linija treba samo Python 3.11+. Testovi: `python -m pytest simulator/tests`
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
- UI testovi: `node simulator/tests/ui_smoke.js`, `ui_f2.js`, `ui_f3.js` dok radi `sim.py serve`
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
kad se menja verzija: `cd simulator/web/vendor/codemirror-src && npm ci && npm run build`.
