# Gambit Studio: Senzori, Poveži robota, preimenovanje · plan implementacije

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Cilj:** prostor Senzori (maketa B) umesto „Test dela“, „Poveži robota“ na statusnoj traci, ime Gambit Studio i
folder `studio/`.

**Arhitektura:** sesija ostaje jedini izvor uživo (veza = ROBOT sesija pokrenuta sa trake). Senzori su jedan panel sa
svojim spiskom blokova (`web/senzori/`); čisti moduli bez DOM-a (`izvor.js`, `podaci.js`, `skica.js`) odlučuju oznaku
izvora, vrednosti i geometriju i imaju node testove. Detalj lidara su postojeći lidar paneli (`panels/lidar.js`)
prikazani kad je `store.sensOpen === 'lidar'`, pa sve što Test dela → Lidar ume ostaje.

**Tehnologije:** Python 3 + aiohttp (server, pytest), vanilla JS ES moduli bez build koraka (`node --test`), canvas 2D.

**Spec:** `docs/plan-gambit-studio-senzori.md` (odobren dizajn; čitati uz ovaj plan). Ciljni izgled: maketa
`~/makete-ui/senzori/b.html` (van repoa), stanje „Robot sa svim poljima“.

## Globalna ograničenja

- Bez izmena ponašanja ESP-a, Nucleo-a i protokola. U `ESP32/` se menjaju samo komentari (putanja `simulator/`).
- Interna imena ostaju: paket `eurosim`, `sim.py`, `~/.eurosim.json`, `~/Eurosim`, `EUROSIM_*`, ključevi `eurosim.*`.
- `[lidar] z` u Profilu se ne menja (određuje šta simulirani lidar vidi).
- Svi natpisi na srpskom; „Eurosim“ nigde gde ga korisnik vidi.
- 1366×768 bez skrolovanja glavnog prostora Senzora.
- Stari kod se briše tek kad novo radi isto ili bolje. Kad plan ne odgovara kodu: stati i pitati.
- Posle svake **faze**: pun pytest + node testovi, lokalni commit, STOP, lista za ručnu proveru u browseru; dalje tek na
  „dalje“. Samo lokalni commit-i, bez push-a, bez Claude atribucije.
- Testovi (u worktree-u venv ostaje u starom folderu i radi i posle preimenovanja):
  `simulator/.venv/bin/python -m pytest -q studio/tests` i `node --test studio/tests/js/` (pre Faze A: `simulator/…`).
- Playwright se ne instalira; `ui_*.js` se ažuriraju, ne pokreću.

## Fokus pregleda

1. **Robot povezan bez Nucleo-a** (ESP šalje telemetriju bez `x`, pa snimak sesije nema nijedan frame; stižu samo
   krugovi lidara): blokovi pogona pišu „nepovezano: Nucleo ne javlja (nema poze)“, lidar radi, ništa ne puca. → test u
   Tasku 6.
2. **Sesija se završi dok je otvoren detalj bloka** (`sensOpen` ostaje): detalj pokazuje „nepovezano“, „← Svi senzori“
   radi; detalj lidara ostaje dostupan (izvor Snimak). → test u Tasku 6 (izvor bez sesije) i ručna provera Faze C.
3. **Sačuvan prostor `eurosim.ws = 'test'`** iz starije verzije: otvara Senzore. → test u Tasku 4.
4. **Prenos iz starog foldera kad isti fajl postoji i u `studio/`**: ne prepisuje, ostavlja stari, javlja. → test u
   Tasku 1.
5. **Hibrid sa lidarom iz snimka** (`session.lidar === 'file'`): lidar blok ima oznaku SNIMAK, traka ne piše
   „lidar: host“ nego „lidar iz snimka“. → testovi u Tasku 3 i Tasku 6.

---

## Faza A · Preimenovanje

### Task 1: `simulator/` → `studio/`, prepoznavanje repoa, prenos lokalnih fajlova

**Files:**
- Move: `git mv simulator studio` (ceo folder; netracked `.venv`, `lidar/` ostaju u starom folderu)
- Modify: `studio/eurosim/paths.py` (`_is_repo`, `configure`: `SIM = ROOT / "studio"`, standalone `BUNDLE / "studio"`,
  `WEB`), `studio/eurosim/repo.py` (`SHARED`, poruka provere, `diff -- studio/profiles`), `studio/eurosim/server.py`
  (poziv prenosa, `info["migrated"]`), komentari i docstring-ovi sa `simulator/` u `studio/eurosim/*.py`
- Create: `studio/eurosim/migrate.py`
- Modify: `.github/workflows/simulator.yml`, `start.sh`, `start.bat`, `.gitignore` (`/studio/.venv/`), `README.md`
  (koren, ako pominje putanju), `studio/README.md`, komentari u `ESP32/lib/lidarpkt.py`, `ESP32/sim/fakelidar.py`,
  `ESP32/tactics/kamenolomi.py`, `ESP32/PROBLEMI.md`, `docs/redizajn-napredak.md` (odeljak „Nastavak na drugom računaru“)
