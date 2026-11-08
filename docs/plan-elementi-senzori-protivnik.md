# Plan: koraci na mapi, IR senzori, elementi igre, taktike protivnika

Nacrt, 2026-11-08. **Ništa od ovoga još nije urađeno.** Posle odobrenja se radi po fazama, sa lokalnim
commit-ima (na `main` tek kad kažeš). Izmene u `ESP32/`, `protocol/` i STM delu protokola tek posle "da" za
tu fazu; ostali kod na Nucleo-u je Lein.

Kako je sada (provereno u kodu):
- Na mapi su za svaki korak **dve** oznake: tačka gde je korak počeo (krug 42 mm sa brojem i imenom) i,
  za GOTO, cilj (prsten sa krstom, strelicom i natpisom "broj: x, y"). Brojevi se ponavljaju i preklapaju,
  natpisi su uvek uključeni (`simulator/web/view3d.js` setRun).
- IR u simulatoru: 8 senzora (napred/nazad x levo/desno x dole/gore), visine iz profila (40 i 320 mm);
  vide sve što je više od senzora, pa kamenolom (330 mm) vide i donji i gornji (`eurosim/plant.py` scan).
  Na pravom robotu (BlackPill) IR kod još ne postoji; Nucleo takođe nema IR.
- Kamenolomi su nepomerljive prepreke (3 kamena, 330 mm); robot koji udari u njih se zaglavi
  (`plant.py` collides/stuck). Ne mogu da se sklone ni promene.
- Protivnik je nepomična kutija koja se prevlači mišem; nema svoje kretanje (`sim.py` obstacles).

---

## E1. Koraci na mapi: manje i jasnije

**Problem:** posle povećanja (S5) oznake su prevelike, a nije jasno šta je šta: dve oznake po koraku, isti
brojevi na dva mesta, natpisi svuda.

**Predlog:**
- **Jedna oznaka po koraku:** samo cilj (gde robot treba da stigne). Za GOTO to je tačka cilja; za MOVE i
  okret tačka gde je robot bio na kraju koraka. Tačka gde je korak počeo se više ne crta: početak koraka
  je kraj prethodnog, a vidi se na timeline-u.
- **Mala oznaka:** krug ~22 mm u boji koraka (ista boja kao deo putanje i traka na timeline-u), broj u krugu,
  bez natpisa.
- **Natpis samo kad treba:** za korak koji je upravo u toku i kad se pređe mišem preko oznake (tooltip:
  "3. GOTO 600, 1000 · OK 1.4 s"). Izbor u Show ▾: natpisi `none / current / all` (podrazumevano current).
- **Ishod na oznaci:** obod zelen (OK), crven (neuspeh), sivi (još nije), žuti (u toku). Bez dodatnih
  prstenova.
- **Strelica ugla** samo kad je zadat završni ugao, tanka.
- **Legenda** u uglu mape (jedan red): "● cilj koraka · boja = korak · ─ putanja · ┄ nacrt iz editora ·
  ▭ odometrija".
- U tabeli STEPS kvadratić u boji koraka ispred imena, da se poveže sa mapom.
- Nacrt iz editora (ljubičasto, isprekidano) ostaje kao sada, ali iste veličine kao oznake koraka.

**Provera:** snimci ekrana primer/kamenolomi (3D i Top), UI test da je po koraku jedna oznaka i da se
natpis vidi samo za tekući korak.

---

## E2. IR senzori: gornji iznad kutija, pojedinačno paljenje iz taktike

### E2a. Visine (samo simulator, odmah)

Robot je visok najviše 350 mm, kutije (kamen 110 mm x 3) su 330 mm. Gornji senzori su planirani **iznad
kutija** (npr. 340 mm), da vide protivnika i preko kutija koje robot nosi ili gura.
- Profil: `[ir] high_z = 340` (podesivo), `low_z = 40`.
- Posledica u simulatoru: kamenolome vide samo **donji** senzori; protivnika (350 mm) vide i gornji.
- Svaki senzor dobija ime u profilu (lista umesto 2 visine), da može da se uključuje pojedinačno:

      [[ir.sensor]]
      name = "front_left_low"     # ime koje se koristi u taktici
      x = 82, y = 140, dir = 0, z = 40   # mm od centra robota, smer (0 = napred, 180 = nazad)

  Podrazumevano isti raspored kao sada (4 napred, 4 nazad, u uglovima, dole/gore). **Pitanje:** tačan broj,
  položaj i visine senzora na novom robotu (i da li ima bočnih).

### E2b. Arhitektura na robotu (za razgovor sa Leom)

