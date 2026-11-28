# Redizajn UI: napredak izrade

Stanje 2026-11-28 (posle noći). Plan: `docs/plan-implementacija-redizajna.md`. Spec: `docs/redizajn-ui.md`.
Grana: `redizajn-ui` (lokalna). Maketa: varijanta A (`~/makete-ui/varijanta-a.html`, van repoa).

## Gde je stalo

- **Faza 0 — gotova** (0.1 jedan spec, 0.2 čišćenje, 0.3 lidar sa robota bez poze).
- **Faza 1 — gotova** (1.1 snimak v2 sa `meta.origin`, bez lažnih polja sa robota; 1.2 server po modulima `eurosim/api/`).
- **Faza 2 — gotova** (2.1 `eurosim/session.py`: `SimSource`, `RobotSource`, `ReplaySource`; 2.2 `/ws/session`
  sa porukama `hello` i `state` (`ok`/`stale`/`lost`), `/ws/live` i `/ws/robot` su alijasi, stari UI radi bez izmena).
- **Faza 3 — gotova** (3.1 `web/core/run.js` (inkrementalni snimak, `hasData`), `core/store.js`, `core/session.js`;
  3.2 okvir varijante A: statusna traka, bočna traka, registar panela `core/panels.js`, `web/shell/`; stari UI je
  montiran ispod; Esc = STOP odasvud, i iz editora; Live i Robot idu preko `/ws/session`).
- Testovi: `simulator/.venv/bin/python -m pytest -q simulator/tests` → 145 passed (polazno 119);
  `node --test simulator/tests/js/` → 25 passed.
- Ručno u browseru (1366×768): brza simulacija, Live (Naoruži, činč, Esc = STOP, End), virtuelni robot
  (Push & Run, Esc, Disconnect), robot koji se ne javlja („no telemetry“, STOP se i dalje šalje) — bez grešaka.