- Test: `studio/tests/test_repo.py` (fixture pravi `studio/`), Create `studio/tests/test_migrate.py`

**Interfaces:**
- Produces: `paths.is_repo(p) -> bool` (ESP32/lib/tac.py i `studio/`); `paths.old_layout(p) -> bool` (ima `simulator/`,
  nema `studio/`); `repo.check(p)` za stari raspored vraća poruku koja sadrži „git pull“;
  `migrate.move_old_local(root: Path) -> {"moved": [str], "skipped": [str]}` (relativne putanje);
  `/api/info` dobija `"migrated": {"moved": [...], "skipped": [...]}` (prazne liste kad nema ničega).

- [ ] **Step 1: Napiši testove koji padaju** (`test_migrate.py`, dopuna `test_repo.py`)

```python
def test_move_old_local_premesta_bez_prepisivanja(tmp_path):
    (tmp_path / "studio" / "lidar").mkdir(parents=True)
    old = tmp_path / "simulator" / "lidar"; old.mkdir(parents=True)
    (old / "a.jsonl.gz").write_bytes(b"A"); (old / "b.jsonl.gz").write_bytes(b"OLD")
    (tmp_path / "studio" / "lidar" / "b.jsonl.gz").write_bytes(b"NEW")
    (tmp_path / "simulator" / ".venv").mkdir()                     # .venv se ne dira
    r = migrate.move_old_local(tmp_path)
    assert r["moved"] == ["lidar/a.jsonl.gz"] and r["skipped"] == ["lidar/b.jsonl.gz"]
    assert (tmp_path / "studio/lidar/a.jsonl.gz").read_bytes() == b"A"
    assert (tmp_path / "studio/lidar/b.jsonl.gz").read_bytes() == b"NEW"
    assert (tmp_path / "simulator/lidar/b.jsonl.gz").exists() and (tmp_path / "simulator/.venv").exists()

def test_move_old_local_bez_starog_foldera(tmp_path):
    assert migrate.move_old_local(tmp_path) == {"moved": [], "skipped": []}

def test_repo_prepoznaje_studio(tmp_path):            # test_repo.py: fixture sa studio/
    assert paths.is_repo(make_repo(tmp_path))

def test_stari_raspored_trazi_git_pull(tmp_path):
    (tmp_path / "ESP32" / "lib").mkdir(parents=True); (tmp_path / "ESP32/lib/tac.py").write_text("")
    (tmp_path / "simulator").mkdir()
    ok, msg = repo.check(tmp_path)
    assert not ok and "git pull" in msg
```

Prenose se samo podfolderi `lidar`, `runs`, `scenarios`, `opponents`, `profiles` (rekurzivno, svi fajlovi); prazni stari
folderi se brišu, `.venv` i ostalo ostaje.

- [ ] **Step 2:** `simulator/.venv/bin/python -m pytest -q simulator/tests/test_repo.py` → FAIL (još nema `studio/`).
- [ ] **Step 3:** `git mv simulator studio`; izmene iz liste Files. Prenos se poziva jednom pri pokretanju servera u
  repo režimu (u `server.make_app` ili `sim.py serve`), rezultat ide u `app[STATE]["migrated"]` i u `/api/info`.
- [ ] **Step 4:** `simulator/.venv/bin/python -m pytest -q studio/tests` → sve PASS (162 + novi);
  `node --test studio/tests/js/` → PASS; `bash -n start.sh`.
- [ ] **Step 5:** `grep -rn "simulator/" --include=*.py --include=*.sh --include=*.bat --include=*.yml . | grep -v "^./docs/"`
  pokazuje samo `migrate.py` i komentare koji namerno pominju stari folder.
- [ ] **Step 6: Commit** `Preimenovanje: simulator/ → studio/ (repo, CI, start skripte, prenos lokalnih snimaka)`

### Task 2: Ime Gambit Studio u aplikaciji

**Files:**
- Modify: `studio/web/index.html` (`<title>Gambit Studio</title>`), `studio/web/shell/rail.js` (logo na vrhu trake:
  ikonica + „Gambit“ / „Studio“, kao u maketi), `studio/web/style.css` (`.rl-logo`), `studio/web/core/keys.js` ili
  prozorčić Pomoć (naslov „Gambit Studio · prečice“), `studio/web/app.js` (poruka za `info.migrated`:
  „Premešteno iz starog foldera simulator/: N fajlova“ + spisak preskočenih), vidljivi „Eurosim“ u `studio/web/**`
- Test: `studio/tests/js/shell.test.mjs` (dopuna)

