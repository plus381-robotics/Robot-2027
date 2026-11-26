# Plan: kontrolna tabla za robota (Robot kao glavni ekran), lidar svuda vidljiv

Nacrt, 2026-11-26. **Stanje: ništa još nije urađeno.** Simulator (eurosim) je do sada rastao kao alat za
simulaciju; namena aplikacije je i **upravljanje robotima i praćenje uživo**. Ovaj plan pravi od kartice Robot
glavni ekran (kontrolnu tablu), a simulacija ostaje kao poseban deo. Radi se po fazama, posle odobrenja, sa
lokalnim commit-ima. Izmene u `ESP32/` (telemetrija, nove komande) tek posle "da" za tu fazu.

---

## 0. Zašto lidar sada ne vidiš (provereno 2026-11-26 na robotu)

Robot (10.34.46.249, mreža `.`) šalje krugove lidara (33 paketa za 3 s), ali telemetrija **nema pozu**:
`ok: False`, nema `x/y`, jer STM32 nije povezan (rad na stolu).
- **Robot kartica:** krug se crta oko poze robota (`robotlink.TelemRecorder.feed_lidar`); bez poze se krug
  tiho odbaci, pa se ne vidi ništa.
- **Live sa "Lidar: robot (WiFi)":** pravi krugovi idu lidaru **simuliranog** ESP-a, a on radi samo dok je na
  ESP panelu u browseru otvoren **Lidar test**. Sam izbor izvora ne prikazuje ništa; tačke su i sitne na stolu.

Do faze A, da se lidar vidi bez izmena: Live sa "Lidar: robot (WiFi)", pa na ESP panelu u browseru dugi
BACK -> Lidar test -> klik; prikaz Top.

---

## Kako je sada

| Deo | Šta radi | Šta fali |
|---|---|---|
| **Simulate** | brza simulacija celog meča, pa puštanje | ništa bitno (alat za razvoj) |
| **Live** | simulirani robot uživo, ESP panel, protivnici, hibridni lidar | dobro za taktike |
| **Robot** | Push / Run / STOP taktike; telemetrija na stolu kao snimak | koristi raspored simulacije; malo podataka; upravljanje samo pokretanjem taktike |
| Editor, Repo, Profil | taktike, git, dimenzije robota | - |

Robot kartica dobija samo ono što šalje telemetrija (`ESP32/lib/telem.py`): pozu, brzinu, bitove stanja, korak
taktike i dnevnik. **Ne dobija:** IR, ugaonu brzinu, zdravlje veze sa STM32, krug petlje, WiFi signal, bateriju,
ekran ESP-a, stanje aktuatora. Većina toga već postoji na ESP-u (STATUS ima `w`, `ir_raw`, `ir_mask`, `uptime_ms`;
upload `STAT` ima krug petlje, PING, CRC, ponavljanja, RAM, verziju), samo se ne šalje.

---

## Predlog: Robot kao glavni ekran

```
┌ Robot: eurokik (10.34.46.249) ● povezan   STM32 ✗   WiFi -61 dBm   ESP krug 12 ms   ■ STOP ┐
├──────────────────────────────┬───────────────────────────────────────────────────────────┤
│ Sto: prava poza, lidar,      │ STANJE  x/y/θ, v, w, zastavice, vreme meča, taktika/korak  │
│ ciljevi, IR zraci            │ LIDAR   radar (radi i bez poze), Hz, najbliža tačka, snimi ●│
│ (klik = GOTO, kad je         │ IR      8 senzora uživo (raw + maska)                      │
│  dozvoljeno)                 │ ZDRAVLJE veza STM32, CRC, ponavljanja, RAM, verzija, baterija│
│                              │ UPRAVLJANJE pomeri ±100 mm / ±15°, aktuatori, IR maska, reset│
│                              │ ESP     ekran robota + tasteri (meni na daljinu)           │
│                              │ DNEVNIK ESP dnevnik, greške                                │
└──────────────────────────────┴───────────────────────────────────────────────────────────┘
```

Gore: **Robot** (podrazumevano, kontrolna tabla) | **Simulator** (Simulate, Live) | Editor. Jedan STOP,
uvek na istom mestu; Esc = STOP.

---

## Faze