Predlog:
- **Senzori su na Nucleo-u** (GPIO), Nucleo ih čita u 1 kHz petlji i **sam zaustavlja robota** kad uključen
  senzor vidi nešto ispred u smeru vožnje. Najbrža reakcija, bez čekanja na UART (PING je na 150 ms).
- **ESP preko UART-a pali i gasi svaki senzor pojedinačno** (maska) i dobija stanje svih senzora u STATUS-u,
  da taktika može da odlučuje (npr. "protivnik ispred: idi na drugi kamenolom").
- Deo protokola (moj, `comm.c`): poruka za masku, polja u STATUS-u, funkcija koju Lein IR kod zove:
  `comm_ir_enabled(i)` / `comm_ir_mask()`. Čitanje senzora i zaustavljanje u regulaciji: Lea.
- BlackPill: isto preko `comm_port.c` (već postoji `comm_port_set_obstacle(bits)`, proširuje se maskom).

**Protokol v6** (predlog; v5 sa `near` još nije flešovan):
- `IR_MASK {mask: u8}` (ESP -> STM32): bit i = senzor i sme da zaustavi robota (1 = uključen). Posle
  restarta STM32 sve je uključeno.
- `STATUS` dobija `ir_raw: u8` (šta svaki senzor vidi sada, bez obzira na masku) i `ir_mask: u8`.
- Redosled bitova = redosled senzora iz profila (isti spisak u `protocol.yaml` kao enum `Ir`:
  `FRONT_LEFT_LOW = 1, FRONT_LEFT_HIGH = 2, ...`).

### E2c. API u taktici (Gambit Micro)

```python
ir_off("low")                  # isključi donje (npr. posle kupljenja: kamen u robotu ili ispred)
goto(750, 1770)
ir_on()                        # sve ponovo uključeno
ir_off("front_left_low", "front_right_low")   # pojedinačno, po imenu iz profila
if ir_sees("front_high"):      # stanje senzora (iz STATUS-a), bez obzira na to da li je uključen
    goto(...)                  # protivnik ispred: drugi plan
```
- Grupe imena: `front`, `back`, `low`, `high`, `left`, `right` (presek: `"front_low"`), ili tačno ime.
- Na kraju taktike i na STOP: sve ponovo uključeno (bezbednost).
- **Pitanje: šta sa `near`?** v5 još nije flešovan, pa predlog: `near=True` ostaje kao skraćenica za
  "isključi donje senzore za ovu komandu i vozi sporo", a osnovno je `ir_off`/`ir_on`. Druga mogućnost:
  izbaciti `near` pre nego što ga iko koristi (jednostavnije, jedan način).
- Simulator: zraci isključenih senzora se crtaju isprekidano/sivo; na timeline-u traka "IR off" dok je
  neki senzor isključen; u nacrtu putanje (S7) natpis kad se menja maska.

**Provera:** host testovi (maska ide na STM32, vraća se na kraju i na STOP), simulator (kamenolomi bez
`near`, sa `ir_off("low")`; protivnik i dalje zaustavlja preko gornjih), `gcc -fsyntax-only` za C.

---

## E3. Elementi igre ("buntovi" = kamenolomi): menjanje i guranje

**Cilj:** testiranje naprednih taktika kad stanje na stolu nije kao na početku: neki kamenolom fali, fali
gornji kamen, pomeren je, ili ga protivnik gura.

**Model:** svaki kamenolom je gomila kamenova (lista kamenova, svaki 320 x 110 x 110 mm); visina gomile =
broj kamenova x 110. IR vidi gomilu samo ako je viša od senzora (2 kamena = 220 mm: donji vide, gornji ne).

**Ručno, u UI (pre simulacije i u Live-u):**
- Klik na kamenolom: meni **ukloni gornji kamen · ukloni ceo · dodaj kamen · okreni 90°**, prevlačenje
  mišem (kao protivnik). Dugme "vrati sve kako je po pravilima".
- Stanje stola se čuva uz snimak i u localStorage (kao protivnici), i može da se sačuva kao "scenario"
  (`simulator/scenarios/*.json`, npr. "bez kamenoloma 2", "protivnik uzeo gornje") i izabere iz liste.

**Guranje (fizika, jednostavno):**
- Kad robot ili protivnik naleti na gomilu, gomila se pomera u smeru guranja (bez prevrtanja; kamenovi
  ostaju zajedno), robot pri tome usporava (otpor podesiv u profilu: `elements.push_resist`). Gomila ne
  prolazi kroz ivicu stola ni kroz druge gomile.
- Ako je guranje isključeno (`elements.pushable = false`), ponašanje je kao sada (robot se zaglavi).

