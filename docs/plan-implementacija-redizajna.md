# Redizajn simulator/web: plan implementacije

> **Za agente:** OBAVEZAN pod-skill: superpowers:subagent-driven-development (preporučeno) ili
> superpowers:executing-plans. Zadaci imaju polja za štikliranje (`- [ ]`).

Datum: 2026-11-26. **Stanje: odobren, izrada sa subagentima.** Izabrana maketa: varijanta A
(`~/makete-ui/varijanta-a.html`, van repoa); iz B i C ništa.

**Cilj:** simulator/web postaje jedan interfejs za robota (varijanta A). Ima levu bočnu traku sa radnim prostorima,
uvek vidljivu statusnu traku i sesiju koja simulaciju i pravog robota prikazuje na isti način.

**Arhitektura:**

- **Server:** jedna `Session` sa tri izvora (`SimSource`, `RobotSource`, `ReplaySource`) na `/ws/session`, sa listom
  sposobnosti (`capabilities`) i jednim rečnikom komandi. Snimak v2 ne sadrži lažne vrednosti.
- **Web:** `store` + registar panela + okvir (traka, bočna traka). Postojeći delovi UI-ja prelaze u panele jedan po
  jedan; stari kod se briše posle svakog prenosa.

**Tehnologija:** Python 3.11+, aiohttp; vanilla ES moduli bez build-a; three.js, uPlot, CodeMirror (već u
`web/vendor/`); pytest; Playwright (Node 20) za UI testove; `node --test` za JS jedinične testove (bez novih zavisnosti).

**Spec:** `docs/redizajn-ui.md` (pravi ga Zadatak 0.1) od:

- `docs/plan-redizajn-interfejsa.md`;
- `docs/plan-arhitektura-interfejsa.md`;
- IA audita i UX spec-a iz razgovora o redizajnu;
- makete `~/makete-ui/varijanta-a.html`.

## Globalna ograničenja

- Posle **svake** faze: `simulator/.venv/bin/python -m pytest -q simulator/tests` zeleno i
  `node simulator/tests/ui_smoke.js` zeleno (uz `python simulator/sim.py serve --no-browser`).
- Web ostaje bez build koraka: ES moduli, bez novih biblioteka; vendor ostaje kakav jeste.
- ESP kod se ne kopira ni ne menja u fazama 0–5. Faza 6 menja `ESP32/` i traži posebno „da“.
- Svi natpisi u UI-ju su na srpskom (latinica).
- Ciljni ekran je 1366×768. Traka nikad ne gubi polja Izvor, Veza, Meč i ■ STOP.
- STOP (dugme i Esc) radi iz svakog radnog prostora čim sesija radi. Provera „odbij u meču“ je na serveru ili ESP-u,
  a ne samo u UI-ju.
- Snimci v1 (postojeći `.json.gz`) se i dalje učitavaju.
- Podatak koji izvor nema je `null` ili ga nema, nikad lažna nula. UI tada piše „nema sa robota“.
- Commit-i su lokalni, bez push-a, bez Claude atribucije (`CLAUDE.md`).

## Na šta da pazi pregled

1. **Robot povezan bez STM32** (nema poze): UI ne sme da pukne. Traka piše „nema poze (STM32)“, a lidar se crta oko
   robota. Test je u Zadatku 0.3 i Zadatku 5.2.
2. **Telemetrija stane usred sesije** (WiFi): posle 1.5 s „podaci stari“, posle 5 s „veza izgubljena“. Sesija nije
   završena, a STOP i dalje šalje. Test je u Zadatku 2.2 i Zadatku 3.2.
3. **Snimak v1 iz `simulator/runs/`** se učitava i pušta. Test je u Zadatku 1.1.
4. **Stari firmver bez novih polja telemetrije:** panel pokazuje „nema sa robota“, a ne „0.00“. Grafik bez podataka se
   ne crta. Test je u Zadatku 1.1 i Zadatku 4.1.
5. **Esc dok je fokus u editoru** (CodeMirror popup otvoren), a sesija radi: STOP mora da ode. Test je u Zadatku 3.2.

---

## Faza 0: Priprema i čišćenje bez promene ponašanja ★ prva verzija

