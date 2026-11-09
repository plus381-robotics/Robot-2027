# Plan: gornja traka, prikaz IR senzora, kalibracija robota

Nacrt, 2026-11-08. **Odluke (posle pregleda):** U1 i U2 odobreni. Odometrija se računa ručno (bez
čarobnjaka). K2b i K3 otpadaju. Ostaje: simulacija što bliža pravom robotu u dinamici (trzaj, ubrzanje,
kašnjenje): sada **K-sync** (parametri regulacije iz C koda), a **K0 + K1** (fit iz snimka) kad robot vozi
(procena 2-3 meseca). **Ništa još nije urađeno.** Radi se posle odobrenja, lokalni commit-i; na `main` kad kažeš.

---

## U1. Gornja traka i editor: manje dugmadi, svako jedno značenje

### Šta sada zbunjuje (provereno u `simulator/web/index.html`)

| Problem | Gde |
|---|---|
| **▶ Simulate** (gore) i **▶ Run** (u editoru) rade isto (brza simulacija, Ctrl+Enter oba) | `#run`, `#edRun` |
| Izbor taktike na dva mesta: **Tactic** gore i lista fajlova u editoru | `#tactic`, `#edFile` |
| **Mode: Match / Test** gore, a u Live-u posebno **Arm match** i **Run test** | `#mode`, `#armBtn`, `#testBtn` |
| **Live** i **Robot** su dugmad koja menjaju ceo red (pojavi se 8 novih dugmadi), pa se red stalno menja | `#liveGroup`, `#robotGroup` |
| Dva STOP-a, dva Follow-a (Live i Robot), Pull cord gore i na timeline-u | |
| Desno: Save run, Saved runs…, a "compare with…" je na stolu | `#save`, `#runs`, `#cmpRun` |

### Predlog: tri zone i jedan režim rada u isto vreme

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│ Eurosim │ Tactic [kamenolomi ▾] Side [Yellow|Blue]  ✎ Editor │ [ Simulate | Live | Robot ] │ ⋯ ⎇ ⚙ │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Simulate:  [Match ▾]  ▶ Run (Ctrl+Enter)                                     poruka …             │
│ Live:      ▶ Start   Arm   Cord   Test   ■ STOP   ×1 ▾  ⏸  Follow   ■ End                          │
│ Robot:     host [eurokik.local] Connect | Push   Push & Run   ■ STOP   Follow   Disconnect          │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

- **Levo, "šta":** Tactic (jedina lista taktika; editor uvek prikazuje izabranu), Side kao prekidač
  Yellow/Blue, ✎ Editor.
- **Sredina, "kako":** tri kartice **Simulate / Live / Robot**. Ispod je drugi red, uvek iste visine, samo sa
  dugmadima izabrane kartice. Red se ne pomera, a jasno je u kom si režimu (boja kartice: Simulate plava,
  Live zelena, Robot crvena jer robot vozi).
- **Jedno dugme za pokretanje po režimu:**
  - Simulate: **▶ Run** (Match ili Test pored njega). Kad je editor otvoren, pokreće tekst iz editora,
    sačuvan ili ne; dugme Run iz editora se briše.
  - Live: Start / End, Arm, Cord, Test, STOP.
  - Robot: Connect, Push, Push & Run, STOP.
- **Desno:**
  - **⋯** meni: Save run, Load run, Compare with…, Scenarios (sada razbacani);
  - **⎇** Repo, **⚙** Profile.
- **Editor:** traka samo za fajl (Save, File ▾ sa New / Save as / Rename / Delete, 📖 Commands, auto-sim).
  Lista fajlova i Run se brišu, jer su gore.
- **Jedan STOP** (crven, uvek na istom mestu u drugom redu) za Live i Robot; Esc radi STOP u oba.
- **Prečice** u tooltip-ovima i u "?" meniju (Ctrl+Enter Run, Ctrl+S Save, Space Play, Esc STOP, Alt+klik
  tačka sa mape).
- Pull cord ostaje i na timeline-u (to je mesto gde se gleda vreme), a gore samo u Live kartici.

**Provera:** postojeći UI testovi prepravljeni na nove id-jeve, snimci ekrana pre/posle; svi tokovi (brza
simulacija, editor, Live, Robot / virtuelni robot) prolaze.

**Otvoreno:** da li ti odgovara ova raspodela, ili hoćeš da prvo vidiš 2-3 varijante kao statične slike pre
pravljenja?

---

## U2. IR senzori uživo: slika robota sa senzorima

