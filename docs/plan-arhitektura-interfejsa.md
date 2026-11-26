> Zamenjeno: vidi docs/redizajn-ui.md

# Pregled arhitekture: eurosim + web, prema `docs/plan-redizajn-interfejsa.md`

Datum: 2026-11-26. **Stanje: predlog, ništa još nije urađeno.** Svaka faza ide posle odobrenja, sa lokalnim
commit-ima; ESP izmene posebno.

**Ukratko:** temelj je dobar, jer simulacija, Live i robot već prave isti snimak. Fale tri stvari:

- **sloj „izvor“** između UI-ja i onoga što proizvodi podatke;
- **model panela** u web-u;
- **opis protokola prema laptopu.**

Predlog je prelazak u osam faza (F0–F7), tako da simulator radi posle svake.

## 1. Trenutno stanje

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

## 2. Da li protokol i server nose ono što spec traži

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

## 3. Predlog

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

### 3.1 Izvor iza jednog interfejsa (server)

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

### 3.2 Snimak v2

Jedan modul pravi snimak za sva tri izvora.

- Kad podatak ne postoji, polje je `null` ili ga nema. Nikad lažna vrednost.
- Meta nosi verziju taktike (git/sha), stranu, scenario, profil i konfiguraciju izvora. Od toga zavise
  „simuliraj isto“ i poređenje.
- Novi događaji: `decision`, `detect`, `manual`, strukturisan `step_end`.
- Učitavač čita i v1, pa stari `simulator/runs/` ostaju upotrebljivi.

### 3.3 Paneli i radni prostori (web)

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

### 3.4 Server po modulima

`session.py` (WebSocket + izvori) i `api/` za taktike, snimke, repo, profil i scenarije. Procesni radnik ostaje.

### 3.5 Protokol prema laptopu u `protocol.yaml`

- odeljak `e2h`: polja telemetrije v2, lidar paket, `detect`, `decision`;
- odeljak `h2e`: upload komande i `MAN`.

`gen.py` iz toga pravi jednu definiciju koju dele `telem.py`, `robotlink` i `tools/watch.py`. Telemetrija nosi
verziju; stari firmver se i dalje čita, kao danas STATUS v3/v4/v5. Spora polja (RAM, verzija) idu 1 Hz, da se ne
optereti petlja na ESP-u.

## 4. Šta skloniti

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

## 5. Rizici

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

## 6. Faze prelaska (simulator radi posle svake)

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
