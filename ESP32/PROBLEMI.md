# Uočeni problemi (ESP32 i veza sa STM32)

Spisak problema na koje se naišlo tokom rada na simulatoru (`simulator/`). Za svaki: šta je problem,
zašto je bitan, kako ga rešiti i kako proveriti. Osim tačke 1, ništa od ovoga još **nije ispravljeno**; izmene u
`ESP32/`, `protocol/` i STM32 kodu idu tek posle odobrenja.

Oznake: **[ESP]** kod na ESP-u, **[STM]** BlackPill (regulacija, comm), **[PROT]** protokol, **[ALAT]** alati
i testovi. Ozbiljnost: **visoka** (pogrešno ponašanje u meču), **srednja** (može da zbuni ili da izgubi
vreme), **niska** (kozmetika, čišćenje).

---

## 1. [ESP] Strane terena su obrnute u odnosu na pravila 2027 — visoka — ✅ REŠENO

**Rešeno (odobreno):** `tac.REF_SIDE = "zuta"`; komentari, README, `tools/tactic.py` i host testovi
usklađeni (ogledanje ostaje isto, menja se samo ime referentne strane). Postojeće taktike se ne menjaju:
koordinate su već bile za levu (žutu) stranu.


**Problem.** `lib/tac.py` kaže da se taktike pišu za `REF_SIDE = "plava"`, a primer taktike i
`config.START_POSE` počinju na `(250, 1000)`. Po pravilima Eurobot 2027 (dodatak G.1, slika 8) **žuta**
startna zona je na x 0..500, a **plava** na x 2500..3000 (obe y 750..1250). Dakle, taktika "za plavu" sa
x = 250 zapravo startuje u žutoj zoni, a kad se na robotu izabere "plava", robot je u tuđoj zoni.

**Zašto je bitno.** Ogledanje (x -> 3000 - x) radi ispravno, ali je ime strane zamenjeno: tim izabere
"plava" na ekranu, robot ide kao da je na žutoj. U meču to znači startnu pozu na pogrešnom kraju stola.

**Rešenje (predlog).** Taktike i dalje pisati za levu stranu (x mali), ali je nazvati pravim imenom:
- `tac.py`: `REF_SIDE = "zuta"` i komentar ("taktike se pišu za žutu, levu stranu; na plavoj se ogleda").
- `config.START_POSE` ostaje `(250, 1000, 0)` (to je centar žute zone).
- Podrazumevana strana u meniju (`app.py`: `self.side = ... or tac.REF_SIDE`) se time sama menja.
- Komentari u `tactics/*.py`, `README.md` ("Taktika se piše za **plavu** stranu") i host testovi koji
  pretpostavljaju plavu (`test_faza2.py`: "taktika pisana za plavu; na žutoj ...") — zameniti imena.

Druga mogućnost: ostaviti `REF_SIDE = "plava"` i prepisati sve taktike na x ~ 2750. Lošije, jer bi se menjale
sve koordinate, a ne samo ime.

**Provera.** Simulator: `python simulator/sim.py run primer --side zuta` treba da startuje u žutoj zoni
(x 0..500). Host testovi posle zamene imena.

---

## 2. [STM] DONE stiže dok se robot još kreće — srednja (uočeno u simulaciji, proveriti na robotu)

**Problem.** `control.c` proglašava kraj vožnje kad je `distance_proj < 5 mm` i `|v| < 2 * V_MIN` (0,3 m/s),
a kraj okreta kad je ugao u toleranciji i `|w| < 2 * W_MIN` (1,26 rad/s). Odmah tada `comm_port.c` šalje
DONE i ESP šalje sledeću komandu. U simulaciji (`primer`): DONE za GOTO stiže pri v ≈ 0,13 m/s, za okret
pri w ≈ 0,63 rad/s, za MOVE pri v ≈ -0,15 m/s; robot posle DONE pređe još ~5-10 mm ili ~0,5°.

**Zašto je bitno.** (a) `here()` odmah posle koraka vraća pozu koja nije konačna (u simulaciji
`(601, 810)`, a robot se zaustavio na `(601, 800)`); (b) sledeća komanda kreće iz kretanja, pa početni
okret ka cilju računa sa pozom koja se još menja; (c) greške se sabiraju kroz taktiku.

**Rešenje (predlog).** Jedno od:
- na STM32: posle uslova za kraj sačekati da `|v|` i `|w|` padnu ispod malog praga (npr. 0,02 m/s i
  0,05 rad/s) ili 50-100 ms, pa tek onda DONE (izmena u regulaciji, dogovor sa Lazarom);
- na ESP-u (bez izmene STM-a): u `tac._cmd` posle DONE čekati prvi STATUS sa `v == 0` (najviše ~150 ms)
  pre nego što se korak zatvori; `here()` posle kretanja tada vraća konačnu pozu.

**Provera.** Na robotu: `tools/watch.py --csv`, pogledati `sp` (v) u trenutku kad dnevnik javi "OK".
U simulatoru: brzina u trenutku DONE (snimak, polje `v`).

---

## 3. [STM] Ubrzanje nema profil: referenca brzine je odmah V_MAX — srednja (za regulaciju)

**Problem.** U `velocity_synthesis` (signal.c) grana ubrzavanja radi `clamp(abs_v_ref, v_min_acc, v_max)`,
a `V_MIN_ACC_ = 1.5` je veće ili jednako od `v_max`. `clamp` prvo proverava gornju granicu, pa za svaku
vrednost ispod `v_max` vraća `v_min_acc` (1,5), a spoljašnji `clamp` to svede na `v_max`. Posledica:
`synthesis_v` (profil sa ograničenim trzajem) se izračuna pa odbaci, i referenca brzine skoči odmah na
`v_max`. Ubrzanje tada određuje samo brzinski PID i zasićenje motora. Isto važi za okret (`W_MIN_ACC_`).