### Zadatak 0.1: Spec u jednom fajlu i polazna tačka testova

**Fajlovi:**

- novo: `docs/redizajn-ui.md`;
- izmena: prvi red u `docs/plan-redizajn-interfejsa.md` i `docs/plan-arhitektura-interfejsa.md`
  („Zamenjeno: vidi docs/redizajn-ui.md“).

- [ ] Spoji spec, arhitekturu, IA audit, UX spec i odluke (varijanta A; srpski; radni prostor sme da se menja tokom
      sesije).
- [ ] `simulator/.venv/bin/pip install pytest` (van repoa, u venv). Pokreni ceo pytest i zapiši polazni rezultat u
      commit poruku.
- [ ] Pokreni `ui_smoke.js`, `ui_f2.js`, `ui_f3.js`, `ui_faza_a.js`, `ui_faza_b.js` i `ui_faza_e.js`. Zapiši koji
      prolaze. Oni koji već sada padaju nisu kriterijum za kasnije faze.
- [ ] Commit: `Redizajn UI: jedan spec (docs/redizajn-ui.md)`

### Zadatak 0.2: Čišćenje (F0 iz arhitekture)

**Fajlovi:**

- izmena: `eurosim/server.py`, `eurosim/robotlink.py`, `web/app.js`, `web/index.html`, `web/style.css`,
  `web/view3d.js`;
- novo: `web/side.js`;
- test: `tests/test_server.py`.

**Interfejsi koje pravi:**

- `server._tactic_names() -> set[str]`, `server._dumps(o) -> str`;
- `web/side.js`: `export function mirrorX(x, side, refSide)`;
- `GET /api/profile?file=<ime>` samo čita i ne menja aktivni profil;
- `POST /api/vrobot {"action":"stop"}` se šalje pri prekidu veze sa virtuelnim robotom.

Koraci:

- [ ] Test `test_profil_citanje_ne_menja_aktivni`: GET sa `file=` drugog profila, pa `/api/info` → `profile.name` je
      i dalje stari.
- [ ] Test `test_vrobot_stop_gasi_proces`: start, pa stop → `{"running": false}` i proces je mrtav.
- [ ] Implementacija. `robotlink.default_password` koristi `espnet().password()`. Ogledanje u `app.js` (4 mesta) ide
      kroz `mirrorX`. Mrtav kod se briše.
- [ ] pytest + `ui_smoke.js` zeleni.
- [ ] Commit.

**Briše se:**

- `#logcard`, `button.live-on`, `#stepscard .tablewrap`;
- `mk` u `view3d.js:447`, `let tab` u `app.js`, grana `stat` u `robot_ws`;
- duplikat regex-a lozinke;
- 4 kopije ogledanja.

### Zadatak 0.3: Lidar sa robota vidljiv i bez poze (A1 iz kontrolne table)

**Fajlovi:** izmena `eurosim/robotlink.py` (`TelemRecorder.feed_lidar`); test `tests/test_robot.py`.

- [ ] Test `test_lidar_bez_poze_se_snima`: `feed_lidar` pre ijednog frame-a sa pozom → postoji događaj `lidar` sa
      `"nopose": true` i `pose == [250, 1000, 0]`.
- [ ] Implementacija: poslednja poznata poza, inače START iz `field`, uz `nopose`.
- [ ] `web/view3d.js setLidar`: kad je `nopose`, natpis „nema poze: STM32 nije povezan“.
- [ ] Testovi zeleni. Commit.

---

## Faza 1: Snimak v2 i server po modulima ★

### Zadatak 1.1: Snimak v2 bez lažnih polja

**Fajlovi:** izmena `eurosim/record.py`, `eurosim/robotlink.py`, `eurosim/sim.py` (meta); test novo
`tests/test_record.py`.

**Interfejsi koje pravi:**

- `record.VERSION = 2`;
- `record.upgrade(d: dict) -> dict` (v1 → v2);
- meta v2 ključevi: `source: {"engine": "sim"|"robot"|"replay", "parts": {"pogon": "sim"|"pravi",
  "lidar": "sim"|"pravi"|"snimak", ...}}`, `tactic_sha: str|None`, `scenario: str|None`, `profile: str`.