**Interfaces:**
- Produces: `RAIL_LOGO = {title: 'Gambit', sub: 'Studio'}` export iz `rail.js`.

- [ ] **Step 1:** test: `assert.deepEqual(RAIL_LOGO, { title: 'Gambit', sub: 'Studio' })`; i da `index.html` ima
  `<title>Gambit Studio</title>` (čita fajl sa diska).
- [ ] **Step 2:** `node --test studio/tests/js/shell.test.mjs` → FAIL.
- [ ] **Step 3:** izmene iz liste Files.
- [ ] **Step 4:** `node --test studio/tests/js/` → PASS; `grep -rn "Eurosim" studio/web --include=*.html --include=*.js`
  bez pogodaka u tekstu koji se prikazuje (ključevi `eurosim.*` i komentari su u redu).
- [ ] **Step 5: Commit** `Gambit Studio: ime u aplikaciji, logo u bočnoj traci, poruka o prenetim fajlovima`

**STOP Faze A** — ručno: `python studio/sim.py serve --port 8271` iz worktree-a; tab „Gambit Studio“, logo u traci;
poruka o prenetim snimcima iz `simulator/lidar/` (u worktree-u ih ima), snimci se vide u Test dela → Lidar → Snimak;
`start.sh` pokreće aplikaciju.

---

## Faza B · „Poveži robota“ na traci

### Task 3: Čista logika polja Veza

**Files:**
- Modify: `studio/web/shell/strip.js` (`linkView`, nova `connectView`)
- Test: `studio/tests/js/strip.test.mjs`

**Interfaces:**
- Consumes: store polja `session {kind, host, virtual, lidar}`, `lidarScan {wall}`, `telemetry`, `linkAge`, `linkState`.
- Produces: `linkView(st, now = performance.now()) -> {cls, text, connect: bool, disconnect: bool}`;
  `connectView(st) -> {ok: bool, reason: string|null}` (može li „Poveži robota“).

- [ ] **Step 1: testovi**

```js
test('bez sesije: dugme Poveži robota', () => {
  const v = linkView({ session: null });
  assert.equal(v.connect, true); assert.equal(v.disconnect, false); assert.equal(v.text, 'nije povezano');
});
test('ROBOT: Prekini, tekst kao pre', () => {
  const v = linkView({ session: { kind: 'robot', host: 'eurokik.local' }, telemetry: true, linkAge: 100 });
  assert.equal(v.disconnect, true); assert.equal(v.connect, false); assert.equal(v.text, 'povezan');
});
test('hibrid sa pravim lidarom: lidar: host, bez Prekini', () => {
  const v = linkView({ session: { kind: 'sim', lidar: 'robot', host: 'eurokik.local' }, speed: 1,
    lidarScan: { wall: 1000 } }, 1500);
  assert.equal(v.text, 'lidar: eurokik.local'); assert.equal(v.cls, 'ok'); assert.equal(v.disconnect, false);
});
test('hibrid: lidar stao duže od 1,5 s je warn', () => {
  assert.equal(linkView({ session: { kind: 'sim', lidar: 'robot', host: 'h' }, speed: 1, lidarScan: { wall: 0 } }, 2000).cls, 'warn');
});
test('hibrid iz snimka: lidar iz snimka', () => {
  assert.equal(linkView({ session: { kind: 'sim', lidar: 'file' }, speed: 1 }).text, 'lidar iz snimka');
});
test('SIM sesija: Poveži se odbija sa razlogom', () => {
  assert.deepEqual(connectView({ session: { kind: 'sim' } }), { ok: false, reason: 'Sesija radi: prvo Završi u Vožnji' });
  assert.deepEqual(connectView({ session: null }), { ok: true, reason: null });
});
```

Ako `session.host` ne postoji za hibrid, `app.js` `bridgeSession` ga dodaje (host iz `#rHost` pri pokretanju).

- [ ] **Step 2:** `node --test studio/tests/js/strip.test.mjs` → FAIL.
- [ ] **Step 3:** implementacija u `strip.js` (stara polja `cls`/`text` za SIM i ROBOT ostaju ista).
- [ ] **Step 4:** → PASS. **Step 5: Commit** `Traka: Veza zna za Poveži / Prekini i hibrid (lidar: host)`

### Task 4: Prozorčić „Poveži robota“ i Vožnja bez Izvora

**Files:**
- Modify: `studio/web/shell/strip.js` (dugmad `#stripConnect`, `#stripDisc` u polju Veza; prozorčić `#vezaPop` ispod
  trake), `studio/web/index.html` (premesti `#rHost`, `#rPass`, `#rConnect`, `#rVirtual` iz `#izvori` u `#vezaPop`,
  id-jevi isti), `studio/web/panels/izvori.js` + `studio/web/core/izvori.js` (bez dela za vezu; hibrid i dalje čita
  `#rHost`/`#rPass`), `studio/web/panels/voznja-alati.js` (ROBOT „▶ Pokreni sesiju“ otvara `#vezaPop`), `studio/web/app.js`
  (Prekini = postojeći prekid veze; `ctx.openConnect`), `studio/web/style.css`