- **Faza 4 — gotova (preko noći, grana `redizajn-ui-2`, oznaka `posle-faza-4`)**: regioni (alati / glavni / bočne
  kartice / dole), paneli u `web/panels/`: teren, editor (samo Taktike, sa karticom Komande), vreme, grafici (+ ugao θ),
  Korak sada, Koraci, Dnevnik („samo greške“), Stanje i IR, alati Taktika (meč|test, ▶ Pokreni), alati Vožnja po
  mogućnostima sesije (Pokreni sesiju, Naoruži, Povuci činč, Test, brzina, Pauza, Pošalji, Pošalji i pokreni, Prati,
  Završi / Prekini vezu), ESP i Postavka stola kao kartice, prostor Snimci (lista sa filterom, učitavanje, referenca,
  poređenje, „Otvori u Snimcima“), poruke desno u redu alata, Prikaz ▾ u dve grupe, Alt+1..4 i „?“ prečice. Stari UI
  (#bar, kartice Simulate/Live/Robot, stari STOP-ovi, ⋯ Runs) je obrisan. Testovi: pytest 149, JS 65.
- **Faza 5 (5.1, 5.2) — gotova (preko noći, oznaka `posle-faza-5`)**: blok **Izvori** (iz bočne trake i iz Vožnje:
  a sve sim, b hibrid sa lidarom sa robota ili iz snimka, d sve pravo; nedostupno sivo sa razlogom; veza sa robotom na
  istom mestu; tokom sesije samo čitanje). **Test dela → Lidar**: sto i radar oko robota (radi i bez poze), slojevi
  u stolu / van stola / grupe, Hz, broj tačaka, starost kruga, najbliža grupa, oznaka „izračunao laptop“; izvori:
  sesija (SIM ili ROBOT) ili snimak krugova; za ROBOT „Upali lidar“ (postojeća komanda `LIDAR ON`, siva dok taktika
  radi / naoružan / meč) i „Snimi krugove“ u `simulator/lidar/`. Pogon, Mehanizmi i IR su sivi: „dolazi sa Fazom 6
  (ESP)“.
- **Završni pregled noćne grane** je našao jednu pravu grešku (klik na snimak ili „Sačuvaj snimak“ tokom sesije je
  radio nad pogrešnim snimkom) i ostatke engleskog; sve popravljeno (`1afed01`): Snimci su zaključani tokom sesije sa
  razlogom, natpisi su na srpskom, `localStorage` u try/catch.
- Testovi na kraju noći: pytest **162 passed**, JS **86 passed**. Playwright skripte su ažurirane ali nisu pokrenute.
- **Prva upotrebljiva verzija je gotova.** Kasnije: 5.3 poređenje sim/robot (tabela koraka, „Simuliraj isto“),
  5.4 automatsko snimanje sesija sa robotom, Faza 6 (ESP: telemetrija v2, ručne komande, lažirani delovi).
- Otvoreno (nije popravljeno): `core/panels.js`, `core/lidar.js`, `core/regions.js` čitaju `localStorage` van
  try/catch u podrazumevanom parametru — u browseru sa blokiranim podacima sajta stranica ne bi krenula. Mali zadatak.

## Gambit Studio i Senzori (grane gs-a … gs-d, 2026-11-28)

Plan: `docs/plan-gambit-studio-senzori.md`. Lokalne grane, jedna na drugoj; ništa nije gurnuto na GitHub.

- **gs-a-preimenovanje**: aplikacija se zove **Gambit Studio**, folder je `studio/` (bio `simulator/`). Unutrašnja imena
  ostaju (`eurosim`, `sim.py`, `~/.eurosim.json`, `~/Eurosim`, `EUROSIM_*`, localStorage `eurosim.*`). Migracija
  prenosi lokalne snimke (`simulator/runs`, `simulator/lidar`) u `studio/` i javlja to porukom.
- **gs-b-povezi-robota**: **Poveži robota** je na statusnoj traci (host, lozinka, virtuelni robot), a ne samo u Vožnji.
- **gs-c-senzori-okvir**: prostor **Senzori** zamenio je Test dela (okvir, zaglavlje „Prikazuje: …“, izvori podataka).
- **gs-d-senzori-blokovi**: 10 blokova (lidar odozgo, skica robota sa IR, brzine, regulacija, napajanje, aktuatori,
  enkoderi, činč i tasteri, meč i taktika, veza), detalj na klik, i **snimak u Senzorima** (SNIMAK, dugme Uživo).
- **Završni pregled (gs-d)**: virtuelni robot je SIM (ne PRAVO); Poveži robota se vidi i tokom SIM sesije (klik kaže
  „prvo Završi“); aktuatori bez tipa u Profilu pišu ime i sirovu vrednost (ugao samo za `[actuators.type]` servo,
  lampica za pumpu); razmak pauzira pušten snimak i u Senzorima; Veza broji pakete telemetrije robota (i bez Nucleo-a).
- **Šta robot šalje danas**: poza, brzina v, stanje meča, taktika, krugovi lidara (posle Upali lidar), stanje veze.
  **Kasnije (ESP/Nucleo)**: IR (`ir`, `irm`), ω, aktuatori (`act`), činč i tasteri, INA3221 napajanje, PID reference,
  enkoderi, RSSI, RAM i krug petlje. Blokovi za njih već postoje i pišu „nepovezano“ sa razlogom; kad polje stigne, počnu
  da rade bez izmene prikaza. SIM ih već daje (osim napajanja).
- Testovi: `node --test studio/tests/js/` i `simulator/.venv/bin/python -m pytest -q studio/tests`; `ui_*.js` skripte
  su ažurirane, ali se (bez Playwright-a) ne pokreću ovde.

## Pravila izrade (od korisnika)

- Jedna faza po jedna: posle faze testovi, lokalni commit, STOP i lista za ručnu proveru; dalje tek na „dalje“.
- Stari kod se ne briše dok novi panel ne radi isto ili bolje.
- Kad plan ne odgovara kodu: pitati pre improvizacije.
- Samo lokalni commit-i, bez push-a (osim kad korisnik izričito kaže), bez Claude atribucije.

## Odluke donete tokom izrade

- „Faza 1“ iz prvog zahteva = prva faza plana (Faza 0).
- Playwright se ne instalira; UI testovi se pišu, a UI se proverava ručno u browseru posle svake faze.
- Profile padajući meni ostaje kako jeste (izbor fajla ga i aktivira); stavka iz plana 0.2 izbačena.
- Zadatak 1.1 sadrži i zaštitu starog UI-ja od kolona kojih nema (prikaz „–“, prazan grafik se ne crta).
- Ključ u meta snimka je `origin` = `{engine, parts}`; `meta.source` ostaje tekst taktike.
  `hello.source` u Zadatku 2.2 (poruka WebSocket-a) nije pogođen.
- Lozinka robota se traži kroz `tools/espnet.py`, ali bez `sys.exit` u serveru (vraća "").

## Sitnice ostavljene za završni pregled

- 0.1: spec bez naslova H1; dve rečenice konteksta izostavljene; naslov Arhitekture pominje stari fajl.
- 0.2: `test_vrobot_stop_gasi_proces` bez try/finally; `espnet.password()` čita bez `encoding="utf-8"`;
  zatvaranje taba bez prekida veze ostavlja virtuelnog robota upaljenog.
- 0.3: boje natpisa „nema poze“ nisu iz tema-promenljivih; natpis ostaje ~200 ms kad poza stigne;
  ako poze prvo ima pa nestane (STM32 ispadne), lidar se ne gasi kad stane (rešava Faza 2, stanja veze).
- 1.1: IR panel `c.ir[i] || 0` je lažna nula (rešava 3.1 `hasData`); `upgrade()` ne računa `tactic_sha` za v1;
  `_set_sha(name)` ne koristi `name`; `Charts.update` računa `hasData` pri svakom osvežavanju;
  kasni `step_end` iz telemetrije posle ponovljenog koraka / timeout „?“ ima prednost (tek uz Fazu 6.1).
- 1.2: `server.py` re-eksportuje `columns`, `RUN_TIMEOUT_S`, `_runs` možda bez potrebe; `info`, `_ir_layout`,
  `no_stale_ui` ostali u `server.py`.

- 2.1: komanda posle kraja sim sesije; test virtuelnog robota pokreće Sim nit pre `try`; nema testa da realtime
  odbija pauzu/brzinu; dete-proces uvozi aiohttp preko `api.runs`.
- 2.2: robot ima dva tajmera od 100 ms (neravnomerni paketi); izuzetak u pumpi se ne loguje; tekst greške
  „ne mogu da nađem …“ važi i za sim; snimak bez `run` piše „nema snimka None“; STAT ide paralelno sa komandama
  (dobro za STOP, više TCP veza ka ESP-u).

- 3.1: `buildRun`/`appendRun` menjaju ulaz (komentar); `hasData` ponovo skenira sve-null kolone; test „bez ponovnog
  skeniranja“ je slab.
- 3.2 (vidljivo u prelaznom periodu): Profil i Repo se ne vide u „Test dela“; Taktike tokom sesije pišu „end Live
  first“; STOP bi mogao biti odsečen ako fontovi budu širi; Repo u bočnoj traci vidljiv i van repo režima; klik na
  stare kartice Live/Robot ne menja izbor u bočnoj traci; Meč je krupniji od Izvora; uz otvoren editor stari raspored je
  tesan na 768 px (rešava Faza 4).

## Odluke preko noći (2026-11-27/28, korisnik spava; proveri ujutru)

- Faza 4 nije imala korake u planu, pa je dizajn prenosa zapisan pre početka: regioni alati / glavni / bočne kartice /
  dole, paneli premeštaju postojeće elemente (isti id-jevi), a ne prepisuju logiku.
- Rezultat simulacije ostaje kartica preko stola (ne bočna kartica).
- Editor postoji samo u Taktikama; × ga zatvara bez pitanja, a nesačuvan tekst ostaje kao nacrt.
- Taktika i Strana se vide i u Vožnji i u Snimcima (isti elementi, premeštaju se), jer promena strane u Snimcima
  ponovo simulira prikazani snimak.
- U Vožnji se dok sesija radi krije brzina puštanja snimka (`#pace`), da ne postoje dve brzine.
- ESP kartica se vidi i u Vožnji SIM bez sesije (snimljen ekran učitanog snimka).
- Ime taktike koja stvarno radi (robot ili Live) je na traci, pored izvora („virtuelni · primer“).
- „Uporedi sa…“ učitava referencu tako da „Sačuvaj snimak“ i dalje čuva tvoju simulaciju; referenca se van Snimaka
  vidi kao oznaka „referenca: X ✕“ na stolu.
- Korak sada i Dnevnik u Snimcima počinju sklopljeni (mesta za listu); Grafici sklopljeni svuda osim dok se poredi.
- Nečitljiv snimak vraća grešku 422 sa porukom umesto prazne greške servera.
- Alt+1..4 menja prostor; na nekim browserima Alt+broj menja tab browsera.
- Test dela → Lidar računa međukorake na laptopu (ESP nema kod za grupe), oznaka „izračunao laptop“; za ROBOT dugme
  „Upali lidar“ šalje postojeću komandu `LIDAR ON` (robot je već podržava i sam gasi lidar kad se naoruža).

## Sitnice iz Faze 4 (za završni pregled)

- Toggle Grafika resetuje 3D kameru; grafik ugla skače na ±180°; poruke nemaju istoriju (puna poruka u tooltipu).
- „samo greške“ krije [sim] linije o sudaru; prazan filtriran dnevnik nema natpis „nema grešaka“.
- Postavka stola je tesna na 768 px kad su ESP, Korak sada i Koraci otvoreni.
- Snimci povučeni sa imenom van `[A-Za-z0-9_.-]` se vide u listi ali ne učitavaju (staro); datum posle `git pull` je
  vreme povlačenja.
- Numerička tastatura Alt+1..4 menja prostor (Windows Alt+kodovi); app.js je i dalje 1355 redova (logika ostala).
- Neki tooltip-ovi i tekst preko stola su još na engleskom.

## Nastavak na drugom računaru

```bash
git fetch && git switch redizajn-ui
python3 -m venv studio/.venv && studio/.venv/bin/pip install -r studio/requirements.txt pytest
studio/.venv/bin/python -m pytest -q studio/tests      # očekivano 130 passed
studio/.venv/bin/python studio/sim.py serve --port 8271
```

Pa u Claude Code: `/superpowers:subagent-driven-development` sa planom `docs/plan-implementacija-redizajna.md`,
uz napomenu da su Faze 0 i 1 gotove (ovaj fajl) i da se nastavlja od Faze 2.