Koraci:

- [ ] Test `test_v1_snimak_se_ucitava`: ručno napravljen v1 dict (bez `source`, `version: 1`) → posle `upgrade` važi
      `meta.source.engine == "sim"`; sa `result.robot = True` → `"robot"`.
- [ ] Test `test_telemetrija_nema_laznih_polja`: frame iz `TelemRecorder.feed` nema ključeve `ox`, `w`, `vl`, `vr`,
      `v_ref`, `w_ref`, `reg`, `ir`.
- [ ] Test `test_step_end_iz_telemetrije_ima_prednost`: paket sa `"step_end": [3, "x", true, null, 1200]` → događaj
      `step_end` bez parsiranja dnevnika. Parser dnevnika ostaje za stari firmver.
- [ ] Implementacija: `Recording.load` zove `upgrade`; `RobotLink.recording()` koristi `Recording`.
- [ ] Testovi zeleni. Commit.

### Zadatak 1.2: `server.py` podeljen po modulima

**Fajlovi:**

- novo: `eurosim/api/__init__.py`, `api/tactics.py`, `api/runs.py`, `api/repo.py`, `api/profile.py`,
  `api/scenarios.py`;
- izmena: `eurosim/server.py` (samo `make_app`, `index`, `live`, `robot_ws`, `vrobot`, `serve`).

- [ ] Premesti handlere bez promene ruta i odgovora. `make_app` registruje rute iz modula.
- [ ] Ceo `test_server.py` zelen bez izmena testova. Commit.

**Briše se:** ništa osim premeštenog koda.

---

## Faza 2: Sesija i izvori na serveru ★

### Zadatak 2.1: `Source` i tri izvora

**Fajlovi:** novo `eurosim/session.py`; test novo `tests/test_session.py`.

**Interfejsi koje pravi (`eurosim/session.py`):**

```
class Source:                      # zajednički oblik
    kind: str                      # "sim" | "robot" | "replay"
    capabilities: frozenset[str]   # iz CAPS
    async def start(self) -> None
    async def poll(self) -> dict   # {"frames":[...], "events":[...], "meta": dict|None, "t": int, "age": int|None, "final": bool}
    async def command(self, c: list) -> dict   # {"cmd": str, "ok": bool, "lines": [str]}
    async def close(self) -> dict  # snimak v2 (Recording.to_dict())
CAPS = {"pause","speed","esp_screen","esp_buttons","arm","cord","test","push","run","stop","opponents","lidar","manual","seek"}
SimSource(kw)        # obuhvata _live_worker; caps: pause speed esp_screen esp_buttons arm cord test stop opponents lidar
RobotSource(host, pw, prof)  # obuhvata RobotLink; caps: push run stop lidar
ReplaySource(path)   # caps: seek
```

- [ ] Test `test_nepodrzana_komanda`: `ReplaySource.command(["arm"])` → `{"ok": False, "lines": ["nepodržano"]}`.
- [ ] Test `test_sim_source_sposobnosti_i_podaci`: posle `start` i 1 s, `poll()` vraća frame-ove, a
      `"pause" in capabilities`.
- [ ] Test `test_robot_source_preko_virtuelnog_robota`: virtuelni robot (kao
      `test_virtuelni_robot_push_run_telemetrija`), pa `command(["push","primer",None])` → ok.
- [ ] Implementacija. Testovi zeleni. Commit.

### Zadatak 2.2: `/ws/session`, stari WebSocket-i kao alijasi

**Fajlovi:** izmena `eurosim/server.py`; test `tests/test_session.py`.

**Poruke:**

- prva poruka: `{"type":"hello","source":{"engine":..,"parts":{..}},"capabilities":[..]}`;
- zatim `{"type":"data",...poll()}`, `{"type":"reply",...}`, `{"type":"state","link":"ok"|"stale"|"lost","age":ms}`
  i `{"type":"end","run":...}`;
- `link` je `stale` kad je `age > 1500`, a `lost` kad je `age > 5000`.

Koraci:

- [ ] Test `test_ws_session_hello_pa_podaci` (sim).
- [ ] Test `test_link_stale_pa_lost`: `RobotSource` sa lažnim UDP-om koji ćuti → stanja `stale`, pa `lost`, a sesija
      se ne zatvara.