- Test: `studio/tests/js/izvori.test.mjs` (izbaci očekivanja za vezu ako ih ima), `studio/tests/ui_shell.js` (ažuriraj, ne pokreći)

**Interfaces:**
- Consumes: `linkView`, `connectView` (Task 3).
- Produces: `mountStrip(el, ctx)` sa `ctx.openConnect(anchor?)`; `ctx.disconnect()` (= postojeći handler „Prekini
  vezu“ iz Vožnje).

- [ ] **Step 1:** node test (ako `izvori.test.mjs` proverava stavke veze, izmeni ga da ih više nema) → FAIL.
- [ ] **Step 2:** izmene iz liste Files. Klik na „Poveži robota“ dok SIM sesija radi: `notice(connectView(st).reason)`.
  Prozorčić se zatvara na ✕, Esc (Esc i dalje šalje STOP ako sesija radi) i klik van njega.
- [ ] **Step 3:** `node --test studio/tests/js/` → PASS; `node --check` na svakom izmenjenom JS fajlu.
- [ ] **Step 4: Commit** `Poveži robota na traci: veza važi u svim prostorima; Vožnja ROBOT više ne vodi u Izvori`

**STOP Faze B** — ručno (1366×768): bez sesije „Poveži robota“ → Virtuelni robot → traka ROBOT, Veza „povezan“,
„Prekini“ radi; iz Vožnje ROBOT „▶ Pokreni sesiju“ otvara isti prozorčić; dok radi SIM Live klik daje poruku;
hibrid (Izvori b, pravi lidar) traka „lidar: host“; Izvori više nemaju polja za vezu.

---

## Faza C · Prostor Senzori: okvir

### Task 5: Prostor `senzori` umesto `test`

**Files:**
- Modify: `studio/web/core/panels.js` (`WORKSPACES = ['taktike', 'senzori', 'voznja', 'snimci']`; `loadWorkspace`
  čita staro `'test'` kao `'senzori'`), `studio/web/shell/rail.js` (stavka `senzori`, „Senzori“, ikonica merača,
  title „Senzori: pregled svih senzora robota (Alt+2)“), `studio/web/core/keys.js` (`timeKey`: `ws === 'senzori'`),
  `studio/web/shell/strip.js` (`stripErr`: `'senzori'`), `studio/web/panels/poruka.js`, `studio/web/panels/lidar.js`
  (`workspaces: ['senzori']`, `when: st => st.sensOpen === 'lidar'` na sva tri panela, `visible()`), `studio/web/shell/layout.js`
  (ponovni raspored i kad se promeni `sensOpen`)
- Test: `studio/tests/js/panels.test.mjs`, `studio/tests/js/keys.test.mjs`

**Interfaces:**
- Produces: store `sensOpen: null | string` (id otvorenog detalja); radni prostor `'senzori'`.

- [ ] **Step 1: testovi**

```js
test('staro eurosim.ws = test otvara senzori', () => {
  const s = { getItem: () => 'test' };
  assert.equal(loadWorkspace(s), 'senzori');
});
test('WORKSPACES', () => assert.deepEqual(WORKSPACES, ['taktike', 'senzori', 'voznja', 'snimci']));
test('lidar paneli samo u detalju lidara', () => {
  const ids = st => panelsFor('senzori', [], st).map(p => p.id);
  assert.ok(ids({ sensOpen: 'lidar' }).includes('lidar'));
  assert.ok(!ids({ sensOpen: null }).includes('lidar'));
});
```

(poslednji test uvozi `panels/lidar.js` samo ako se može učitati u node-u; ako ne može, proveriti isto na registru sa
lažnim panelom sa istim `when` i proveriti `when` ručno u Fazi C).

- [ ] **Step 2:** → FAIL. **Step 3:** izmene. **Step 4:** `node --test studio/tests/js/` → PASS.
- [ ] **Step 5: Commit** `Prostor Senzori umesto Test dela (id senzori, Alt+2, staro sačuvano mesto vodi u Senzore)`

### Task 6: Čisti moduli `izvor.js` i `podaci.js`

**Files:**
- Create: `studio/web/senzori/izvor.js`, `studio/web/senzori/podaci.js`
- Test: Create `studio/tests/js/senzori-izvor.test.mjs`, `studio/tests/js/senzori-podaci.test.mjs`