**Zašto je bitno.** Nagli start (proklizavanje točkova, greška odometrije, prevrtanje tereta), a ponašanje
zavisi od PID-a umesto od zadatog profila. Možda je namerno (brz start), ali onda je `synthesis_v` mrtav kod.

**Rešenje.** Ako je profil poželjan: `V_MIN_ACC_` postaviti na malu vrednost (npr. `V_MIN_`), isto
`W_MIN_ACC_`. Odluka je na autoru regulacije. Simulator prati C kod (isto ponašanje), pa se razlika može
videti u simulatoru menjanjem `V_MIN_ACC` u profilu.

---

## 4. [STM][PROT] Bitovi BLOCKED i LINK_LOST u STATUS-u se nikad ne postavljaju — niska

**Problem.** `protocol.yaml` ima `State.BLOCKED` (2) i `State.LINK_LOST` (16), ESP ih prikazuje
(`tekst.TAGS`: "BLOK", "VEZA!"), ali ih STM32 nikad ne postavlja: `comm_port_fill_status` puni samo
MATCH bitove, `comm.c` samo MOVING. Posle pada veze STM32 uopšte ne šalje STATUS, pa ni LINK_LOST ne
bi stigao.

**Rešenje.** Ili postaviti `BLOCKED` dok IR vidi prepreku (kad novi robot dobije senzore: `goal.obstacle`),
ili bitove označiti kao rezervisane u protokolu v3. `LINK_LOST` ima smisla samo ako STM32 šalje STATUS i
posle pada veze (npr. jedan STATUS kad se ESP vrati). Za simulator nije prepreka (prati C kod).

---

## 5. [ESP] Auto SET_POSE ne zna za stranu — niska (samo razvoj) — ✅ REŠENO

**Rešeno:** auto poza se ogleda po izabranoj strani i šalje pri svakom povezivanju STM32 (docs/esp-pregled-logike.md L27).


**Problem.** `app.update` posle povezivanja šalje `config.START_POSE` (250, 1000, 0) bez ogledanja,
nezavisno od izabrane strane. Ako robot stoji na drugoj strani, odometrija je pogrešna dok taktika ne
pozove `pose()` ili dok meč ne pošalje START pozu.

**Rešenje.** Ogledati po `self.side` (isto kao `match.py` radi za START): `tac.mirror_xy`/`mirror_deg`
sa `tac.current_side = self.side`. U meču nije bitno (START poza se šalje na činč), ali test sa ekrana
(`plava: test`) na drugoj strani počinje sa pogrešnom pozom.

---

## 6. [ESP] PING pauza pri pokretanju taktike (~590 ms) — srednja (već zapisano u plan-esp.md) — delimično rešeno

**Delimično:** taktika se sada prevodi pri naoružavanju (`match.arm`), ne na činč; za "test odmah" i dalje pri pokretanju. Izmeriti na robotu.


**Problem.** Prevođenje taktike (`runner._compiled`) na WROOM-32 traje toliko da PING pauza pređe 500 ms,
pa STM32 proglasi pad veze i stane baš na startu.

**Rešenje.** Prevesti taktiku pri naoružavanju (`match.arm` -> `runner._compiled(name)`), a ne kad činč
izađe; ili slati taktike kao `.mpy` (`esp_push`/`tools/tactic.py` već koriste mpy-cross za lib/).
Na S3 izmeriti ponovo. Simulator ovo ne vidi (prevođenje u CPython-u je trenutno).

---

## 7. [ESP] read_meta čita START samo u jednostavnom obliku — niska

**Problem.** `match.read_meta` traži red koji počinje sa `START` i parsira brojeve između zagrada. Ne radi
za `START = (250, 1000, 0)  # ...` sa izrazima (`START = (X0, Y0, 0)`), za START u više redova, niti za
`START=[...]` sa negativnim brojevima u izrazima. Tada meč krene bez START poze (samo upozorenje u dnevniku).

**Rešenje.** Dokumentovati pravilo ("START samo brojevima u jednom redu") ili proveriti pre slanja: editor u
simulatoru (faza F2) će javljati grešku ako START ne može da se pročita.

---

## 8. [ESP] Sitnice u kodu — niska

- `settings.py`: komentar `# lažna taktika na ekranu ...` je iza `screen_match` umesto iza `demo`.
- `README.md` pominje taktike "za plavu" (vidi tačku 1).

---

## 9. [ALAT] Host testovi i testovi simulatora ne mogu u istom pytest pozivu — niska

**Problem.** `ESP32/tests/host/conftest.py` i `simulator/tests/conftest.py` imaju isto ime modula, pa
`python -m pytest ESP32/tests/host simulator/tests` pada pri učitavanju. Odvojeno oba prolaze (CI ih
pokreće odvojeno). Host test `test_esp_push_salje_samo_izmenjeno` traži `mpy-cross`; bez njega pada
sa `ModuleNotFoundError` (nije greška u kodu).

**Rešenje.** Pokretati odvojeno, ili dodati `pytest.ini` sa `--import-mode=importlib` u koren repoa.
Za mpy-cross: `pytest.importorskip("mpy_cross")` u tom testu, da bez njega bude preskočen umesto pao.