- [ ] Test `test_stop_radi_i_kad_je_veza_izgubljena`: posle `lost`, `["stop"]` → poziv `link.cmd("STOP")`.
- [ ] `/ws/live` i `/ws/robot` zovu isti handler (`engine=sim` / `engine=robot`). Postojeći `test_live_websocket` i UI
      testovi prolaze bez izmena.
- [ ] Commit.

**Briše se:** dupli kod `live()` / `robot_ws()` (WS setup, `dumps`, „sačuvaj last, pošalji end“).

---

## Faza 3: Okvir varijante A u web-u ★

### Zadatak 3.1: `store`, klijent sesije, inkrementalni snimak

**Fajlovi:**

- novo: `web/core/store.js`, `web/core/session.js`, `web/core/run.js` (premešten `buildRun`);
- test: novo `tests/js/run.test.mjs`;
- izmena: `web/app.js` (koristi `run.js`).

**Interfejsi koje pravi:**

```
store.js:   createStore(initial) -> { get(), set(patch), subscribe(fn) -> unsubscribe }
session.js: connect({engine, ...params}) -> { capabilities:Set, source, command(c:list), on(type, fn), close() }
run.js:     buildRun(d) -> run ;  appendRun(run, frames, events) -> run   // ne prolazi ponovo stare događaje
            hasData(run, key) -> bool                                       // kolona postoji i nije sva null
```

Koraci:

- [ ] Test `appendRun daje isto što i buildRun nad svim podacima` (frame-ovi i događaji podeljeni u 3 dela).
- [ ] Test `hasData je false za kolonu koje nema i za sve-null kolonu`.
- [ ] `node --test simulator/tests/js/` zeleno.
- [ ] `liveRebuild` koristi `appendRun`.
- [ ] Commit.

### Zadatak 3.2: Okvir — statusna traka, bočna traka, registar panela

**Fajlovi:**

- novo: `web/core/panels.js`, `web/shell/strip.js`, `web/shell/rail.js`, `web/shell/layout.js`;
- izmena: `web/index.html`, `web/style.css`, `web/app.js`;
- test: novo `tests/ui_shell.js`.

**Interfejsi koje pravi:**

```
panels.js: registerPanel({id, title, workspaces:[..], region:"main"|"side"|"bottom"|"tool", priority:int,
                          needs:[cap|dataKey], open:bool, mount(el, ctx), update(state)})
           panelsFor(workspace, caps) -> [panel]        // side po priority; needs nezadovoljen → siv sa razlogom
ctx = { store, command(c), go(workspace) }
radni prostori: "taktike" | "test" | "voznja" | "snimci";  ključ u localStorage "eurosim.ws"
```

- **Izgled po maketi A:**
  - bočna traka 100 px sa 4 prostora, a dole Izvori, Repo, Profil, Pomoć;
  - u Vožnji, ispod nje izbor SIM/ROBOT;
  - traka visoka 72 px sa tankom linijom u boji izvora i poljima Izvor, Veza, Poza, Meč, Korak, Detekcija, ⚠n,
    ■ STOP;
  - tokeni i veličine iz dizajn sistema: osnova 15–16 px, kontrole ≥ 40 px, STOP ≥ 54 px.
- **Prelazni korak:** stari `#bar`, `#main` i `#timeline` se montiraju kao privremeni „legacy“ sadržaj glavnog
  prostora. Postojeći id-jevi ostaju, pa stari UI testovi prolaze.

Koraci:

- [ ] `ui_shell.js` (Playwright, 1366×768):
  - bočna traka ima 4 stavke;
  - traka pokazuje „SIM“;
  - `■ STOP` je vidljiv i ceo u prozoru;
  - posle starta Live-a, Esc šalje `["stop"]`, i to i kad je fokus u editoru sa otvorenim popupom za dopunu;
  - posle prekida telemetrije (virtuelni robot ugašen) traka pokazuje „podaci stari“, pa „veza izgubljena“.
