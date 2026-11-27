# Redizajn UI: napredak izrade

Stanje 2026-11-26. Plan: `docs/plan-implementacija-redizajna.md`. Spec: `docs/redizajn-ui.md`.
Grana: `redizajn-ui` (lokalna). Maketa: varijanta A (`~/makete-ui/varijanta-a.html`, van repoa).

## Gde je stalo

- **Faza 0 — gotova** (0.1 jedan spec, 0.2 čišćenje, 0.3 lidar sa robota bez poze).
- **Faza 1 — gotova** (1.1 snimak v2 sa `meta.origin`, bez lažnih polja sa robota; 1.2 server po modulima `eurosim/api/`).
- **Faza 2 — gotova** (2.1 `eurosim/session.py`: `SimSource`, `RobotSource`, `ReplaySource`; 2.2 `/ws/session`
  sa porukama `hello` i `state` (`ok`/`stale`/`lost`), `/ws/live` i `/ws/robot` su alijasi, stari UI radi bez izmena).
- Testovi: `simulator/.venv/bin/python -m pytest -q simulator/tests` → 145 passed (polazno 119).
- Ručno u browseru (1366×768): brza simulacija, Live (Naoruži, činč, Esc = STOP, End), virtuelni robot
  (Push & Run, Esc, Disconnect), robot koji se ne javlja („no telemetry“, STOP se i dalje šalje) — bez grešaka.
- **Sledeće: Faza 3** (3.1 `store`, klijent sesije, inkrementalni snimak; 3.2 okvir varijante A: traka, bočna traka,
  registar panela).

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

## Nastavak na drugom računaru

```bash
git fetch && git switch redizajn-ui
python3 -m venv simulator/.venv && simulator/.venv/bin/pip install -r simulator/requirements.txt pytest
simulator/.venv/bin/python -m pytest -q simulator/tests      # očekivano 130 passed
simulator/.venv/bin/python simulator/sim.py serve --port 8271
```

Pa u Claude Code: `/superpowers:subagent-driven-development` sa planom `docs/plan-implementacija-redizajna.md`,
uz napomenu da su Faze 0 i 1 gotove (ovaj fajl) i da se nastavlja od Faze 2.
