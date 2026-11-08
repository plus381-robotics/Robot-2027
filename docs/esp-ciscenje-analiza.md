# ESP32 kod: analiza za čišćenje i olakšavanje

Datum: 2026-11-08. Obim: `ESP32/` (main, boot, config, `lib/`, `tactics/`, `tests/`, `sim/`), `tools/*.py`,
`protocol/`, `.github/workflows/esp32.yml`, i iz simulatora samo ono što koristi ESP API
(`simulator/eurosim/esp.py`, `sim.py`, `stm.py`, `tactics.py`, `robotlink.py`, `server.py`).
Ništa nije menjano osim ovog fajla.

Oznake: **[IZMERENO]** = stvarno izmereno na laptopu (wc, veličine fajlova, `mpy-cross` 1.29.0, pytest);
**[PROCENA]** = procena iz čitanja koda (RAM na ESP-u se ovde ne može izmeriti, nema ploče ni unix
MicroPython-a). Brojevi linija se odnose na trenutno stanje repoa.

Stanje pre analize **[IZMERENO]**: `python -m pytest -q ESP32/tests/host` → **47 passed (0,53 s)**.

---

## 0. Ukratko (najvažnije)

1. **Kod nije naduvan, ali RAM jeste pun samim kodom.** Sve što se uveze pri pokretanju je
   **~49,5 KB `.mpy`** **[IZMERENO]**, a heap na WROOM-32 je ~100 KB (README: ~25 KB slobodno). Brisanje
   mrtvog koda donosi 1,5-2 KB; **frozen moduli** (kod iz fleša) bi oslobodili verovatno 35-50 KB
   **[PROCENA]**. To je najveća poluga za RAM, mnogo veća od svega ostalog.
2. **Jedan izuzetak u bilo kom servisu petlje gasi `main.py`** (pa STM32 staje posle 500 ms), a tokom
   taktike prekida taktiku kao "greska" (`runner.py:22-43`, nema `try` po servisu). Ekran, telemetrija ili
   upload ne smeju da mogu da obore meč.
3. **WDT ostaje uključen posle meča** (ne može da se ugasi do restarta), a `FLASH` (stmflash, blokira
   desetine sekundi) je posle meča dozvoljen → restart ESP-a usred flešovanja, STM32 ostaje u bootloader-u.
4. **~400 alokacija izuzetaka u sekundi u mirovanju** **[PROCENA]**: `upload.poll` (`accept`) i `telem.poll`
   (`recvfrom`) bacaju `OSError(EAGAIN)` u svakom krugu petlje. Plus po krugu: `list(self._wait)`,
   `list(self._late)`, nova lista događaja, dict literal u `app.update` (linija 129), PING okvir se
   gradi iznova svakih 150 ms. To je najveći izvor rada za GC (a na S3 sa PSRAM-om GC pauze rastu).
5. **Mrtav kod** (sigurno se ne koristi): Demo taktika (~45 linija u 5 fajlova), `ui.action_bar`,
   `pages.MARK/ICON_WARN/ICON_WAIT`, `Loop.slowest`, `Robot.frames/logs/busy`, `app.last`, `Pages.NAMES`,
   `Match.remaining`, `Number(unit, fmt)`, `Action(confirm)`, `config.BOARD`, poruke protokola
   `LIDAR_SCAN/CONTROL_DEBUG/DEBUG_STREAMS/TACTIC_EVENT` + `Debug` na ESP strani, lažni `machine.RTC`.
6. **Nove greške van PROBLEMI.md**: `tactics/x100.py` šalje sirove koordinate iz `status()` u `goto()`
   (koji ogleda) → na plavoj strani robot krene preko celog stola; "WiFi off mec" gasi WiFi mimo
   `net.py` pa se posle meča ESP verovatno prebaci u AP režim; `tools/espnet.py` šalje lozinku u čistom
   tekstu ako pozdrav ne stigne za 0,35 s; prevođenje taktike se dešava i u **crtanju ekrana PROVERA**
   (`app.tactic_ok` → `runner._compiled`), što je verovatno deo PING pauze iz PROBLEMI 6.

---

## 1. Pregled modula

### 1.1 Tabela **[IZMERENO]** (osim kolona "uloga/meč")

`lin` = sve linije, `kod` = bez praznih i komentara, `.mpy` = `mpy-cross 1.29.0` (bajtkod, isto što
`esp_push` šalje), `kl/fn` = klase / funkcije+lambda (ast).

| fajl | lin | kod | .py B | .mpy B | kl | fn | uloga | ko uvozi | u meču? |
|---|---:|---:|---:|---:|---:|---:|---|---|---|
| main.py | 75 | 60 | 2933 | 1236 | 0 | 4 | sklapanje, glavna petlja | firmver | DA |
| boot.py | 4 | 2 | 168 | 88 | 0 | 0 | `sys.path` | firmver | DA (vidi 6.8) |
| config.py | 31 | 13 | 1315 | 518 | 0 | 0 | pinovi, aktuatori | svi | DA |
| lib/app.py | 363 | 312 | 15889 | 7227 | 1 | 60 | stanje, provera, izveštaj, meniji | main, sim | DA (meniji samo van meča) |
| lib/compat.py | 26 | 18 | 773 | 377 | 0 | 5 | vreme ESP/laptop | svi | DA |
| lib/inputs.py | 132 | 105 | 5119 | 1751 | 3 | 9 | enkoder (hard IRQ), tasteri | main, sim | DA |
| lib/link.py | 94 | 77 | 2538 | 886 | 1 | 7 | COBS + CRC16 | robot, stm sim | DA |
| lib/match.py | 117 | 97 | 4471 | 2018 | 1 | 9 | tok meča, WDT, read_meta | app, runner, sim | DA |
| lib/net.py | 84 | 72 | 3270 | 1275 | 1 | 4 | WiFi STA/AP, WebREPL | main, rescue | DA (ili ugašen) |
| lib/pages.py | 486 | 399 | 17068 | 8207 | 9 | 52 | 7 stranica ekrana | app | DA |
| lib/protocol.py | 97 | 84 | 2567 | 1844 | 4 | 2 | generisano iz yaml | robot, tac, match, tekst, pages | DA |
| lib/rescue.py | 49 | 42 | 1462 | 768 | 0 | 2 | rescue režim | main (lenjo) | ne (samo pri padu) |
| lib/robot.py | 168 | 141 | 7596 | 2303 | 1 | 9 | veza sa STM32 | main, sim | DA |
| lib/runner.py | 114 | 96 | 3979 | 1602 | 1 | 7 | Loop, run_tactic | main, app, sim | DA |
| lib/screen.py | 13 | 10 | 475 | 341 | 0 | 0 | I2C + SSD1306 | main, rescue | DA |
| lib/settings.py | 37 | 32 | 1451 | 582 | 1 | 2 | settings.json | main, sim | DA |
| lib/state.py | 4 | 3 | 149 | 84 | 0 | 0 | MODE/IP/SSID | net, app, pages, upload, telem | DA |
| lib/stmflash.py | 212 | 182 | 7563 | 3109 | 2 | 14 | flešovanje STM32 | upload (lenjo) | ne (razvoj) |
| lib/tac.py | 297 | 212 | 10544 | 3573 | 1 | 26 | API taktika | main, runner, match, app, sim | DA |
| lib/tactic.py | 102 | 76 | 3460 | 1298 | 2 | 12 | tracker + Demo | app, pages, tac, runner, telem | DA (Demo mrtav) |
| lib/tekst.py | 30 | 16 | 1147 | 785 | 0 | 3 | natpisi | app, pages | DA |
| lib/telem.py | 74 | 65 | 2579 | 1288 | 1 | 3 | UDP 8268 JSON | main, sim | razvoj (učitan uvek) |
| lib/ui.py | 549 | 439 | 18384 | 6934 | 11 | 73 | meni, crtanje, poruke | app, pages | DA |
| lib/upload.py | 518 | 434 | 17373 | 7174 | 1 | 39 | TCP 8267 server | main, rescue, sim | razvoj (+LOG/STOP/STAT u meču) |
| tactics/primer.py | 19 | 12 | 905 | 376 | 0 | 0 | primer | runner (exec) | - |
| tactics/provera.py | 7 | 5 | 194 | 180 | 0 | 0 | provera veze | runner | - |
| tactics/x100.py | 20 | 13 | 735 | 468 | 0 | 0 | probna vožnja | runner | - (ima grešku, 2.4) |
| **UKUPNO** | **3722** | **3017** | **134107** | **56292** | 41 | 342 | | | |