- [ ] `ui_smoke.js` i ostali UI testovi koji su prolazili u Zadatku 0.1 i dalje prolaze.
- [ ] Ručno: 1366×768, Simulate / Live / Virtuelni robot rade; prelaz između prostora tokom Live-a ne gasi sesiju.
- [ ] Commit.

---

## Faza 4: Prenos postojećih panela, jedan po jedan ★

Svaki zadatak:

- pravi `web/panels/<ime>.js` i registruje ga;
- briše odgovarajući deo iz `app.js`, `index.html` i `style.css`;
- menja selektore u UI testovima;
- završava sa zelenim pytest-om i UI testovima i ručnim prolazom kroz prostor koji je dirao.

| Zadatak | Paneli (prostor, zona) | Provera | Briše se iz starog |
|---|---|---|---|
| **4.1** | Teren (sve, main), Vreme (Vožnja/Snimci, bottom), Grafici + **ugao θ** (bottom, sklopivo) | test `grafik bez podataka se ne crta` (robot snimak); `ui_smoke` | `#viewwrap` izvan terena, `#timeline`, `charts.js` ostaje kao komponenta |
| **4.2** | Korak sada, Koraci, Dnevnik (filter „samo greške“), Rezultat | `ui_smoke` (3 koraka, OK) | desna kolona `#side-panel`, `#status`, `#stepscard`, `#logcard` |
| **4.3** | Editor + Problemi + Komande, Pokreni [meč\|test] (Taktike) | `ui_f2.js` prepravljen | `#editorPane` izvan editora, `#apiDrawer`, `#mode`, `#run` u staroj traci |
| **4.4** | Vožnja: kontrole (Naoruži, Činč, Test, brzina, pauza, Završi, Pošalji, Pošalji i pokreni, Prekini vezu, pali se po `capabilities`), ESP (samo uz `esp_screen`), Protivnici + Postavka stola (Taktike i Vožnja-SIM) | `ui_f3.js` prepravljen; ručno: Live, virtuelni robot | `#rowSim/#rowLive/#rowRobot`, kartice Simulate/Live/Robot, 3× STOP, 2× Follow, End/Disconnect, `startLive/startRobot` duplikat, `#robotConnect` (prelazi u Izvori) |
| **4.5** | Snimci: lista (datum, izvor, taktika, ishod, filter), učitavanje, postojeće poređenje (pin/compare) | novi `ui_snimci.js`; test `v1 snimak se pušta u UI-ju` | `⋯ Runs` meni, `#cmpTools` sa stola |
| **4.6** | Kraj prelaza: „legacy“ montaža se briše; Prikaz ▾ u dve grupe („Šta crtam“ / „Kako izgleda“); kamera prati robota = „Kamera prati robota“ | svi UI testovi; ručni prolaz kroz 4 prostora na 1366×768 | stari `#bar`, `setTab`, `localStorage eurosim.tab`; `app.js` ostaje samo kao ulazna tačka (~100 redova) |

---

## Faza 5: Novi režimi bez izmena na ESP-u

### Zadatak 5.1: Izvori ▾ i hibrid kroz sesiju ★

**Fajlovi:** novo `web/panels/sources.js`; izmena `eurosim/session.py` (`SimSource` sa
`parts.lidar = "pravi"|"snimak"`), `eurosim/lidarsrc.py`.

- [ ] Test `test_hibrid_lidar_iz_snimka_kroz_sesiju`: `engine=sim`, `parts.lidar=file:<snimak>` →
      `hello.source.parts.lidar == "snimak"`, a stižu događaji `lidar`.
- [ ] UI: unapred zadate kombinacije a, b i d. Nedozvoljeno (pravi pogon + sim lidar) je sivo, sa razlogom. Dok
      sesija radi, blok se samo čita.
- [ ] Commit.

**Briše se:** `#lidarSrc`, čitanje host-a i lozinke iz Robot prozora za hibrid.

### Zadatak 5.2: Test dela → Lidar ★

**Fajlovi:** novo `web/panels/lidar.js`, `eurosim/lidarview.py` (međukoraci na laptopu); test novo
`tests/test_lidarview.py`.