**Tvoja ideja:** slika robota i 4 ugla, svaki ugao krug od dve polovine (F i B), uključeno/isključeno uživo.

**Predlog** (isti duh, prilagođen tome da su senzori 4 napred i 4 nazad, ne po uglovima):

```
            F1   F2   F3   F4            ◗ uključen, ne vidi ništa       (zelen obod)
           ◗    ◗    ◗    ◗              ● uključen i VIDI (zaustavlja)   (crven, pun)
        ┌─────────────────────┐          ◌ isključen (ir_off), ne vidi    (siv, isprekidan)
        │          ▲          │          ◍ isključen, ali vidi            (siv sa crvenom tačkom)
        │        robot        │
        │                     │          dužina lepeze = domet; kad vidi: do mesta pogotka
        └─────────────────────┘
           ◖    ◖    ◖    ◖
            B1   B2   B3   B4
```

- Mala SVG slika u panelu **STATE** (desno gore), odozgo, u razmeri robota iz profila.
- Svaki senzor je na svom stvarnom mestu iz profila (`ir_sensors`), kao mala **lepeza** u smeru gledanja.
  To se lakše čita od polukrugova u uglovima: vidi se i koji smer (napred/nazad), i koji je (levo/desno).
- Natpis F1..B4, a ispod jedan red teksta: "isključeni: B1 B2 B3 B4 · vidi: F2".
- **Radi u sva tri režima:**
  - snimak: stanje u tom trenutku;
  - Live: uživo;
  - Robot: iz telemetrije (treba dodati `ir_raw` i `ir_mask` u telemetriju ESP-a, vidi K0).
- **U Live-u klik na senzor ga pali/gasi**, isto što i `ir_off`/`ir_on` iz taktike (komanda IR_MASK), za
  probu bez menjanja taktike.
- **Na plavoj strani** slika pokazuje imena kako ih piše taktika (žuta), sa napomenom "plava: levo/desno
  zamenjeno", da se ne mešaju F1 i F4.
- Isto stanje i dalje na stolu (zraci).

**Provera:** UI test (stanje se menja kroz snimak kamenolomi gde je `ir_off("B")`; klik u Live-u šalje masku).

---

## K. Kalibracija robota iz interfejsa

**Cilj:** simulacija verna pravom robotu. Robot vozi poznatu kalibracionu taktiku, merenja se snimaju, a
simulator iz njih podesi profil (`simulator/profiles/robot2027.toml`). Na kraju: jedan klik
"Primeni na profil", pa (preko ⎇ Repo) svi imaju isti, izmeren profil.

**Izvodljivo je**, uz dva ograničenja:
1. **Dinamika** (ubrzanje, kašnjenje, najveća brzina, kako se završava kretanje): može automatski iz
   brzina `v` i `w` u STATUS-u (20 Hz).
2. **Odometrija** (prečnici točkova, razmak): robot sam ne zna gde je stvarno, zna samo šta misli
   (odometrija). Za to treba **spoljna mera**: metar (čovek upiše rezultat) ili ivica stola (robot je
   dodirne). Bez toga nijedna automatika ne može da nađe grešku odometrije.

### K0. Šta prvo treba (ESP, odobrenje)

- **Telemetrija za kalibraciju:** sada ESP šalje 10 puta u sekundi `x, y, th, sp, st, mm` (`lib/telem.py`).
  Potrebno: `w`, `ir_raw`, `ir_mask`, `last_seq/last_result` i **20 Hz dok traje kalibracija** (svaki
  STATUS). Pretplata `WATCH 50`; bez nje ostaje kao sada.
- **Rezerva:** ako WiFi gubi pakete, ESP dok traje kalibraciona taktika piše STATUS u RAM (oko 2000 redova x
  12 B = 24 KB, uz `gc` provera) i posle ga pošalje preko upload servera (komanda `CAL`).
- Robot panel već snima sesiju (Robot -> Disconnect ostavlja snimak), pa se to koristi.

### K1. Kalibracija pogona (dinamika): automatski

- Taktika `ESP32/tactics/kalibracija_pogon.py` (oko 60 s, na sredini stola, sve sa `ir_on`):
  - pravo napred i nazad 600 mm na 200, 500 i 900 mm/s;
  - okreti 90° i 180° levo i desno;
  - kratki pomeraji 50 mm (najmanja brzina i kraj kretanja);
  - jedan GOTO sa okretom na kraju.