**Interfaces:**
- Consumes: `hasData(run, key)` iz `core/run.js`; `run.frameAt(t)`, `run.cols`.
- Produces:
  - `viewMode(st) -> {mode: 'robot'|'sim'|'hibrid'|'snimak'|'nista', text: string}`; `st.sens = {run, t, replay, name}`.
    Tekstovi: „Prikazuje: pravi robot · <host>“ (virtuelni: „virtuelni robot“), „Prikazuje: simulacija (Vožnja SIM) ·
    ovo nije pravi robot“, „Prikazuje: hibrid · lidar sa pravog robota, ostalo simulirano“ (iz snimka: „… lidar iz
    snimka …“), „Prikazuje: snimak <name> · <t s>“, „Ništa nije povezano: Poveži robota ili pokreni simulaciju u Vožnji“.
  - `blockSource(block, st, has) -> {src: 'pravo'|'sim'|'snimak'|null, reason: string|null, note: string|null}`;
    `block = {id, part: 'pogon'|'lidar'|'ir'|'mehanizmi'|null, fields: string[], notes?: {robot?: {[field]: string}}}`;
    `has(field) -> bool` (`'@lidar'` = stigao krug lidara).
  - `REASONS` po id-u bloka (tačni tekstovi iz speca): robot `robot` (skica, IR): „ESP ga još ne šalje laptopu (1 polje
    u telemetriji)“, `pid` i `enkoderi`: „Nucleo ga ne šalje (firmver)“, `napajanje`: „INA3221 nije podešen“, `aktuatori` i `ulazi`: „ESP ih
    još ne šalje laptopu“, pogon bez ijednog frame-a: „Nucleo ne javlja (nema poze)“; sim `napajanje`: „nema simulacije
    (samo pravi robot)“, sim `lidar` bez krugova: „na ESP-u: Meni → Lidar test“; snimak bez polja: „nije snimljeno“;
    ništa: „nije povezano“.
  - `lastAt(run, key, t) -> number|null`; `history(run, key, t, sec = 15) -> number[]` (null-ovi izostavljeni);
    `odoWheels(run, t0, t1, track) -> {L, R, diff}|null` (mm, iz `ox`, `oy`, `oth`; `null` ako kolona nema podataka).

- [ ] **Step 1: testovi** (izbor; tačne vrednosti)

```js
const B = { id: 'brzine', part: 'pogon', fields: ['v', 'w'], notes: { robot: { w: 'ω: ESP je još ne šalje laptopu' } } };
test('ništa', () => assert.deepEqual(blockSource(B, { session: null, sens: null }, () => false),
  { src: null, reason: 'nije povezano', note: null }));
test('robot bez Nucleo-a: pogon nepovezano', () => {
  const r = blockSource(B, { session: { kind: 'robot' }, sens: { run: emptyRun } }, () => false);
  assert.equal(r.src, null); assert.equal(r.reason, 'Nucleo ne javlja (nema poze)');
});
test('robot sa v bez w: pravo + napomena', () => {
  const r = blockSource(B, robotSt, k => k === 'v');
  assert.equal(r.src, 'pravo'); assert.equal(r.note, 'ω: ESP je još ne šalje laptopu');
});
test('hibrid: lidar pravo, ostalo sim; lidar iz snimka = snimak', () => {
  const L = { id: 'lidar', part: 'lidar', fields: ['@lidar'] };
  assert.equal(blockSource(L, { session: { kind: 'sim', lidar: 'robot' } }, () => true).src, 'pravo');
  assert.equal(blockSource(L, { session: { kind: 'sim', lidar: 'file' } }, () => true).src, 'snimak');
  assert.equal(blockSource(B, { session: { kind: 'sim', lidar: 'robot' } }, () => true).src, 'sim');
});
test('SIM napajanje', () => assert.equal(blockSource({ id: 'napajanje', part: null, fields: ['bat'] },
  { session: { kind: 'sim' } }, () => false).reason, 'nema simulacije (samo pravi robot)'));
test('snimak pušten: snimak ili nije snimljeno', () => {
  const st = { session: null, sens: { replay: true, name: 'x', t: 3 } };
  assert.equal(blockSource(B, st, () => true).src, 'snimak');
  assert.equal(blockSource(B, st, () => false).reason, 'nije snimljeno');
});
test('snimak učitan, nije pušten: uživo (ništa)', () =>
  assert.equal(viewMode({ session: null, sens: { replay: false, name: 'x' } }).mode, 'nista'));
test('odoWheels: pravo 500 mm', () => {   // frame-ovi ox 0→500, oy 0, oth 0
  const r = odoWheels(runOf([[0, 0, 0, 0], [1, 500, 0, 0]]), 0, 1, 286);
  assert.ok(Math.abs(r.L - 500) < 1e-6 && Math.abs(r.R - 500) < 1e-6 && Math.abs(r.diff) < 1e-6);
});
test('odoWheels: okret u mestu +90°', () => {
  const r = odoWheels(runOf([[0, 0, 0, 0], [1, 0, 0, 90]]), 0, 1, 286);
  assert.ok(Math.abs(r.L + 224.62) < 0.05 && Math.abs(r.R - 224.62) < 0.05);
});
```