**Interfejsi koje pravi:** `lidarview.stages(scan: dict, pose: tuple|None, prof) -> {"in": [[x,y]], "out": [[x,y]],
"groups": [{"x","y","n","dist","angle"}], "nearest": dict|None}`. Računa se istim ESP modulom (`ESP32/lib/lidar.py`)
gde postoji funkcija; inače na laptopu, a prikaz kaže „izračunao laptop“.

Koraci:

- [ ] Test `test_tacke_van_stola_odbacene`: tačka na (3200, 1400) ide u `out`.
- [ ] Test `test_bez_poze_nema_stola`: `pose=None` → sve tačke u koordinatama robota, `in == []`.
- [ ] Test `test_grupa_protivnika`: kocka 300×300 na 420 mm → jedna grupa, `dist` 420 ± 30.
- [ ] UI: radar oko robota (radi i bez poze), slojevi (sirovo / van stola / grupe), Hz, broj tačaka, starost kruga,
      „Snimi krugove“.
- [ ] Commit.

### Zadatak 5.3: Poređenje sim / robot (kasnije)

Tabela koraka A / B / Δ, grafici poravnati po početku koraka, „Simuliraj isto“ (iz meta v2), istaknut korak koji
postoji samo u jednom snimku. Test `test_poravnanje_koraka_i_samo_u_jednom`.

### Zadatak 5.4: Automatsko snimanje sesija sa robotom (kasnije)

Lokalno, u `~/Eurosim/robot-runs/`, van gita; „Sačuvaj u repo“ kopira u `simulator/runs/`. Test
`test_kraj_robot_sesije_pravi_fajl`.

---

## Faza 6: ESP strana (posebno „da“ za svaki zadatak; kasnije)

| Zadatak | Šta | Fajlovi | Provera |
|---|---|---|---|
| **6.1** | Telemetrija v2 (`w`, IR raw/maska, zdravlje, krug petlje, RAM, RSSI, verzija, aktuatori, `step_end`) + `e2h`/`h2e` u `protocol.yaml` + `gen.py`; spora polja na 1 Hz | `protocol/protocol.yaml`, `protocol/gen.py`, `ESP32/lib/telem.py`, `eurosim/robotlink.py` | `ESP32/tests/host` + test virtuelnog robota; krug petlje pre/posle (STAT) |
| **6.2** | Paneli IR, Zdravlje, Odluke; `tac.decide(text)` u tac API-ju | `ESP32/lib/tac.py`, `web/panels/*` | test `odluka_stize_kao_dogadjaj` |
| **6.3** | Ručne komande (MOVE/ROTATE/GOTO/ACT/IRMASK/POSE) na upload serveru, van `BUSY_OK`; UDP „MAN“ keepalive 200 ms, bez njega STOP posle 500 ms; Test dela → Pogon, Mehanizmi, IR, „kopiraj u taktiku“ | `ESP32/lib/upload.py`, `telem.py`, `session.py`, `web/panels/drive.js`, `acts.js` | test `rucna_komanda_odbijena_u_mecu`, `bez_keepalive_robot_staje` (virtuelni robot) |
| **6.4** | Lažirani delovi na robotu (kombinacija c) | `ESP32/config.py`, `lib/robot.py` | test na virtuelnom robotu |
| **6.5** | Rezultat detekcije lidara sa robota u telemetriji; oznaka „robot“ / „laptop“ | `lib/telem.py`, `lidar.py`, `panels/lidar.js` | test `detekcija_sa_robota_ima_prednost` |

---

## Prva upotrebljiva verzija vs. kasnije

- **★ Prva verzija (zamenjuje stari UI, sve postojeće funkcije su prenete):**
  - Faza 0 – Faza 4;
  - 5.1 (hibrid);
  - 5.2 (lidar).

  Grubo: 15 zadataka, sve u `simulator/`, bez ESP-a.
- **Kasnije:**
  - 5.3 poređenje, 5.4 automatski snimci;
  - Faza 6 (ručno upravljanje i nova telemetrija traže ESP);
  - više robota (PAMI), joystick, kalibracija K0/K1, baterija.

**Napomena o veličini:** ovo je plan po fazama. Pre početka svake faze pravi se kratak spisak koraka za tu fazu prema
stanju koda u tom trenutku, jer faze 3–4 zavise od toga kako ispadnu 1–2.