**Kasnije (E5): robot uzima kamenove.** Aktuator (npr. `hvataljka 1`) kad je gomila tačno ispred robota:
gornji kamenovi prelaze u robota (crtaju se na robotu, menjaju visinu za IR), `hvataljka 0` ih spušta
ispred. Pravila (koliko, koliko blizu) u profilu. Potrebno da bi napredne taktike imale smisla do kraja.

**Snimak:** promene elemenata su događaji u snimku (ko je pomerio, gde), pa se vide pri puštanju i na
timeline-u.

**Provera:** testovi plant/sim (guranje pomera gomilu, ne prolazi kroz zid; uklonjen gornji kamen: gornji
senzori ne vide gomilu), UI test (meni, prevlačenje, scenario).

---

## E4. Protivnik sa svojom taktikom

**Cilj:** protivnik koji se kreće (stalno ili po planu), da se proveri kako se naš robot ponaša kad mu neko
seče put, stoji ispred kamenoloma ili gura elemente.

**Predlog: taktika protivnika je fajl istim jezikom (Gambit Micro, podskup):**

```python
# simulator/opponents/patrola.py
from gambit import *
START = (2750, 1000, 180)          # koordinate terena (ne ogledaju se)
while True:
    goto(2200, 1600, speed=400)
    goto(2200, 400, speed=400)
```
- Izvršava se jednostavno (idealno kretanje sa ubrzanjem, bez STM32 i regulacije), u istom vremenu kao naš
  robot, u brzoj simulaciji i u Live-u.
- Podržano: `goto`, `move`, `turn_to`, `wait`, `log`, petlje i promenljive; `wait_until(lambda: ...)` sa
  pogledom na naš robot (`their_robot()` -> x, y) za "jurenje" ili čekanje.
- Protivnik gura elemente (E3), naš IR ga vidi, sudar sa našim robotom: protivnik stane (ne prolazi kroz nas).
- UI: kod svakog protivnika izbor taktike (ili "stoji", kao sada); u editoru se otvara i menja kao naše
  taktike; nacrt putanje i za protivnika (druga boja).
- Više protivnika (do 2 robota) i jednostavne gotove taktike: `stoji`, `patrola`, `ka_nasem_kamenolomu`,
  `nasumicno` (seme za ponovljivost).

**Alternativa:** samo tačke u UI-ju (prevuci tačke, brzina, petlja/tamo-nazad). Lakše za početak, ali ne
može da reaguje. Predlog: fajlovi kao glavni način, a "tačke iz UI-ja" generišu jednostavan fajl.

**Provera:** testovi (protivnik ide po putanji, deterministično; naš robot dobija BLOCKED kad mu protivnik
preseče put; protivnik pomeri kamenolom), UI test (izbor taktike protivnika, Live).

---

## E6. Ikonica (favicon) za Eurosim

SVG ikonica (robot odozgo, žuto/plavo, slovo E), kao `simulator/web/favicon.svg` + `<link rel="icon">`;
ista ikonica u naslovu i za "Add to home screen". Mala stvar, ide u E1.

---

## Redosled i procena

| Faza | Šta | Gde | Odobrenje | Veličina |
|---|---|---|---|---|
| E1 | koraci na mapi, legenda, favicon | simulator | - | mala |
| E2a | senzori po imenu u profilu, gornji 340 mm | simulator | - | mala |
| E3 | elementi: ukloni/dodaj/pomeri, scenariji, guranje | simulator | - | srednja |
| E4 | taktike protivnika | simulator | - | srednja |
| E2b/c | IR maska: protokol v6, ESP API `ir_off/ir_on/ir_sees`, `comm.c` | ESP, protokol, STM | **da + razgovor sa Leom** | srednja |
| E5 | robot uzima kamenove (aktuator menja elemente) | simulator | - | srednja |

Predlog: E1 + E2a odmah (brzo, vidi se odmah), pa E3 i E4 (simulator), a E2b/c kad se dogovorite sa Leom
oko senzora na Nucleo-u. U simulatoru E2c može i pre STM-a (simulirani STM32 zna masku), da se taktike pišu.

## Pitanja pre početka

1. **near:** zadržati kao skraćenicu ili izbaciti i ostaviti samo `ir_off`/`ir_on`?
2. **Senzori novog robota:** koliko ih je, gde (uglovi, sredina, bočno), na kojoj visini? Dok ne znam:
   4 napred + 4 nazad, 40 i 340 mm.
3. **Imena senzora u taktici:** engleski (`front_left_low`, `front`, `low`) kao ostale komande, ili srpski?
4. **Elementi:** da li treba odmah i E5 (robot uzima kamenove), ili prvo samo ručno menjanje i guranje?
5. **Protivnik:** koliko protivničkih robota najviše (2?), i da li treba PAMI (mali roboti)?