`odoWheels`: za svaki par susednih frame-ova u (t0, t1]: `ds = dx·cos θ̄ + dy·sin θ̄`, `dθ` u radijanima svedeno na
±π, `L += ds − dθ·track/2`, `R += ds + dθ·track/2`; `diff = L − R`.

- [ ] **Step 2:** → FAIL. **Step 3:** implementacija. **Step 4:** → PASS.
- [ ] **Step 5: Commit** `Senzori: oznaka izvora i razlozi, vrednosti iz snimka, enkoderi iz odometrije (čisti moduli)`

### Task 7: Panel Senzori, spisak blokova, detalj, most iz `app.js`

**Files:**
- Create: `studio/web/senzori/blokovi/index.js` (spisak i mesto: `slot: 'top'|'sketch'|'right'|'bottom'`),
  `studio/web/panels/senzori.js` (paneli `senzori-alati` region `tool` i `senzori` region `main`,
  `when: st => st.sensOpen !== 'lidar'`), CSS `.sz-*` u `studio/web/style.css`
- Modify: `studio/web/panels/index.js` (uvoz), `studio/web/app.js` (`bridgeSens()`; `store.set({ profile: info.profile })`
  posle `/api/info`)
- Delete: `studio/web/panels/test-dela.js` (lidar je u detalju, isti paneli)
- Test: Create `studio/tests/js/senzori-blokovi.test.mjs`

**Interfaces:**
- Consumes: `viewMode`, `blockSource`, `podaci.*` (Task 6); `sensOpen` (Task 5).
- Produces:
  - modul bloka (podrazumevani export): `{id, name, part, fields, notes?, hints: string[], slot,
    view(d) -> {status: 'ok'|'warn'|'none', text: string, vals: [string, string][]},
    draw?(g, w, h, d, big), html?(d, big) -> string, actions?(d) -> [{label, run()}]}` gde je
    `d = {st, run, t, src, profile}`.
  - `BLOCKS` (redom): `lidar`(top), `robot`(sketch), `brzine`, `pid`, `napajanje`(right), `aktuatori`, `enkoderi`,
    `ulazi`, `mec`, `veza`(bottom). U ovom tasku svaki blok postoji kao modul sa `view` i bez `draw` (prazan prikaz
    + razlog); crtanje dolazi u Fazi D.
  - store `sens = {run, t, replay: bool, name: string|null}`: `bridgeSens()` se zove iz `show()` i posle `appendRun`
    sesije, najviše 10 puta u sekundi; u sesiji `t = run.duration`, `replay = false`.
  - store `profile` = `info.profile` (body, drive, odometry, ir, lidar, ir_sensors).

- [ ] **Step 1: testovi** — `BLOCKS.map(b => b.id)` tačno gornji redosled; svaki blok ima `hints.length > 0`,
  `name`, `slot` iz dozvoljenih; `view` za `{src: null}` vraća `status: 'none'`.
- [ ] **Step 2:** → FAIL. **Step 3:** implementacija:
  - `senzori-alati`: „Senzori“ (u detalju „← Svi senzori“ koji postavlja `sensOpen: null`) · tekst `viewMode(st).text`
    u boji izvora · kad je `mode === 'nista'` dugme **Poveži robota** (`ctx.openConnect`) · desno brojač
    „● n radi · ● n upozorenje · ○ n bez podataka“.
  - `senzori`: mreža po maketi B (kolone `minmax(0,1fr) 290px 330px`, donji red ~186 px); pločica = lampica, ime, oznaka
    (PRAVO crveno / SIM plavo / SNIMAK sivo / „nepovezano“ isprekidano), dugmad iz `actions`, telo (`draw` na canvas,
    `html`, ili razlog), red vrednosti; klik na pločicu → `sensOpen = id` (lidar: postojeći lidar paneli); detalj ostalih
    blokova u istom panelu: veliki prikaz + kartice Vrednosti, Kako proveriti, Izvor, Šta fali. Osvežavanje najviše
    10 Hz (requestAnimationFrame + prag), samo dok je prostor Senzori vidljiv. Tekstovi „Kako proveriti“: iz makete
    (`~/makete-ui/senzori/common.js`, `hints`), uz izmene iz speca (IR samo da/ne, domet točkićem).
- [ ] **Step 4:** `node --test studio/tests/js/` → PASS; `node --check` na novim fajlovima.
- [ ] **Step 5: Commit** `Senzori: panel sa blokovima (raspored B), detalj na klik, lidar detalj su postojeći paneli`