### A. Lidar vidljiv odmah (samo simulator, malo)
- **A1** Robot kartica crta krugove i bez poze: poslednja poznata poza, a bez nje START, sa natpisom
  "nema poze: STM32 nije povezan".
- **A2** Live sa izvorom "robot": lidar simuliranog ESP-a se pali sam (ne mora Lidar test na ESP panelu).
- **A3** Panel **LIDAR (radar)**: pogled odozgo oko robota, uvek trenutni krug (ne zavisi od toga gde je
  robot na stolu), Hz, broj tačaka, najbliža tačka, starost poslednjeg kruga. U Live i Robot kartici.

### B. Kontrolna tabla, samo čitanje (ESP: telemetrija v2, pa UI)
- **B1** Telemetrija v2 (`telem.py`): `w`, IR raw i maska, veza sa STM32 (verzija, okvira/s, CRC, ponavljanja,
  bez odgovora), najduži krug petlje, RAM, WiFi RSSI, uptime, verzija koda. I dalje ~10 Hz; lidar ostaje
  poseban binarni paket (`lidarpkt.py`).
- **B2** Paneli: STANJE, IR (postojeća slika senzora, sada uživo sa robota), LIDAR, ZDRAVLJE, DNEVNIK.
  Radi i bez STM32 (jasno piše šta fali).
- **B3** Robot kao prva kartica; Simulate/Live u odeljku Simulator.

### C. Upravljanje (ESP: nove komande upload servera)
- **C1** Pomeranje: MOVE/ROTATE u koracima (±50/100/300 mm, ±15/90°), klik na sto = GOTO, ograničena brzina.
- **C2** Aktuatori: dugme / klizač za svaki iz `config.ACTUATORS`.
- **C3** IR maska, SET_POSE (postavi robota na START), reset ESP / STM32, podešavanja (zvuk, LED, kontrast).
- **Bezbednost:**
  - STOP uvek (dugme i Esc), i kad UI zastane.
  - Vožnja traži držanje "omogući" (deadman): bez poruke sa laptopa ~300 ms, robot staje.
  - Sve komande se odbijaju kad je robot naoružan ili meč traje (u meču robot mora biti samostalan).

### D. ESP na daljinu, alati u UI
- **D1** Ekran robota (128x64, 1 KB kad se promeni) i tasteri, isti ESP panel kao u Live: meni robota sa
  laptopa (robot zatvoren u kućištu).
- **D2** Slanje koda (`tools/esp_push.py`) i flešovanje STM32 (`tools/flash_stm32.py`) iz UI-ja; sada samo
  iz terminala.

### E. Kasnije
- **E1** Više robota (glavni robot, PAMI): lista robota, svaki sa svojim hostom i tablom.
- **E2** Snimanje pravih vožnji i poređenje sa simulacijom (isti prikaz).
- **E3** Kalibracija iz pravih vožnji (K0/K1, `docs/plan-ui-senzori-kalibracija.md`).
- **E4** Baterija preko INA3221 kad PowerBoard bude povezan (zvuk "baterija" već postoji).

---

## Redosled i odobrenja

| Faza | Šta | Gde | Odobrenje | Veličina |
|---|---|---|---|---|
| A | lidar vidljiv (bez poze, auto-start, radar panel) | simulator | - | mala |
| B | telemetrija v2 + paneli za čitanje, Robot prvi | ESP + simulator | ESP: da | srednja |
| C | upravljanje (pomeranje, aktuatori, podešavanja) | ESP + simulator | da | srednja |
| D | ekran i tasteri na daljinu, push/flash iz UI | ESP + simulator | da | srednja |
| E | više robota, snimci, kalibracija, baterija | sve | po stavci | - |

Predlog: A odmah (vidi se lidar), pa B (najveća korist: sve što robot zna na jednom ekranu), pa C kad se
dogovorimo oko bezbednosti vožnje sa laptopa.

---

## Pitanja

1. **Vožnja sa laptopa:** treba li pomeranje/GOTO sa laptopa (sto, testovi), ili samo aktuatori i čitanje?
2. **Više robota:** da li PAMI ili drugi robot imaju svoj ESP/WiFi kojim aplikacija treba da upravlja?
3. **Šta je najvažnije videti** kad robot ne radi kako treba (pored lidara i IR-a)?