- Iz snimka sa robota: za svaki korak `v(t)`, `w(t)`, trajanje i kraj (koliko posle DONE još klizi).
- **Fit:** simulator pušta istu taktiku sa profilom i menja nekoliko parametara dok se krive ne poklope.
  - Parametri: `[drive] wheel_a_max`, `motor_tau`, `wheel_v_max`; po potrebi `[control] V_MIN`, `W_MIN`.
  - Postupak: Nelder-Mead nad 3-5 parametara; jedna simulacija ~1 s, pa ~50-100 simulacija = 1-2 min, u
    pozadini.
  - Mera greške: razlika `v(t)`, `w(t)`, trajanja koraka i krajnje poze između robota i simulacije.
- **UI, Calibrate (u ⚙ Profile):** izbor snimka sa robota, ▶ Fit, pa tabela "staro → novo" i grafici
  robot/simulacija jedan preko drugog (već postoji poređenje sa referencom). Dugmad "Primeni na profil" i
  "Odbaci".
- **Provera bez robota:** virtuelni robot sa namerno pogrešnim profilom (npr. `motor_tau` 0,08), fit treba
  da nađe 0,08 ± 10 %.

### K2. Kalibracija odometrije: čarobnjak sa metrom (prvo), pa sa ivicom stola (kasnije)

**K2a, sa metrom** (jednostavno, radi odmah posle K0):
1. **Pravo 1 m:** robot vozi 1000 mm po odometriji; ti izmeriš stvarno i upišeš (npr. 992 mm). Iz toga
   ide zajednički prečnik točkova: `left_scale`, `right_scale` *= 1000 / 992.
2. **10 krugova u mestu:** robot se okrene 3600° po odometriji; ti upišeš koliko je stvarno (npr. fali 8°).
   Iz toga ide razmak točkova: `track_scale`.
3. **Kvadrat 800 mm, levo pa desno (UMBmark, Borenstein):** posle oba kruga upišeš za koliko x/y je robot
   promašio startnu tačku. Iz toga se odvoji razlika levog i desnog točka (`left_scale` / `right_scale`) od
   greške razmaka.
- Čarobnjak u UI-ju vodi korak po korak (slika šta se meri), računa i pokaže korekcije.
- Isti brojevi su potrebni i **na STM32** (prečnik i razmak odometrijskih točkova u firmveru, Lazar/Lea):
  čarobnjak ispiše vrednosti za firmver ("u kodu: prečnik 65.0 -> 65.5 mm, razmak 286 -> 287.2 mm"), pa se
  ispravlja i pravi robot, ne samo simulacija.

**K2b, sa ivicom stola** (bez metra, kasnije):
- Robot se nasloni na ivicu (vožnja unazad u zid, STM32 vidi zaglavljivanje). Tada je jedna koordinata i
  ugao poznat.
- Uradi obrazac (pravo, okreti), pa ponovo dodirne ivicu. Razlika odometrije i poznate ivice daje grešku,
  bez čoveka.
- Isti postupak služi i **pre meča i usred meča** za ponovno postavljanje poze ("reset na zidu" u taktici:
  `wall_reset("left")`). To je korisno i van kalibracije.

### K3. Ostale korisne kalibracije

| Šta | Kako | Gde se koristi |
|---|---|---|
| **IR domet i koji senzor gleda gde** | prepreka na poznatim razdaljinama ispred svakog senzora; slika iz U2 pokazuje ko vidi; upišeš na kojoj razdaljini se upali | profil `[ir] range` (po senzoru, ako se razlikuju) |
| **Trajanje aktuatora** | iz snimaka pravih taktika (ACK -> DONE po aktuatoru), automatski | profil `[actuators] ms` |
| **Kraj kretanja i klizanje** | iz K1 (koliko robot pređe posle DONE) | `[control]` tolerancije; ESP čekanje posle DONE (v4) |
| **Startna poza** | robot u startnoj zoni, uz ivice; odometrija posle `pose()` u odnosu na stvarno | provera da START odgovara mestu gde ga postavljate |
| **Veza** (PING pauze, ponavljanja) | već se meri (`ping_max`, `retries`); u izveštaju kalibracije | upozorenje pre meča |
| **Baterija** | brzine iz K1 pri punoj i praznoj bateriji; treba napon u STATUS-u (STM, protokol) | profil za "slabu bateriju" ili upozorenje |

### Koliko simulacija može da prati robota samo iz koda (odgovor)