**STOP Faze C** — ručno: Alt+2 / bočna traka → Senzori; mreža sa 10 blokova i tačnim oznakama u stanjima: ništa,
SIM Live, virtuelni robot, hibrid; klik na lidar → postojeći lidar (Sesija | Snimak, Upali lidar, Snimi krugove,
slojevi) + „← Svi senzori“; klik na drugi blok → detalj; Esc = STOP; 1366×768 bez skrolovanja.

---

## Faza D · Blokovi

### Task 8: Lidar odozgo i skica robota (IR)

**Files:**
- Create: `studio/web/senzori/skica.js`; Modify: `studio/web/senzori/blokovi/lidar.js`, `studio/web/senzori/blokovi/robot.js`
- Test: Create `studio/tests/js/senzori-skica.test.mjs`; dopuna `senzori-blokovi.test.mjs`

**Interfaces:**
- Consumes: `radarView`, `radarXY`, `statsRows`, `robotLidarView` iz `core/lidar.js`; `store.lidarScan`;
  komanda `['lidar', 'on'|'off']` kao u `panels/lidar.js`.
- Produces: `sketchGeometry(profile) -> {w, len, h, irLow, irHigh, driveTrack, odoTrack, wheelD}`;
  `screenSide(robotLeft: boolean, view: 'spreda'|'pozadi') -> 1|-1` (+1 = desno na ekranu);
  `irAt(name) -> {front, left, upper}`.

- [ ] **Step 1: testovi**

```js
test('spreda je levo robota desno na ekranu, pozadi levo', () => {
  assert.equal(screenSide(true, 'spreda'), 1); assert.equal(screenSide(true, 'pozadi'), -1);
  assert.equal(screenSide(false, 'spreda'), -1);
});
test('irAt', () => assert.deepEqual(irAt('BRU'), { front: false, left: false, upper: true }));
test('geometrija iz Profila', () => {
  const g = sketchGeometry({ body: { width: 300, length: 165, height: 350 }, ir: { low_z: 40, high_z: 340 },
    drive: { wheel_track: 166, wheel_diameter: 65 }, odometry: { encoder_track: 286 } });
  assert.deepEqual([g.w, g.h, g.irLow, g.irHigh, g.odoTrack, g.driveTrack], [300, 350, 40, 340, 286, 166]);
});
test('lidar upozorenje ispod 5 Hz', () => assert.equal(lidarBlock.view(dWithHz(4)).status, 'warn'));
```

- [ ] **Step 2:** → FAIL. **Step 3:** lidar blok: radar oko robota (radi bez poze), robot, IR lampice u uglovima,
  krstić + mm za najbližu grupu; red ispod: Hz · tačaka · najbliža grupa mm·ugao · „grupe računa laptop“; `actions`:
  Upali/Ugasi lidar samo za ROBOT (siv sa razlogom iz `robotLidarView`); SIM bez krugova: uputa „na ESP-u: Meni →
  Lidar test“ (ako simulirani ESP prima `LIDAR ON` istim putem kao virtuelni robot bez izmene ESP koda, dugme i za SIM;
  inače samo uputa — zapisati koje je u izveštaju). Skica: SPREDA i POZADI jedna ispod druge, telo iz Profila, lidar
  uvek na vrhu tela, IR D/U kao lampice na `irLow`/`irHigh` u uglovima (`screenSide`), mm enkodera kod pasivnih točkova
  (±`odoTrack`/2); ispod: aktivni IR i maska; klik = detalj IR (velika skica + lista senzora).
- [ ] **Step 4:** → PASS. **Step 5: Commit** `Senzori: lidar odozgo i skica robota spreda/pozadi (IR, lidar na vrhu, enkoderi)`

### Task 9: Brzine, Regulacija (PID), Enkoderi

**Files:**
- Modify: `studio/web/senzori/blokovi/brzine.js`, `pid.js`, `enkoderi.js`; mali crtač grafika
  `studio/web/senzori/grafik.js` (linije kroz vreme, skala sama ili zadata)
- Test: dopuna `senzori-blokovi.test.mjs`

**Interfaces:**
- Consumes: `history`, `lastAt`, `odoWheels` (Task 6); store `sensZero: number|null` (vreme „Nuliraj“).
- Produces: `drawLines(g, x, y, w, h, series: [number[], color, dashed?][], {lo?, hi?, label?})`.

- [ ] **Step 1: testovi** — enkoderi `view`: `|diff| < 5` → `ok`, `|diff| ≥ 5` → `warn`; vrednosti `L`, `D`, `L − D`
  formatirane u mm sa zarezom; brzine sa `w` bez podataka na robotu imaju `note`; PID na robotu `status: 'none'`
  sa razlogom „Nucleo ga ne šalje (firmver)“.