Zbirovi **[IZMERENO]**:
- `lib/` = **3566 linija**, **53 426 B `.mpy`**.
- Uvozi se pri pokretanju (sve osim `stmflash`, `rescue`): **49 549 B `.mpy`** (+ `main.py` 1236 B).
- Razvojni kod koji je ipak stalno u RAM-u: `upload` 7174 + `telem` 1288 = **8,3 KB `.mpy`**.
- Ostalo u repou: `ESP32/sim/` 422, `ESP32/tests/host/` 740, `ESP32/tests/goto_test.py` 81, `tools/` 371 linija.

### 1.2 RAM uticaj **[PROCENA]**

- Učitan `.mpy` u RAM zauzima otprilike koliko i fajl (bajtkod + tabele qstr-ova + objekti funkcija i
  klasa), često i više. Dakle ~50 KB od ~100 KB heap-a je sam kod. Ovo se slaže sa README ("heap ~25 KB
  slobodno") i sa plan-esp.md ("RAM je tesan... ne dodavati velike module").
- Najveći: `pages` 8,2 KB, `app` 7,2 KB, `upload` 7,2 KB, `ui` 6,9 KB, `tac` 3,6 KB (4 modula ≈ 60 %).
- Velike strukture u RAM-u u radu: `upload.rbuf` 2048 B (namerno, bez alokacija pri prijemu),
  `ui._shown` 1024 B (kopija slike), `ssd1306` bafer 1024 B, `link.FrameParser.buf` do 512 B,
  `runner._code` (prevedene taktike, **nikad se ne briše**, vidi 4.5), `tracker.history` 20 n-torki,
  `app.log` 40 stringova, `app.errors` 30, `app.report` (dict sa `steps_list`), `upload._sha_cache`
  (po fajlu: put + 2 int + sha 64 znaka ≈ 150-200 B × ~30 fajlova ≈ 5 KB).
- Stringovi **[IZMERENO]**: ni komentari ni docstring-ovi ne ulaze u `.mpy` (funkcija sa docstring-om od
  2000 znakova: 35 B `.mpy`, bez njega 34 B). Dakle docstring-ove ne treba brisati radi RAM-a.
  `mpy-cross -O3` (izbacuje brojeve linija, pa traceback nema linije): `lib/` 53 426 → 49 832 B (−3,6 KB,
  −7 %). Ne preporučuje se za razvoj (greške bez linija), može za "takmičarski" build.

---

## 2. Mrtav ili neiskorišćen kod

Provereno grep-om kroz `ESP32/lib`, `main.py`, `tactics/`, `tools/`, `simulator/eurosim/`, testove i
`ESP32/sim/` (skripta je tražila svako ime definisano u `lib/` koje se pojavljuje samo jednom).

| # | Šta | Gde | Koristi se? | Predlog | Rizik |
|---|---|---|---|---|---|
| D1 | **Demo taktika** (`Demo`, `tracker.demo`, `app.demo`, `set_demo`, podešavanje `demo`, "DEMO" u naslovu) | `tactic.py:75-102` (klasa), `:26`; `app.py:16,47-48,119-120,334-339,357`; `settings.py:11`; `pages.py:483-484` | Samo iz menija (prikaz bez robota). Nema testa, simulator je ne koristi (ima pravi ekran). | **Ukloniti.** Simulator + `sim/render.py` pokrivaju "kako izgleda ekran". | Nizak. Stari `settings.json` ima ključ `demo`: `Settings.update` ga samo nosi dalje, bez greške. README pominje "demo taktika". |
| D2 | `rotate = turn_to` (stari alias) | `tac.py:23,237` | `tactics/x100.py:17`, `tests/host/test_tac.py:12`. Simulator ga obrađuje generički (`tactics.py` "aliases"), a `simulator/tests/test_tactics.py:22` ga proverava. | **Ukloniti** posle prepravke `x100.py` i testa na `turn_to`. | Nizak: stara taktika na ESP-u sa `rotate` → NameError → taktika se prekine kao "greska" (main ostaje). |
| D3 | `LIDAR_SCAN`, `CONTROL_DEBUG`, `DEBUG_STREAMS`, `Debug`, `TACTIC_EVENT` | `protocol.py:26-28,59,66-67,69` | ESP ih nikad ne šalje ni ne obrađuje. `DEBUG_STREAMS` postoji u BlackPill `comm.c:234` i u `simulator/eurosim/stm.py:215`. `TACTIC_EVENT` (e2h) nikad nije implementiran (telemetrija je JSON). | Na ESP strani: `gen.py` da preskače `dir: e2h` i poruke označene `esp: false`/`reserved`; `LIDAR_SCAN` obrisati u protokolu v3 (lidar ide na ESP, faza4 L-1). | Nizak. Treba usaglasiti sa BlackPill `protocol.h` (CI proverava `git diff`). ~300-400 B `.mpy`. |
| D4 | `ENTER_BOOTLOADER` + `stmflash.py` + `FLASH` u upload-u + `robot.can/FEATURES` | `stmflash.py` (212), `upload.py:290-365`, `robot.py:24,65-67`, `tools/flash_stm32.py` | Da, za flešovanje BlackPill-a preko WiFi-ja. Uvozi se lenjo (RAM samo kad se koristi). | **Zadržati** kao razvojni alat (na S3 dobija NRST/BOOT0 i postaje pouzdaniji). Ispraviti WDT problem (5.2). Ako vlasnik želi minimum: izbaciti (−250 linija ESP, −50 tools). | Uklanjanje: gubi se flešovanje bez kabla. |
| D5 | Rescue režim | `rescue.py`, `main.py:63-75` | Da, pri padu (test `test_rescue_rezim`). Lenjo. | **Zadržati.** Mali, ključan za popravku bez kabla. Napomena: zavisi od `net.py` i `upload.py`; ako je baš jedan od njih pokvaren, rescue ne pomaže (samo USB). | - |
| D6 | WebREPL | `net.py:78-84` | Pokreće se uvek posle WiFi-ja (Thonny preko WiFi-ja). `webrepl_cfg.PASS` je i lozinka upload-a. | **Prebaciti pod `config.WEBREPL = False`** (podrazumevano isključeno). Drži socket i bafere u RAM-u i dodatni otvoren port. Lozinku ostaviti u `webrepl_cfg.py` (ili preimenovati u `secrets.py` kasnije; tools i simulator čitaju `webrepl_cfg.py`). | Nizak. Ko koristi Thonny preko WiFi-ja, uključi opciju. |
| D7 | AP režim (sopstvena mreža) | `net.py:54-61`, `ui.ICON_AP`, `app.py:71-72`, `secrets.AP_*` | Kad nijedna poznata mreža nije dostupna. | **Zadržati, ali pod `config.WIFI_AP = True`.** U meču, ako je WiFi uključen a nema rutera, ESP pravi AP (radio aktivan); proveriti pravila Eurobota o radio emisiji. | Nizak. |
| D8 | `ui.action_bar` | `ui.py:87-91`, uvezen u `pages.py:8` | Nigde se ne zove. | Ukloniti. | Nema. |
| D9 | `pages.MARK`, `ICON_WARN`, `ICON_WAIT` | `pages.py:13-16` | `MARK` se ne koristi (`do_check` ima svoj dict, `pages.py:153`). | Ukloniti (ili koristiti `MARK` u `do_check` i izbaciti dict). | Nema. |
| D10 | `Loop.slowest` | `runner.py:45-50` | Nigde. | Ukloniti. | Nema. |
| D11 | `Robot.frames`, `Robot.logs`, `Robot.busy` | `robot.py:39,42,43,128,142,150,158` | `frames` i `logs` samo upisani; `busy` (kretanje koje traje) samo upisan (ne mešati sa `app.busy()`). | Ukloniti (LOG sa STM32 ostaje `print`). `logs` je i alokacija po LOG poruci. | Nizak. |
| D12 | `app.last` | `app.py:43`, `runner.py:85` | Samo upis. | Ukloniti. | Nema. |
| D13 | `Pages.NAMES` | `pages.py:430` | Nigde. | Ukloniti. | Nema. |
| D14 | `Match.remaining`, `App.remaining` | `match.py:116-117`, `app.py:149-150` | `Match.remaining` nigde; `App.remaining` samo iz `pages.py` (prosleđuje `tac.remaining`). | Ukloniti `Match.remaining`; u pages zvati `tac.remaining()`. | Nema. |
| D15 | `Number(unit, fmt)`, `Action(confirm)` | `ui.py:181-190`, `ui.py:140-146` | Niko ih ne prosleđuje (Confirm se pravi direktno u `pages.py:170,175`). | Ukloniti parametre/granu. | Nema. |
| D16 | `config.BOARD` | `config.py:2` | Nigde se ne čita. | Iskoristiti za izbor ploče (6.1) ili ukloniti. | Nema. |
| D17 | `tekst.version_msg(have, want)` - `want` | `tekst.py:24` | Parametar se ne koristi. | Pojednostaviti. | Nema. |
| D18 | `tekst.TAGS` BLOK / VEZA! | `tekst.py:14-15` | STM32 ih nikad ne postavlja (PROBLEMI 4). | Ostaviti dok se ne reši protokol v3. | - |
| D19 | `compat.ticks_add` | `compat.py:4,19` | Nigde (a treba: M-3, `ui.py:408` radi `ticks_ms() + ms`). | Zadržati i koristiti. | - |
| D20 | `machine.RTC` u laž. modulu | `ESP32/sim/machine.py:55-61` | Nigde. | Ukloniti, ili iskoristiti za 5.3 (nastavak posle restarta). | Nema. |
| D21 | `tools`: podrška za "stari server" | `tools/espnet.py:35-52` (lozinka u čistom tekstu kad nema pozdrava), `tools/esp_push.py:84-91` (PUT svih fajlova) | Svi ESP-ovi već imaju novi server. `esp_push` ulazi u ovu granu i kad LIST vrati `ERR taktika radi`. | **Ukloniti** obe grane: bezbednost (lozinka u čistom tekstu ako ESP kasni > 0,35 s) i jasnija greška. | Nizak. |
| D22 | `ESP32/tests/goto_test.py` | 81 linija | Ručni test na robotu, bez app-a; isto radi `tools/tactic.py x100/primer`. | Zadržati kao "golu" proveru UART-a ili obrisati; ne ide na ESP (`esp_push` ga ne šalje), CI ga samo kompajlira. | - |
| D23 | Komande upload-a `PUT` i `STAGE` | `upload.py:8-9,290-337` | `PUT`: `tools/tactic.py:31`, `simulator/eurosim/server.py:400`, testovi. `STAGE/COMMIT`: `esp_push`. | Zadržati obe (deo su istog koda, `_begin_data`). | - |

Ukupno sigurno mrtvo (D1, D2, D8-D17, D20): **~110 linija, ~1,5-2 KB `.mpy`** **[PROCENA]**.

---

## 3. Dupliranje i složenost

### 3.1 Ponovljena logika

| # | Šta | Gde | Predlog | Dobit **[PROCENA]** |
|---|---|---|---|---|
| S1 | Red koraka `(idx, ime, ok, razlog, trajanje)` crta se 3 puta skoro isto | `pages.py:255-264` (Taktika), `:292-298` (Koraci), `:405-410` (Izvestaj, prikaz 2) | Jedna funkcija `step_row(fb, y, h, short=False)`. | −15 linija |
| S2 | `Provera` ponovo implementira listanje i crtanje menija (izbor, `top`, inverzni red, klizač) | `pages.py:102-121,182-200` vs `ui.Menu.rotate/draw` (`ui.py:286-334`) | Izvući `draw_rows(fb, rows, sel, top)` u `ui.py` i koristiti u oba. | −25 linija |
| S3 | Ogledanje menja globalno `tac.current_side` pa ga vraća | `app.py:319,325` (side_menu), `match.py:84-86`, `simulator/eurosim/esp.py:180-188` | Čista funkcija `tac.mirror(side, x, y, deg)`; ista se koristi i za auto pozu (PROBLEMI 5). Simulator `Esp.mirror` može da je pozove direktno. | −10 linija, manje skrivenog stanja |
| S4 | Dva keša prevedene taktike | `app.tactic_ok` (`app.py:174-188`, `self._compiled` nije inicijalizovan u `__init__`) i `runner._code` (`runner.py:53-72`) | Jedan: `runner.check(name)` vraća `(ok, greška)` i drži samo poslednju taktiku. | −10 linija, RAM (4.5) |
| S5 | Čitanje dnevnika "od rednog broja" | `upload.c_log` (`upload.py:464-474`) i `telem.snapshot` (`telem.py:67-72`) | `app.log_since(n)`. | −5 linija |
| S6 | Obilazak fajl sistema dva puta | `upload._walk` (`:89-99`, koristi ga samo COMMIT, sinhrono) i `_list_gen` (`:397-421`) | COMMIT samo nad `/.new` (dva nivoa), bez opšteg `_walk`. | −12 linija |
| S7 | Strane terena napisane ručno | `pages.py:147` `("plava","zuta")` vs `tac.SIDES` | Koristiti `tac.SIDES`. | - |
| S8 | `app.check()` se zove 2× po crtanju PROVERA, a svaki put `os.listdir` | `pages.py:82-84` (`right`) i `:86-91` (`rows`) → `app.check` → `tactic_ok` → `tactics()` (`app.py:154-159`) | Računati `check()` jednom po crtanju; listu taktika keširati i poništiti na `PUT/COMMIT/DEL` u upload-u. | ~7 listdir/s manje |
| S9 | "Svež STATUS" sa tri različita praga | `app.check` 200 ms, `pages.Robot` 500 ms, `tac.here` 300 ms | Jedna konstanta u `robot.py` (`FRESH_MS`) + `robot.fresh()`. | jasnoća |
| S10 | Gašenje WiFi-ja u meču mimo `net.py` | `match.py:106-112` | `net.off()` / `net.on()` u `net.py` (postavlja `state.MODE`, ne pada u AP, upload/telem znaju da zatvore socket). Vidi 5.5. | ispravnost |
| S11 | `(lista + [x])[-N:]` (dve nove liste po upisu) | `app.py:88,146`, `tactic.py:57`, `robot.py:142` | `append` + `del l[0]` kad pređe N. | manje alokacija |

### 3.2 Preveliki moduli

- **`ui.py` (549)**: dva posla: crtanje i jezgro UI (`UI`, toast, alarm, spavanje, slanje slike) i
  biblioteka stavki menija (`Item`, `Sub`, `Action`, `Toggle`, `Number`, `Choice`, `Info`, `Menu`,
  `Confirm`, ~270 linija). Predlog: `ui.py` (jezgro + crtanje, ~280) i `widgets.py` (stavke + Menu + Confirm).
- **`pages.py` (486)**: posle S1/S2 ~440. Stranice su same po sebi u redu; `Provera` je najsloženija.
- **`app.py` (363)**: tri posla: stanje/provera/pokretanje (jezgro), izveštaji (`on_tactic_end`,
  `save_report`, `reports`, `load_report`, ~65 linija), meniji (`open_menu`, `tactics_menu`, `side_menu`,
  `reports_menu`, `settings_menu`, `set_demo`, ~75 linija). Predlog: `report.py` i `menus.py`.
  Meniji su ionako zaključani od NAORUZAN, pa `menus.py` može da se uveze **lenjo** (prvi dugi NAZAD).
- **`upload.py` (518)**: posle S5/S6 i bez FLASH grane (ako se `_flash` i `_begin_data` deo za FLASH
  prebace u `stmflash.py`, koji se ionako lenjo uvozi) ~440.

### 3.3 Predlog podele: jezgro za meč i opcioni moduli

```
jezgro (uvek):   main, config (+ board_*.py), compat, state, protocol, link, robot,
                 tactic (samo tracker), tac, runner, match, app (jezgro), settings,
                 inputs, screen, ui, widgets, pages, tekst, net
lenjo (van meča): menus.py   (meni podešavanja, izbor taktike/strane, Mecevi)
                  report.py  (čuvanje i čitanje /mec; čuvanje na kraju taktike može ostati u app)
razvoj (WiFi):   upload.py, telem.py  -> uvoze se samo ako WiFi radi; uz "WiFi off mec" posle
                  restarta u meču ne moraju ni da se uvezu
razvoj (lenjo):  stmflash.py (FLASH), rescue.py (pri padu)
```

Realno: pre meča se tim obično kreće kroz PROVERA → Taktike, pa se `menus.py` uveze. Dobit u RAM-u
je zato pouzdana tek uz restart pred meč (izbor taktike i strane se pamti u `settings.json`).
**[PROCENA]** jezgro bez `menus/report/upload/telem`: ~49,5 → ~38 KB `.mpy`.

---

## 4. Memorija i performanse

### 4.1 Alokacije po krugu petlje (krug ≈ 5 ms pauze + rad, ~70-150 krugova/s **[PROCENA]**)

| Mesto | Šta se alocira | Predlog |
|---|---|---|
| `upload.poll` `upload.py:169` | `accept()` na neblokirajućem socketu baca `OSError(EAGAIN)` **svaki krug** dok nema klijenta (objekat izuzetka) | `select.poll()` registrovan za server socket (i za klijent), `poll(0)` ne alocira; ili proveravati upload na 50 ms |
| `telem.poll` `telem.py:37` | `recvfrom` baca `OSError` svaki krug | isto: `select.poll` ili na 50-100 ms |
| `robot.poll` `robot.py:90` | `build_frame(P.PING, 0)` svakih 150 ms: `bytes([t,seq])`, `+`, CRC petlja, `cobs_encode` bytearray, `bytes()`, `+ b"\x00"` | PING okvir je konstantan (seq 0): `PING_FRAME = build_frame(P.PING, 0)` jednom pri uvozu |
| `robot.poll` `:98,111` | `list(self._wait)`, `list(self._late)` svaki krug (i kad su prazni) | `if self._wait:` pre petlje; iteracija bez kopije (skupljati ključeve za brisanje samo kad treba) |
| `robot.poll` `:120` | nova prazna lista događaja svaki krug | vraćati istu listu i čistiti je (`del ev[:]`) na početku sledećeg kruga, ili vratiti zajedničku praznu torku kad nema događaja |
| `link.FrameParser.feed` `link.py:78-94` | po okviru: `bytes(self.buf)`, nov `bytearray()`, u `cobs_decode` nov `bytearray` + isečci, u `parse_frame` `body[:-2]` i `body[2:-2]` | jedan stalni bafer + `memoryview`; COBS dekodiranje u mestu; CRC nad `memoryview` |
| `protocol.decode` `protocol.py:84-97` | STATUS (20 Hz): `struct.unpack` torka + `dict(zip(...))` | opciono: STATUS u postojeći dict (ali vidi rizik: `tac.status()` vraća taj dict taktici; tada vraćati kopiju) |
| `app.update` `app.py:129` | dict literal `{"NAORUZAN": ..., "POZA": ..., "MEC": ...}` **svaki krug** | modulna konstanta `WANT_PAGE = {...}` |
| `app.update` `app.py:100-104` | `"%s: %s" % ...` dvaput isto (error + toast) | jednom formatirati |
| `inputs.poll` `inputs.py:113` | `ev = []` + torke događaja | zajednička prazna torka kad nema događaja (najčešće) |
| `Loop.step` `runner.py:37-40` | nov `{}` jednom u sekundi | `clear()` dva unapred napravljena dict-a |
| `ui.tick/draw` | `self.indicators()` gradi listu (`app.py:67-76`) po crtanju; mnogo `%`-formatiranja po stranici (150-500 ms) | prihvatljivo; ikonice keširati dok se stanje ne promeni |
| `telem.snapshot` `telem.py:58-74` | 10 Hz: dict ~15 ključeva + `json.dumps` (~250 B str) + `.encode()` + lista novih redova | ok za razvoj; u meču ne slati ako niko ne sluša (već tako), ili kompaktni CSV red; **format je ugovor** sa `tools/watch.py` i `simulator/eurosim/robotlink.py` |
| `upload` `:189,207,242` | `self.out += ...`, `self.out[n:]`, `self.buf += d`: kvadratno kopiranje bajtova (LIST ~40 redova) | lista delova ili `bytearray` + indeks; samo van meča, nizak prioritet |

Gruba procena **[PROCENA]**: u mirovanju ~2 izuzetka + ~4-6 malih objekata po krugu → nekoliko stotina
objekata/s samo da bi se proverilo "ima li nečeg". Posle predloga: skoro nula alokacija dok se ništa
ne dešava. To direktno skraćuje i proređuje GC pauze (bitnije na S3, vidi 6.2).

### 4.2 Ekran

- `fb.show()` preko I2C na 400 kHz ~23-30 ms (README/plan) i šalje se samo na promenu (dobro rešeno,
  `ui.py:508-516`). T-3 iz faze 4 (800 kHz-1 MHz, slanje samo izmenjenih stranica SSD1306) bi to spustilo
  na nekoliko ms; promena je u `screen.py` (frekvencija) i drajveru.
- `ui.big()` (`ui.py:68-80`) čita piksel po piksel i crta `fill_rect` (do 512 poziva po natpisu). Za
  "miran" prikaz u meču (500 ms) je ok; na S3 nebitno.
- PROVERA crta na 300 ms i pri tome 2× `app.check()` (S8) sa `os.listdir` i, posle izbora taktike,
  **prevođenjem taktike u crtanju** (vidi 4.5).

### 4.3 CRC i COBS u Python-u

`link.crc16` (`link.py:5-12`) je petlja po bitu: STATUS okvir ~17 B × 8 = 136 iteracija, PONG takođe,
plus slanje. **[PROCENA]** nekoliko ms CPU-a u sekundi na WROOM-32. Predlozi (od jednostavnog ka brzom):
1. tabela 256 × u16 (`bytes` od 512 B ili `array('H')`) → ~8× manje rada;
2. `@micropython.viper` za `crc16` i `cobs_decode` (radi na ESP32 i S3, oba su `xtensawin`).
   Pažnja: modul sa `native/viper` kodom mora da se kompajlira sa `mpy-cross -march=xtensawin`
   (`tools/esp_push.py:38-53` i CI `esp32.yml` treba da dodaju zastavicu), a na laptopu (CPython)
   dekorator ne postoji → u `compat.py` dati lažni `micropython` modul (ili `try: import micropython`).

### 4.4 `const()` i ostalo

- `from micropython import const` za cele brojeve koji se koriste u petlji (`PING_MS`, `ALIVE_MS`,
  `ACK_MS`, `TRIES`, `HEAD`, `ROW`, `W`, `H`, `LIVE_MS`, `BUDGET`...): uz ime sa `_` na početku konstanta
  se ugradi u bajtkod i ne zauzima mesto u rečniku modula. Mala dobit (desetine bajtova po modulu),
  ali besplatna. Na laptopu: `compat.const = lambda x: x`.
- `ui.toast` `ui.py:408`: `ticks_ms() + ms` → `ticks_add` (M-3, posle ~12 dana rada wrap; sitnica).
- Ponovljeni uvozi unutar funkcija (`import state` u `upload._open`/`telem.poll` svaki krug, `import json`
  u `save_report`): uvoz već učitanog modula je samo pretraga u `sys.modules`, ali `telem.poll`
  `import state` je u svakom krugu → premestiti na vrh modula.

### 4.5 Prevođenje taktike i keš

- `app.tactic_ok()` (`app.py:174-188`) zove `runner._compiled()` → `compile()` na ESP-u. Zove se iz
  `app.check()`, a to iz **crtanja PROVERA** (`pages.py:83,89`). Dakle prvo crtanje posle izbora taktike
  (ili posle `PUT` nove verzije) prevodi taktiku u servisu "ekran": isti ~590 ms zastoj iz PROBLEMI 6, samo
  pre naoružavanja. **[PROCENA]** Prevođenje je i najveći kratkotrajni zahtev za RAM (raste heap → manje
  za WiFi drajver, isti mehanizam kao kod `lib/` pre `.mpy`).
- `runner._code` čuva prevedeni kod **svake** taktike koja je ikad proverena (`runner.py:53,71`). Čuvati samo jednu.
- Predlog (rešava i PROBLEMI 6): taktike na ESP slati kao `.mpy` (pored `.py` zbog `read_meta`), runner
  izvršava `.mpy` ako postoji (uvoz modula iz `/tactics` uz `sys.modules.pop(name)` pre i posle), inače
  `.py` kao sada (simulator i testovi rade nepromenjeno). Promene: `upload.check_path` (dozvoliti `.mpy`
  u `tactics/`), `tools/tactic.py` i `esp_push` (mpy-cross za `tactics/`), `simulator/eurosim/server.py:400`
  (šalje `PUT /tactics/<ime>.py`, ostaje ispravno jer je `.py` i dalje podržan).

### 4.6 Frozen moduli (najveća poluga za RAM)

- Na WROOM-32: zamrznuti `lib/` u firmver (`manifest.py` sa `freeze("lib")`, ESP32_GENERIC build).
  Bajtkod se izvršava iz fleša → **[PROCENA]** 35-50 KB heap-a slobodno, brže pokretanje, GC ne
  obilazi taj kod.
- Mana: izmena koda zahteva novi firmver, **osim** ako `/lib` ima prednost nad `.frozen` u `sys.path`.
  MicroPython 1.29 na ESP32 ima podrazumevano `sys.path = ['', '.frozen', '/lib']`, pa frozen pobeđuje.
  Za razvoj: u `boot.py` staviti `/lib` ispred `.frozen` (tada `esp_push` i dalje radi, a frozen je
  rezerva i za rescue). `boot.py:4` sada radi `sys.path.append("/lib")`, što je verovatno duplikat
  podrazumevanog `/lib` (proveriti `print(sys.path)` na ploči).
- Na S3 sa PSRAM-om RAM prestaje da bude problem, ali frozen i dalje ubrzava uvoz i smanjuje heap koji
  GC obilazi. Preporuka: na S3 prvo izmeriti bez frozen-a; frozen tek ako GC pauze smetaju.

---

## 5. Robusnost i bezbednost u meču

(Postojeće stavke u `ESP32/PROBLEMI.md` se ne ponavljaju; ovde su veze i novi nalazi.)

### 5.1 Izuzetak u servisu ruši sve — visoka

`Loop.step` (`runner.py:22-43`) nema `try` po servisu. Posledice:
- van taktike: izuzetak iz `ekran`, `telem`, `upload`, `net` izađe iz `main()` → `rescue.run` → nema
  PING-a → STM32 stane. Ako je meč u toku, ostatak meča robot stoji.
- u taktici: izuzetak iz servisa izađe iz `_pump()` u kod taktike → `run_tactic` ga uhvati kao
  `BaseException` → taktika prekinuta, STOP robotu (`runner.py:97-100`). Greška u crtanju ekrana gasi taktiku.

Primeri puta za neuhvaćen izuzetak: `upload._data` → `f.write`/`os.rename` (`upload.py:317,333`) nisu u
`try` (pun fleš → `OSError` iz `_step`, ne iz `_line`); stranice formatiraju `%d` nad vrednostima iz
STATUS-a/izveštaja (učitan stari `/mec/*.json` drugog oblika → `KeyError` u `Izvestaj.draw`).

**Predlog:** `Loop` da obavija svaki servis osim `robot` u `try/except Exception`, broji greške po servisu,
pamti poslednju (`app.error("ekran: KeyError")`) i nastavlja; servis koji pada stalno se gasi (npr. posle
10 grešaka). `robot` (PING) ostaje kritičan. Test: servis koji baca → petlja i PING rade dalje.

### 5.2 WDT posle meča + blokirajući poslovi — srednja/visoka

`Match.arm` pali `machine.WDT(3000)` (`match.py:57-62`); ne može da se ugasi do restarta. Hrani ga samo
`Match.update` iz petlje. Posle meča (`KRAJ`) `app.busy()` je False, pa upload dozvoljava `FLASH`,
`COMMIT`, `LIST`:
- `FLASH` blokira desetine sekundi (`stmflash.flash_file`, `sleep_ms`, sinhrono čitanje) → WDT restart
  usred flešovanja → STM32 ostaje u bootloader-u (bez `NRST/BOOT0` ne može softverski nazad).
- `COMMIT` (`upload.py:368-385`) sinhrono preimenuje sve fajlove; sa sporim FS-om može preći 3 s.

**Predlog:** `upload` odbija `FLASH`/`COMMIT` ako je `app.match.wdt` aktivan ("restartuj ESP posle
meča"), ili `log()` callback u `_flash` hrani WDT. Najjednostavnije: posle `KRAJ` i pritiska OK na
izveštaju ponuditi "restart".

### 5.3 Restart ESP-a u meču — srednja (odluka)

Posle WDT ili pada usred meča ESP se vrati, STATUS pokazuje `MATCH_RUNNING`, auto poza se pravilno ne
šalje (`app.py:107-112`), ali `Match` je `NEMA` i taktika se ne nastavlja: robot stoji do kraja.
Moguće (odluka vlasnika): upisati `(taktika, strana, t_start)` u `machine.RTC().memory()` pri NAORUZAN, a
posle restarta u meču bar prikazati alarm "RESTART U MECU" (ili namerno ne raditi ništa). Lažni
`RTC` u `ESP32/sim/machine.py` već postoji (sada neiskorišćen, D20).

### 5.4 Taktika koja ne čeka — srednja

Taktika bez `wait()`/komande u petlji (`while True: pass`) zaustavlja petlju: nema PING-a, ni ekrana,
ni **tastera STOP** (tasteri se čitaju u petlji). U meču WDT posle 3 s restartuje ESP; u testu
(`test odmah`, `RUN`) ESP visi do ručnog reseta. Simulator ovo statički upozorava (`tactics.py`).
**Predlog:** STOP taster na hard IRQ koji radi `micropython.schedule(_abort)`, a `_abort` podigne
`tac.Abort` (izuzetak iz planirane funkcije se pojavljuje u prekinutom kodu i u čistoj Python petlji).
Proveriti na ploči; host test: lažni `micropython.schedule`.

### 5.5 "WiFi off mec" mimo `net.py` — niska/srednja

`match._go` (`match.py:106-112`) gasi STA i AP direktno. `state.MODE` ostaje `"STA"`, ikonica WiFi se i
dalje crta (`app.py:73`). Posle meča (`busy()` False) `Net.poll` (`net.py:34-43`) primeti pad, krene
ponovno povezivanje na **neaktivnom** STA interfejsu (`connect` baca `OSError`, uhvaćen), prođe sve
mreže i **verovatno završi u AP režimu** (`net.py:54-61`) umesto na ruteru **[PROCENA, nije provereno na
ploči]**. Upload/telem socketi ostaju vezani za stari interfejs. **Predlog:** `Net.off()`/`Net.on()`
(postavlja `state.MODE = "OFF"`, `sta.active(True)` pri ponovnom paljenju), upload/telem zatvaraju socket
kad `state.MODE` nije STA/AP. Host test postoji za ponovno povezivanje (`test_faza3.py:145`), dodati za off/on.

### 5.6 Ostalo (novo)

- **`tactics/x100.py:6-11`**: `s = status()` su koordinate terena (sirove), a `goto()` ih tumači kao
  "našu stranu" i ogleda → na plavoj strani `goto(2750, y+100)` postane `goto(250, ...)`: robot krene
  preko celog stola. Komentar kaže "+x", a kod pomera +y. Ispravka: `x, y, _ = here()`; `turn_by(180)`
  umesto ručnog računanja ugla i `rotate`.
- **`tools/espnet.py:49-52`**: ako ESP ne pošalje pozdrav za 0,35 s (zauzet, GC, slab WiFi), klijent
  šalje **lozinku u čistom tekstu** (podrška za stari server). Ukloniti (D21).
- **`tools/esp_push.py:84`**: svaki `ERR` na LIST (npr. "taktika radi") se tumači kao "stari server" →
  pogrešna poruka i pokušaj PUT-a svih fajlova.
- **Rescue zavisi od `net.py`/`upload.py`**: ako je `secrets.py` nevažeći ili `upload.py` pokvaren,
  rescue nema WiFi (`rescue.py:28-35`); jedini put je USB. Prihvatljivo, ali dokumentovati.
- **`print` u toplim putevima** (`ui.toast`, `tlog`, LOG sa STM32; 15 `print` u `lib/`): na S3 sa
  nativnim USB-CDC proveriti da `print` ne blokira kad je kabl priključen a terminal ne čita (6.3).
- **Auto SET_POSE** (`app.py:107-112`) i PROBLEMI 5: rešava se istom čistom `tac.mirror` funkcijom (S3).
- Prevođenje u crtanju ekrana (4.5) je verovatno deo uzroka iz **PROBLEMI 6**; predlog "prevesti pri
  naoružavanju" je već delimično ispunjen (keš), ali prvo prevođenje se dešava u crtanju PROVERA.
- **PROBLEMI 8**: neispravljen komentar i dalje je u `settings.py:16` (nestaje sa D1).
- **PROBLEMI 9**: lokalno `mpy_cross` je instaliran, pa test prolazi; `importorskip` i dalje vredi dodati.

---

## 6. Priprema za ESP32-S3 (N16R8)

### 6.1 Config po pločama (S-1)

- `config.py` sada ima `BOARD = "wroom32"` koji niko ne čita (D16). Predlog: `board_wroom32.py`,
  `board_s3.py` (samo pinovi i `UART_ID`, `I2C_*`, `ENC_*`, `BTN_*`, `STM_NRST/BOOT0`, `NEOPIXEL`, `BUZZER`,
  `ESTOP`, `LIDAR_UART`), a `config.py` radi `from board_s3 import *` (ili automatski po
  `os.uname().machine`, sadrži "ESP32S3"). Ponašanje (`ACTUATORS`, `START_POSE`, `HOSTNAME`...) ostaje u `config.py`.
- **Ograničenja iz simulatora**: `simulator/eurosim/tactics.py` (`_actuators`, linije ~79-87) čita
  `ACTUATORS` iz `config.py` preko `ast` kao dodelu na vrhu fajla → `ACTUATORS` mora ostati doslovno u
  `config.py`. `simulator/eurosim/esp.py:103-108,133-147` koristi `cfg.BTN_*`, `cfg.ENC_*` → `import *` iz
  board fajla ih zadržava kao atribute `config`. `esp_push` (`local_files`) mora da šalje i `board_*.py`,
  a `upload.ALLOWED_ROOT` (`upload.py:33`) da ih dozvoli.
- S3 plan pinova (faza4): UART1 17/18, I2C 8/9, tasteri 4/5/6, enkoder 11/12/13, buzzer 14, NeoPixel 21,
  NRST 15 / BOOT0 16, E-STOP 7, UART2 47/48 (lidar). Na S3 `UART_ID = 1`.

### 6.2 PSRAM i GC (S-2)

- `main.py:38`: `gc.threshold(max(4096, gc.mem_free() // 4))`. Sa ~8 MB heap-a to je prag ~2 MB → GC
  retko, ali **dugo** (obilazak velikog heap-a u PSRAM-u, sporijem od internog SRAM-a). **[PROCENA]**
  desetine ms po `gc.collect()`; meriti.
- Predlog: prag iz board fajla (`GC_THRESHOLD`, npr. 32-64 KB na S3), `gc.collect()` u mirnim trenucima
  (posle `fb.show()` ako je krug bio kratak, i obavezno pri NAORUZAN), i merenje trajanja GC-a u `STAT`
  (`ticks_us` oko `gc.collect()`); smanjenje alokacija iz 4.1 je ovde najvažnije.
- Memorijski trikovi za WROOM (redosled uvoza u `main.py:9-20`, `upload.rbuf`, `ui._shown`) mogu da ostanu;
  ne smetaju na S3. `upload.mem()` (`esp32.idf_heap_info`) ostaje koristan.

### 6.3 USB-CDC

- `/dev/ttyACM*` umesto `/dev/ttyUSB0` u README i `goto_test.py` komentaru; `mpremote` i Ctrl+C proveriti.
- Proveriti da li `print` blokira dok je USB priključen, a niko ne čita (5.6). Ako da: `config.LOG_PRINT`
  ili `print` samo kad nije meč.

### 6.4 Enkoder (PCNT)

- `inputs.Encoder` (hard IRQ) zadržati kao rezervu; na S3 probati `machine.Encoder` (PCNT; proveriti da li
  postoji u 1.29 firmveru za S3). Isti interfejs `take()`. Izbor: `if hasattr(machine, "Encoder")`.
- `ESP32/sim/machine.py` nema `Encoder` → host testovi i simulator ostaju na IRQ putanji i
  `Esp.rotate()` (`esp.py:140-147`, koristi `Pin.handlers`) radi bez izmene. Ako se doda lažni `Encoder`,
  simulator mora da ga hrani.

### 6.5 NeoPixel i buzzer (K-1, K-2)

- Novi mali modul (npr. `lib/signal.py`): servis u `Loop`, tabela boja po stanju, upis samo na promenu,
  buzzer kao raspored u petlji (bez `sleep`). Na WROOM: `config.NEOPIXEL = None` → modul se ne uvozi.
- Za testove i simulator: lažni `neopixel.py` i `machine.PWM` u `ESP32/sim/`.

### 6.6 Ostalo za S3

- Firmver ESP32_GENERIC_S3 SPIRAM_OCT, ista verzija 1.29 (CI `mpy-cross==1.29.0.post2` ostaje).
  Bajtkod `.mpy` je isti za obe ploče; zastavica `-march=xtensawin` treba samo ako se uvede `native/viper`.
- Fajl sistem: izmeriti `listdir/stat/open` (STAT) pre odluke o kešu sha (plan-esp).
- `stmflash` sa `STM_NRST/BOOT0` postaje pouzdan; dodati "Resetuj STM32" (faza4).
- Lidar (L-1..L-3): `lib/lidar.py` kao servis; parser u `viper`; UART rxbuf veći od najdužeg kruga.

### 6.7 Šta uraditi PRE prelaska (redosled)

1. 5.1 (izolacija servisa) i 4.1 (alokacije): smanjuje GC pritisak koji će na S3 biti vidljiviji.
2. Merenja u STAT: trajanje `gc.collect()`, broj GC-a u sekundi (`gc.mem_alloc` razlike), najduži krug.
3. Board fajlovi (6.1) uz zadržavanje `config.ACTUATORS`; host test da `config` ima sve pinove.
4. README: USB-CDC, nove komande.

### 6.8 Sitnica

`boot.py:4` `sys.path.append("/lib")`: na MicroPython-u za ESP32 `/lib` je verovatno već u `sys.path`
(proveriti); ako se uvode frozen moduli, ovde se postavlja redosled (4.6).

---

## 7. Plan čišćenja u koracima

Svaki korak je mali, posle svakog: `python -m pytest -q ESP32/tests/host`, `mpy-cross` za sve (kao CI),
i `python -m pytest simulator/tests` (odvojeno, PROBLEMI 9). Linije i `.mpy` su **[PROCENA]**.

| Korak | Šta | Linije (lib) | `.mpy` | Simulator / tools | Test |
|---|---|---:|---:|---|---|
| K1 | Mrtav kod: D8-D15, D17 (action_bar, MARK+2 ikone, slowest, frames/logs/busy, app.last, NAMES, Match.remaining, Number unit/fmt, Action confirm, version_msg) | −45 | −0,6 KB | ništa (proveriti `sim.py` ne čita `robot.busy`: ne čita) | postojeći |
| K2 | Demo (D1) + komentar u settings (PROBLEMI 8) + README | −45 | −0,8 KB | ništa | postojeći |
| K3 | `x100.py` ispravka (5.6), `test_tac.py` na `turn_to`, ukloniti `rotate` (D2) | −2 (+tactics) | −50 B | `simulator/eurosim/tactics.py` radi generički, ali **`simulator/tests/test_tactics.py:22`** proverava `f["rotate"]["doc"]` → izmeniti/ukloniti tu proveru | novi: x100 na plavoj strani ide +100 u svojoj strani |
| K4 | Izolacija servisa u `Loop` (5.1) | +15 | +0,2 KB | `Esp` koristi isti `Loop` (dobija zaštitu) | novi: servis koji baca, PING ide dalje |
| K5 | Alokacije u petlji (4.1): PING konstanta, `_wait/_late` bez kopije, konstanta u `app.update`, `select.poll` ili proređivanje upload/telem, `ticks_add` u toast | ±0 | ±0 | `sim.py:129-135` ubacuje `upload.poll`/`telem.poll` kao servise: potpis ostaje isti | postojeći + test da PING okvir ostaje isti bajt-po-bajt |
| K6 | WDT i FLASH/COMMIT (5.2) | +6 | +0,1 KB | ništa | novi: FLASH odbijen dok je WDT aktivan |
| K7 | `tac.mirror(side, ...)` (S3) + auto poza po strani (PROBLEMI 5) | −10 | −0,1 KB | `simulator/eurosim/esp.py:180-188` može da zove `tac.mirror` (staro i dalje radi) | `test_faza2` |
| K8 | `check()` jednom po crtanju, keš liste taktika, jedan keš prevođenja (S4, S8, 4.5) | −15 | −0,2 KB | ništa | novi: crtanje PROVERA ne zove `os.listdir` više od jednom |
| K9 | Pages/UI deduplikacija (S1, S2, S7) | −40 | −0,8 KB | `ESP32/sim/render.py` za vizuelnu proveru (piksel-isto) | `test_ekran` + poređenje slika iz render.py pre/posle |
| K10 | `net.off/on` za "WiFi off mec" (S10, 5.5), `WEBREPL`/`WIFI_AP` u config (D6, D7) | +10 | +0,2 KB | `sim.py:125-128` postavlja `state.*` direktno: ostaje | novi u `test_faza3` |
| K11 | Upload: S5, S6, (opciono) FLASH deo u `stmflash.py` | −30 | −0,6 KB | `sim.py` koristi `Upload(app, {}, None, port=)`: zadržati potpis; `server.py:400` koristi PUT: zadržati | `test_faza3` |
| K12 | tools: D21 (stari server) | tools −20 | - | `robotlink.py` koristi `espnet.query`: potpis isti | `test_esp_push_salje_samo_izmenjeno` |
| K13 | Podela `app.py` → `menus.py` (lenjo) + `report.py`; `ui.py` → `widgets.py` | ±0 (premeštanje) | match-boot −3..−5 KB RAM ako se meni ne otvori | `esp.py:78,87` postavlja `appmod.MEC_DIR` → posle podele `report.MEC_DIR` (izmena u `esp.py` i `render.py`, `test_ekran.py:9`) | postojeći |
| K14 | Protokol: `gen.py` bez e2h/rezervisanih poruka na ESP strani (D3) | −5 (gen.) | −0,3 KB | `simulator/eurosim/stm.py:215` (DEBUG_STREAMS) koristi `P.*` iz ESP `protocol.py`: zadržati u C-u, ili i sim da preskoči | CI `git diff` protokola |
| K15 | Taktike kao `.mpy` (4.5, PROBLEMI 6) | +20 | +0,3 KB | `tools/tactic.py`, `esp_push.py`; simulator nepromenjen (`.py` putanja ostaje) | novi: runner izvršava `.mpy` ako postoji |
| K16 | Board fajlovi (6.1), GC prag po ploči (6.2) | +20 (config) | - | `tactics.py` (ACTUATORS ostaje u config.py), `esp.py` (cfg.BTN_*) | novi: `config` ima sve pinove za obe ploče |
| K17 | (opciono, kad zatreba) CRC tabela/viper, `const()`, frozen moduli | ±10 | frozen: −35..−50 KB RAM | `compat.py` lažni `micropython` za laptop | `test_link` |

Redosled: K1-K3 (čisto brisanje, bez rizika) → K4-K6 (bezbednost u meču) → K7-K11 (pojednostavljenje)
→ K12-K14 → K15-K17 (veće promene, uz merenje na robotu).

---

## 8. Brojevi

**Sada [IZMERENO]:**
- ESP kod koji ide na ploču (main, boot, config, lib, tactics): **3722 linije** (3017 bez komentara i
  praznih), **134 KB `.py`**, **56,3 KB `.mpy`**.
- Samo `lib/`: **3566 linija**, **53,4 KB `.mpy`**; uvozi se pri pokretanju **49,5 KB `.mpy`**.
- Uz ESP kod u repou: `ESP32/sim` 422, `ESP32/tests/host` 740, `goto_test.py` 81, `tools` 371 linija.
- Host testovi: 47 prolazi, 0,53 s.

**Posle čišćenja [PROCENA]:**

| Varijanta | `lib/` linije | `lib/` `.mpy` | uvozi se pri pokretanju |
|---|---:|---:|---:|
| sada | 3566 | 53,4 KB | 49,5 KB |
| K1-K12 (konzervativno, sve funkcije ostaju) | ~3400 (−5 %) | ~50,5 KB | ~46,5 KB |
| + K13 (lenji meniji/izveštaji, bez upload/telem kad je WiFi ugašen u meču) | ~3420 | ~51 KB | ~38-40 KB |
| + agresivno (bez FLASH/stmflash, AP, WebREPL; telem samo na zahtev) | ~3150 (−12 %) | ~46 KB | ~36 KB |
| + frozen moduli (K17) | isto | isto | **~0 KB bajtkoda u heap-u** |

Zaključak: linija se ne dobija mnogo, jer kod nije naduvan; dobija se **jasnoća** (bez mrtvih grana i
duplikata), **bezbednost u meču** (K4, K6, K10), **manje GC rada** (K5) i, ako treba RAM na WROOM-32,
**frozen moduli** (K17), koji vrede više od svega ostalog zajedno.