- **Regulacija je prepisana iz C koda** (BlackPill `control.c` + `signal.c`, Lazar), korak po korak na 1 kHz:
  profil brzine sa ograničenim trzajem (J_MAX, J_MAX_STOP, J_ROT_MAX...), ograničenja V/W, uslovi za kraj
  kretanja, zaglavljivanje. Taj deo je veran **ako su brojevi u profilu isti kao u firmveru** (K-sync).
  Ista je i greška PROBLEMI 3: referenca brzine skače odmah na V_MAX, pa profil trzaja zapravo ne radi; i u
  simulatoru i na robotu.
- **Fizika robota se ne može dobiti iz koda:**
  - koliko brzo motor i drajver prate referencu (`motor_tau`) i najveće ubrzanje točka (`wheel_a_max`);
    zavise od mase, motora, baterije i trenja;
  - proklizavanje;
  - brzinski PID (`pid.c`), koji se ne prepisuje, već je zamenjen kašnjenjem prvog reda.
  
  Te vrednosti su sada procene (P). Zato se oblik kretanja i trajanje poklapaju grubo; tačno ubrzanje i
  klizanje na kraju tek posle merenja (K1).
- **Novi robot (Nucleo):** `regulacija.c` (Lea) za sada ima samo regulaciju brzine (40 redova), bez
  regulacije položaja. Kad Lea napiše svoju, simulator treba da je prepiše isto kao BlackPill (nova klasa u
  `control.py`, izbor u profilu), inače simulira BlackPill regulaciju.
- **Zaključak:** fit (K1) ima smisla tek kad robot vozi; do tada K-sync drži simulaciju u skladu sa kodom.

### K-sync (sada, malo): parametri regulacije iz firmvera

- Test u simulatoru čita dodele iz `pogon-blackpill/Core/Lib/control.c` (`V_MIN_ = 0.15;`, `J_MAX_ = 36.0;`...)
  i `comm_port.c` (`#define W_GOTO ...`) i poredi sa `[control]` u profilu. Kad Lazar promeni broj u C-u, a
  profil ostane star, test pada i kaže tačno koji broj.
- Kasnije isto za Nucleo regulaciju.

### Firmver preveden za računar (umesto K-sync i ručnog prepisivanja; kad pogon dođe na red)

- Fajlovi regulacije (`control.c`, `signal.c`, kasnije Leina regulacija na Nucleo-u) prevedu se za računar
  kao mala biblioteka (gcc, `-shared`); simulator je poziva svake 1 ms (ctypes) umesto Python prepisa
  (`eurosim/control.py`). Izmena u C kodu odmah važi i u simulaciji.
- Treba: zamene za STM32 HAL (vreme, PWM; slične onima za `gcc -fsyntax-only`), reset globalnih promenljivih
  na početku svake simulacije, C kompajler (Linux ima; za Windows CI pravi gotovu biblioteku ili je `start`
  prevodi).
- Fizika robota (motor, ubrzanje, proklizavanje) i dalje iz profila, pa fit (K1) kad robot vozi.

### Redosled za kalibraciju

K-sync (sada) -> K0 + K1 kad robot vozi (2-3 meseca). Odometrija: ručno izmereni brojevi u profil
(`[odometry]`) i u firmver.

## Ukupan redosled (predlog)

| Faza | Šta | Odobrenje |
|---|---|---|
| U1 | gornja traka i editor | - |
| U2 | slika IR senzora (snimak, Live, klik pali/gasi) | - |
| K-sync | parametri regulacije iz C koda (test) | - |
| K0 | telemetrija za kalibraciju (`w`, IR, 20 Hz), kad robot vozi | ESP: da |
| K1 | kalibracija pogona (fit iz snimka), kad robot vozi | - |

## Pitanja

1. **U1:** odgovara li raspodela (Simulate / Live / Robot kao kartice), ili prvo slike varijanti?
2. **U2:** važi li prikaz senzora kao lepeza na stvarnim mestima (umesto 4 ugla sa polukrugovima)?
3. **Kalibracija na pravom robotu:** kad otprilike imate robot koji vozi (za K0/K1/K2)? Do tada sve može da
   se napravi i proveri na virtuelnom robotu sa namerno pogrešnim profilom.
4. **Odometrija u firmveru:** ko menja prečnik i razmak u STM kodu kad čarobnjak izračuna nove (Lazar,
   Lea)? Čarobnjak može samo da ispiše brojeve.

> Ispravka (posle U2): senzori su u uglovima, po dva (donji D i gornji U), imena FLD..BRU; slika crta u svakom
> uglu veliki luk (gornji) i mali (donji), sa natpisom ugla (FL, FR, BL, BR). Skica iznad sa F1..B4 je zastarela.