- [ ] **Step 2:** → FAIL. **Step 3:** brzine: dva mala grafika v (mm/s) i ω (°/s), 15 s; PID: zadato isprekidano i
  stvarno za `v_ref`/`v` i `w_ref`/`w`; enkoderi: veliki brojevi L i D od „Nuliraj“ (`actions`: Nuliraj → `sensZero =
  t`), razlika L − D oko nule (±10 mm, zelena < 5), u detalju grafik sa skalom koja se širi.
- [ ] **Step 4:** → PASS. **Step 5: Commit** `Senzori: brzine, regulacija (zadato/stvarno) i enkoderi bez maksimuma`

### Task 10: Napajanje, Aktuatori, Činč i tasteri, Meč, Veza

**Files:**
- Modify: `studio/eurosim/tactics.py` (`actuator_ids() -> dict[str, int]` iz `ESP32/config.py` `ACTUATORS`),
  `studio/eurosim/server.py` (`info["actuators"]`), blokovi `napajanje.js`, `aktuatori.js`, `ulazi.js`, `mec.js`, `veza.js`
- Test: `studio/tests/test_server.py` (`test_info_actuators`), dopuna `senzori-blokovi.test.mjs`

**Interfaces:**
- Produces: `/api/info` → `"actuators": {"hvataljka": 1, "lift": 2, "ruka_l": 3, "ruka_r": 4}` (tačno iz config-a);
  store `actuators` iz `info`.

- [ ] **Step 1: testovi** — pytest: `info["actuators"] == {"hvataljka": 1, "lift": 2, "ruka_l": 3, "ruka_r": 4}`;
  node: aktuatori u SIM-u sa `act = {"1": 512}` daju red „hvataljka“ sa uglom `512 · 300 / 1023` ≈ 150°; napajanje na
  robotu i u SIM-u `status: 'none'` sa razlozima iz speca; meč iz `mec`/`match` frame-a; veza iz `linkView`.
- [ ] **Step 2:** → FAIL. **Step 3:** napajanje: baterija krupno, ≈ %, traka sa pragom, tabela kanala 5 V (logika) ·
  baterija (ulaz) · posle total stopa sa V i A, lampica „Total stop“ (sve „—“ dok nema podataka; crta se tek kad polje
  postoji); aktuatori: servo kao traka 0–300° sa iglom (vrednost 0–1023 → stepeni), pumpe kao lampice kad Profil kaže
  tip (bez tipa: ime i vrednost); činč i tasteri: lampice činč, STOP, OK, NAZAD, enkoder menija (SIM: činč iz stanja
  meča, ostalo „—“); meč: stanje, taktika, strana, vreme; veza: redovi ESP ↔ laptop, telemetrija, Nucleo ↔ ESP,
  RSSI / RAM / krug petlje sa napomenom „ESP ih još ne šalje“.
- [ ] **Step 4:** pytest i node → PASS. **Step 5: Commit** `Senzori: napajanje, aktuatori, činč i tasteri, meč, veza`

### Task 11: Snimak u Senzorima, dokumentacija

**Files:**
- Modify: `studio/web/app.js` (`sens.replay`: `true` kad puštanje krene na učitanom snimku i ostaje kroz pauzu;
  `false` na „Uživo“, kad puštanje stigne do kraja, na učitavanje drugog snimka i kad sesija krene),
  `studio/web/panels/senzori.js` (dugme **Uživo** u zaglavlju dok je `replay`), `docs/redizajn-napredak.md`,
  `studio/README.md`, `studio/tests/ui_shell.js` (Senzori umesto Test dela; ne pokretati)
- Test: dopuna `senzori-izvor.test.mjs`

**Interfaces:**
- Consumes: `viewMode`, `blockSource` (Task 6).

- [ ] **Step 1: testovi** — `viewMode({session: null, sens: {replay: true, name: 'abc', t: 42.3}}).text ===
  'Prikazuje: snimak abc · 42,3 s'`; pauziran (`replay: true`) i dalje `mode === 'snimak'`.
- [ ] **Step 2:** → FAIL. **Step 3:** implementacija; grafici u snimku: poslednjih 15 s pre kursora.
- [ ] **Step 4:** pun pytest + node → PASS.
- [ ] **Step 5: Commit** `Senzori: pušten snimak pokazuje trenutak snimka (SNIMAK, dugme Uživo); dokumentacija`

**STOP Faze D** — ručno (1366×768): svi blokovi u stanjima ništa / SIM Live (Meni → Lidar test) / virtuelni robot /
hibrid / snimak učitan (uživo) / snimak pušten i pauziran (SNIMAK) / „Uživo“; Nuliraj enkodera; detalj svakog bloka;
pravi robot (ESP bez Nucleo-a): Poveži robota → Senzori → Upali lidar.
