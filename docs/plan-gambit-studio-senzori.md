# Gambit Studio: prostor Senzori, veza sa robotom i novo ime

Dizajn, 2026-11-28. Nastavak redizajna UI-ja (`docs/redizajn-ui.md`, `docs/redizajn-napredak.md`; Faze 0–5.2 gotove i
na `main`). Maketa koju je korisnik prihvatio: `~/makete-ui/senzori/b.html` (van repoa; stanje makete „Robot sa svim
poljima“ pokazuje ciljni izgled, „Robot danas“ pokazuje šta robot danas stvarno šalje).

## Namera i zašto

1. **Prostor za sve senzore.** Pre meča i na treningu treba za minut videti da li svaki senzor radi, i imati detaljnu
   analizu po senzoru (npr. tačnost lidara na stolu). Treba da izgleda kao prava kontrolna tabla. Današnji prostor
   „Test dela“ ima samo Lidar (Pogon, Mehanizmi i IR su sivi), a ime „Test dela“ korisniku zvuči čudno.
2. **Veza sa robotom je bila teško nalažljiva.** Korisnik je, prvi put sa pravim lidarom, lutao: Izvori → Taktike →
   Vožnja → SIM → lidar „pravi“ → opet Izvori → negde poveži ESP. Uzrok: „povezan sa robotom“ danas znači „ROBOT sesija
   u Vožnji“, a polja za vezu su u prozoru Izvori. Korisnik se inače brzo snalazi, pa je to znak da UI nije jasan.
3. **Ime.** Alat je prerastao simulator. Zove se **Gambit Studio** (Gambit = timski sistem za taktike; API taktika već
   se zove Gambit Micro, `from gambit import *`). Folder `simulator/` postaje `studio/`.

## Ciljevi

- Prostor **Senzori** (zamenjuje „Test dela“) po rasporedu makete B, sa detaljem na klik za svaki blok.
- Svaki blok prikazuje ono što trenutno stiže na server, iz bilo kog izvora: pravi robot, simulacija, hibrid, snimak.
  Svaki blok ima **oznaku izvora** (PRAVO / SIM / SNIMAK / nepovezano). Pravo ima prednost. Deo koji nema podataka piše
  „nepovezano“ i **zašto** (šta fali: polje u ESP telemetriji, firmver Nucleo-a, INA3221 nije podešen, nema simulacije).
- **„Poveži robota“** na statusnoj traci, odasvud. Veza važi u svim prostorima dok se ne klikne „Prekini“.
- Ime **Gambit Studio** svuda gde se vidi; folder `studio/`.

## Ne-ciljevi (ovaj posao)

- Nikakve izmene na ESP-u, Nucleo-u ni u protokolu. Polja koja fale dodaju se kasnije, **jedno po jedno**, kao poseban
  posao sa posebnim odobrenjem (vidi „Kasnije“).
- Ručne komande (Pogon, Mehanizmi: vozi 20 cm, pomeri servo) nisu deo Senzora; dolaze sa Fazom 6 (ESP).
- Preimenovanje internih imena: Python paket `eurosim`, komanda `sim.py`, `~/.eurosim.json`, `~/Eurosim`,
  `EUROSIM_ROOT`, ključevi `eurosim.*` u localStorage ostaju (preimenovanje bi kolegama obrisalo podešavanja i
  izabrani repo; može kasnije, uz prenos).
- Posebna stalna veza sa robotom nezavisna od sesija (odbačeno, vidi Pristupi).

## Anti-ciljevi (neuspeh i ako „radi“)

- Neko pre meča gleda zelene lampice **simulacije** i misli da je pravi robot u redu. Izvor mora biti jasan na svakom
  bloku i u zaglavlju prostora.
- Lažni podaci: blok ne sme da pokaže nulu ili izmišljenu vrednost kad podatka nema (kao „lažna nula“ iz Faze 1);
  bez podatka je „nepovezano“ sa razlogom.
- Nešto što danas radi prestane da radi: lidar u Test dela (Sesija | Snimak, puštanje snimka u krug, Upali/Ugasi lidar,
  Snimi krugove, slojevi sirovo / van stola / grupe, domet radara, „izračunao laptop“) mora postojati i u Senzorima.
- Ponašanje pravog robota se menja (bilo šta što ESP dobija drugačije nego danas, osim postojećih komandi).

## Ograničenja

- Pravila repoa (`CLAUDE.md`): izmene tek posle odobrenog plana; samo lokalni commit-i, bez push-a dok korisnik ne
  kaže; bez Claude atribucije.
- Vanilla JS, ES moduli, bez build koraka (kao do sada); three.js / uPlot / CodeMirror su u `web/vendor`.
- Natpisi na srpskom. Ekran 1366×768 mora da radi bez skrolovanja glavnog prostora.
- Testovi: `pytest` u `studio/tests` (posle preimenovanja), `node --test studio/tests/js/`. Playwright se ne instalira
  (odluka korisnika): `ui_*.js` skripte se ažuriraju ali ne pokreću; UI se proverava ručno u browseru.
- Jedna sesija u isto vreme (SIM uživo ili ROBOT), kao danas.

## Pristupi

### Veza sa robotom („Poveži robota“)

- **a) Veza = ROBOT sesija pokrenuta sa trake. — IZABRANO.** Sesija već preživljava promenu prostora (`store.session`
  je globalan), pa je posao uglavnom premeštanje polja za vezu (`#rHost`, `#rPass`, `#rConnect`, `#rVirtual`, sada u
  prozoru Izvori) u prozorčić na traci i povezivanje Vožnje ROBOT sa tom vezom. Ograničenje: dok si povezan sa robotom
  ne možeš da puštaš SIM sesiju u Vožnji (ni danas ne možeš).
- b) Posebna stalna veza na serveru, nezavisna od sesija (Senzori bi pokazivali pravog robota dok Vožnja vrti
  simulaciju). Odbačeno: više posla na serveru, više mesta za greške, a retko treba.

### Kako su blokovi napravljeni

- **a) Ceo dashboard je jedan panel sa svojim spiskom blokova. — IZABRANO.** Svaki blok je mali modul u
  `studio/web/senzori/`; jedan čist modul (bez DOM-a, sa node testovima) odlučuje oznaku izvora i razlog. Raspored B
  se pravi tačno, a blokovi se kasnije doteruju jedan po jedan.
- b) Svaki blok kao poseban panel u postojećem registru (regioni glavni / bočni / donji / alati). Odbačeno: raspored B
  (uska kolona sa skicom, desna kolona, donji red) i detalj preko cele površine se ne uklapaju u te regione.

## Dizajn

### 1. Preimenovanje (prvi, poseban commit)

- `git mv simulator studio`. Ažurirati sve putanje: `.github/workflows/simulator.yml` (putanje i komande; ime
  workflow-a po izboru graditelja), `start.sh`, `.gitignore` (`/studio/.venv/`), README-i, komentari u `ESP32/`
  (samo komentari, bez promene koda), `docs/` gde se pominje putanja za pokretanje, testovi.
- Prepoznavanje repoa (`eurosim/paths.py` `_is_repo`, `eurosim/repo.py`): repo je Robot-2027 ako ima
  `ESP32/lib/tac.py` i `studio/`. Ako folder ima stari `simulator/` (klon koji još nije povučen), poruka kaže „povuci
  najnovije (git pull)“. `SHARED` u `repo.py` postaje `studio/profiles`. `paths.WEB` (i spakovani izvršni fajl) prati
  novu putanju.
- **Prenos lokalnih podataka:** fajlovi koji nisu u gitu u starom `simulator/lidar/` (snimci krugova) i, ako postoje,
  u `simulator/runs/`, `simulator/scenarios/`, `simulator/opponents/`, `simulator/profiles/` aplikacija pri pokretanju
  jednom premesti u isto mesto pod `studio/` (ne prepisuje postojeće fajlove; ako ime postoji, ostavlja stari i javlja),
  i javi porukom šta je premestila. `.venv` se ne seli (`start.sh` / uv ga pravi ponovo, treba internet jednom).
- Vidljivo ime: naslov taba „Gambit Studio“, logo na vrhu bočne trake (ikonica + „Gambit / Studio“), naslov README-a,
  Pomoć, `favicon` po želji graditelja. „Eurosim“ ne sme ostati nigde gde ga korisnik vidi.
- Posle preimenovanja: `python studio/sim.py serve` i `start.sh` rade; CI prolazi.

### 2. „Poveži robota“ na statusnoj traci

- Polje **Veza** na traci:
  - bez ROBOT sesije: dugme **Poveži robota**; klik otvara prozorčić ispod trake: Host (`#rHost`), Lozinka (`#rPass`),
    **Poveži** (`#rConnect`), **Virtuelni robot** (`#rVirtual`), ✕, i rečenica „Veza ostaje dok ne klikneš Prekini, u
    svakom prostoru“. Id-jevi ostaju isti (ponašanje u `app.js` se ne prepisuje, premešta se).
  - sa ROBOT sesijom: `● host · starost veze` (boja po stanju ok / stale / lost kao danas) i malo dugme **Prekini**.
- **Vožnja ROBOT:** „▶ Pokreni sesiju“ više ne vodi u Izvori; bez veze otvara isti prozorčić sa trake, sa vezom
  koristi postojeću sesiju (Pošalji, Pošalji i pokreni…).
- **Izvori** ostaju samo za mešanje (hibrid: lidar sa robota ili iz snimka uz simulaciju). Host i lozinka za pravi
  lidar u hibridu se uzimaju iz istih polja (sada na traci).
- **Senzori** bez ikakve sesije u zaglavlju imaju i veliko dugme **Poveži robota** (isti prozorčić).
- Ako je u toku SIM sesija, „Poveži robota“ objašnjava da prvo treba „Završi“ (jedna sesija u isto vreme).

### 3. Prostor Senzori (zamenjuje „Test dela“)

- Stavka u bočnoj traci: **Senzori**, ikonica merača, Alt+2, na mestu „Test dela“. Podkartice Lidar · Pogon ·
  Mehanizmi · IR nestaju (IR je u Senzorima, Pogon i Mehanizmi dolaze sa Fazom 6).
- **Red ispod trake:** „Senzori“ · rečenica šta se prikazuje („Prikazuje: pravi robot · host“, „simulacija (Vožnja SIM)
  · ovo nije pravi robot“, „hibrid · lidar sa pravog robota, ostalo simulirano“, „snimak …“, ili „Ništa nije povezano:
  Poveži robota ili pokreni simulaciju u Vožnji“ + dugme) · desno brojač „● n radi · ● n upozorenje · ○ n bez podataka“.
- **Raspored (maketa B), 1366×768:**

```
┌──────────────────────────────┬──────────────┬───────────────────┐
│ Odozgo · lidar  [Upali lidar]│ Robot · IR   │ Brzine v i ω      │
│  radar oko robota, robot,    │  SPREDA      ├───────────────────┤
│  IR lampice u uglovima       │  (skica)     │ Regulacija (PID)  │
│                              │  POZADI      ├───────────────────┤
│ Hz · tačaka · najbliža grupa │  (skica)     │ Napajanje INA3221 │
├──────────────┬────────┬──────┴──┬──────────┴──┬────────────────┤
│ Aktuatori    │Enkoderi│Činč i   │ Meč i       │ Veza i zdravlje│
│ servo · pumpe│        │tasteri  │ taktika     │                │
└──────────────┴────────┴─────────┴─────────────┴────────────────┘
```

  Kolone otprilike `1fr · 290px · 330px`, donji red ~186 px; tačne mere su na graditelju, uz uslov da sve stane na
  1366×768.
- **Klik na blok** otvara detalj preko cele površine: „← Svi senzori“, lampica, ime, oznaka izvora, stanje; veliki
  prikaz; desno kartice **Vrednosti**, **Kako proveriti** (koraci za ručnu proveru), **Izvor**, i kad fali podatak
  **Šta fali**. Esc i dalje znači STOP (ne zatvara detalj).

#### Oznaka izvora i „nepovezano“

- Jedan čist modul (npr. `web/senzori/izvor.js`, bez DOM-a, node testovi) za svaki blok vraća
  `{src: 'pravo'|'sim'|'snimak'|null, reason, note}` iz: vrste sesije, `hello.source.parts` (pogon, lidar, ir,
  mehanizmi, protivnici) i toga da li polja koja blok traži stvarno stižu u podacima.
- Pravo ima prednost: kad deo dolazi sa robota, blok pokazuje robota. U hibridu lidar je PRAVO, ostalo SIM.
- Razlozi su kratki i konkretni, npr. „ESP ga još ne šalje laptopu (1 polje u telemetriji)“, „Nucleo ga ne šalje
  (firmver)“, „INA3221 nije podešen“, „nema simulacije (samo pravi robot)“, „nije povezano“.
- Ako polje dođe kasnije (posle ESP izmene), blok ga sam prikaže bez izmene bloka; menja se samo tabela razloga.

#### Snimak u Senzorima (odluka korisnika)

- **Snimak je samo učitan (nije pušten):** Senzori prikazuju uživo (sesija koja radi, ili „Ništa nije povezano“).
- **Snimak je pušten** (puštanje na vremenskoj liniji krenulo): Senzori pokazuju šta su senzori javljali u tom trenutku
  snimka, svaki blok sa oznakom SNIMAK (ili nepovezano ako taj deo nije snimljen, npr. struja u SIM snimku).
  Zaglavlje: „Prikazuje: snimak <ime> · <vreme> s“ i dugme **Uživo**.
- *(odluka pri pisanju)* Pauza usred puštanja ostaje na snimku (da se trenutak može pogledati). Nazad na uživo se vraća
  dugmetom Uživo, kad puštanje stigne do kraja, ili kad se učita drugi snimak. Sesija i puštanje ne idu zajedno (Snimci
  su zaključani dok sesija radi), pa nema sukoba.
- Grafici kroz vreme (brzine, PID, enkoderi, napajanje) za snimak pokazuju poslednjih ~15 s pre kursora.
- Puštanje snimljenih krugova lidara u detalju lidara (izvor Snimak) ostaje kao danas i nezavisno je od ovoga.

#### Blokovi i odakle im podaci

| Blok | Robot danas | SIM | Šta prikazuje |
|---|---|---|---|
| **Odozgo · lidar** | da (krugovi lidara, posle Upali lidar) | da, dok je na ESP-u Meni → Lidar test (vidi ispod) | radar oko robota (radi i bez poze), robot, IR lampice u uglovima, najbliža grupa (krstić + mm); ispod: Hz, broj tačaka, najbliža grupa mm·ugao, „grupe računa laptop“; dugme Upali/Ugasi lidar (ROBOT i hibrid) |
| **Robot · IR** (skica) | IR: nepovezano (ESP ne prosleđuje) | da (`ir`, `irm`) | skica SPREDA i POZADI, jedna ispod druge; IR D i U kao lampice (samo da/ne) na pravoj visini, lidar **na vrhu** robota sa ravni skeniranja, točkovi sa mm od enkodera; ispod: aktivni senzori i maska; klik = detalj IR |
| **Brzine v i ω** | v da; ω nepovezano (ESP ne prosleđuje) | da | dva mala grafika kroz vreme |
| **Regulacija (PID)** | nepovezano (Nucleo) | da: `v_ref`/`v` i `w_ref`/`w` | zadato (isprekidano) i stvarno, za v i ω; po točku tek kad Nucleo bude slao |
| **Napajanje (INA3221)** | nepovezano (INA3221 nije podešen) | nepovezano (nema simulacije) | baterija krupno (V, ≈ %, traka sa pragom), tabela kanala 5 V (logika) · baterija (ulaz) · posle total stopa sa V i A, lampica „Total stop: otpušten/pritisnut“ (iz napona posle total stopa) |
| **Aktuatori** | nepovezano (ESP ne šalje) | da (`act`: id → poslednja vrednost) | servo (AX) kao traka 0–300° sa iglom trenutnog ugla, ↻ dok se kreće; pumpe kao lampice; imena iz `ESP32/config.py` `ACTUATORS` |
| **Enkoderi** (pasivni odometrijski točkovi) | nepovezano (Nucleo) | da: iz odometrijske poze `ox`, `oy`, `oth` na laptopu (pomeraj i okret → L/D sa `encoder_track`), ista veličina koju će Nucleo kasnije slati | pređeno od „Nuliraj“ po točku kao broj (bez maksimuma), razlika L − D oko nule (±10 mm, zelena < 5 mm), u detalju grafik koji sam širi skalu; na skici se mm pišu kod pasivnih točkova (±`encoder_track`/2), ne kod pogonskih |
| **Činč i tasteri** | nepovezano (ESP ne šalje) | činč iz stanja meča; ostalo što SIM zna | lampice: činč, STOP, OK, NAZAD, enkoder menija |
| **Meč i taktika** | da | da | stanje (spreman / naoružan / meč), taktika, strana, vreme meča |
| **Veza i zdravlje** | da: veza, starost paketa, telemetrija Hz; RSSI, RAM, krug petlje: napomena „ESP ih još ne šalje“ | da (virtuelno) | redovi sa tačkom stanja i vrednošću |

- **Lidar po izvoru** *(odluke pri pisanju, posle pregleda; ponašanje ESP-a se ne menja)*:
  - ROBOT: dugme Upali/Ugasi lidar (postojeća komanda `LIDAR ON/OFF`, siva dok taktika radi / naoružan / meč).
  - SIM: krugovi stižu samo dok je na simuliranom ESP-u Meni → Lidar test (kao danas). Blok tada piše tu uputu
    umesto praznog radara. Ako simulirani ESP prima `LIDAR ON` istim putem kao virtuelni robot (bez izmene ESP koda),
    dugme Upali lidar radi i u SIM-u; ako ne, ostaje uputa. Odluku donosi graditelj posle provere.
  - Hibrid: pravi lidar pali i gasi sama sesija (`RobotLidar`, kao danas), pa dugmeta nema; blok je PRAVO.
- **Traka u hibridu** *(odluka pri pisanju)*: izvor je HIBRID (kao danas); polje Veza ne nudi „Poveži robota“ nego
  piše „lidar: host“ sa tačkom po starosti poslednjeg kruga lidara; „Prekini“ ne postoji, sesija se završava u Vožnji
  („Završi“), kao i svaka SIM sesija.
- **Detalj lidara** sadrži sve što današnji Test dela → Lidar ima: izvor Sesija | Snimak (snimci iz `studio/lidar/`,
  ▶/⏸, u krug), Upali/Ugasi lidar, Snimi krugove, slojevi sirovo / van stola / grupe, domet radara, sto + radar,
  „izračunao laptop“. Kad je izvor Snimak, oznaka bloka je SNIMAK.
- **Skica robota** se crta iz Profila (`studio/profiles/*.toml`): `[body]` širina, dužina, visina; `[ir]` `low_z`,
  `high_z`; `[drive]` pogonski točkovi; `[odometry]` `encoder_track` (pasivni odometrijski točkovi). Pogled SPREDA =
  stojiš ispred robota (levo robota je tebi desno), POZADI = stojiš iza (levo robota je tebi levo); strane su označene.
  **Lidar se na skici uvek crta na vrhu tela** (to je činjenica sa robota). `[lidar] z` u Profilu se u ovom poslu
  **ne menja**: on određuje šta simulirani lidar vidi (prepreke niže od ravni lidara se ne vide; protivnik 350 mm,
  kamenolom 330 mm), a Profil je zajednički za ceo tim. Prava visina lidara i to da li pravi lidar vidi protivnike
  (npr. preko nosača bikona) je posebno pitanje za kasnije (vidi „Kasnije“). *(odluka pri pisanju, posle pregleda)*
- **Lampice stanja** po bloku: zeleno radi, narandžasto upozorenje, prazno bez podataka. Pravila upozorenja su po
  bloku (npr. lidar ispod 5 Hz ili krug stariji od 1,5 s; baterija ispod praga iz Profila kad podatak postoji).
- **„Kako proveriti“** (tekstovi iz makete, mogu se doterati): lidar (kutija na 50 cm), IR (ruka na svaki ugao; domet se
  podešava točkićem na senzoru), enkoderi (Nuliraj, gurni 50 cm, razlika < 5 mm), PID, napajanje (total stop),
  aktuatori, tasteri, meč, veza.

### 4. Šta se briše

- `panels/test-dela.js` (podkartice) i raspored lidara u Test dela, tek kad Senzori rade isto ili bolje (pravilo
  korisnika: stari kod se ne briše pre toga).
- Polja za vezu iz prozora Izvori (premeštaju se na traku, id-jevi ostaju).

## Odluke korisnika (iz razgovora)

- Ime Gambit Studio; folder `studio/`; preimenovanje kao poseban prvi commit.
- Senzori umesto Test dela; raspored maketa B; detalj na klik.
- Prikazuje se šta god stiže (pravo, sim, hibrid, snimak), jasno označeno po bloku; pravo ima prednost; struja i napon
  bez podatka = nepovezano.
- Prvo dashboard sa podacima koji danas postoje; protokol i firmver kasnije, jedno po jedno polje.
- INA3221 ima 3 kanala: 5 V, baterija na ulazu, posle total stopa (12 V pogon); podela ostaje; struju meri ESP32.
- IR je samo da/ne (domet točkićem na senzoru); nema posebnog IR bloka jer je skica robota isti prikaz.
- Lidar je na vrhu robota.
- Poza nema svoj blok (već je na traci); Enkoderi bez maksimuma, sa Nuliraj.
- Snimak: samo učitan → uživo; pušten → Senzori pokazuju trenutak snimka (SNIMAK).
- Servo kao traka sa pozicijama; pumpe lampice; ventili kasnije.
- Pristupi 1a (veza = ROBOT sesija sa trake) i 2a (jedan panel sa svojim blokovima).

## Prepušteno graditelju

- Tačne mere rasporeda, boje (iz postojećih tema-promenljivih), ikonica Gambit Studio.
- Unutrašnji oblik modula bloka i ime foldera u `web/` (predlog `web/senzori/`).
- Kako se tačno računaju enkoderi iz `vl`/`vr` (integral po vremenu okvira) i Hz lidara.
- Imenovane pozicije servoa i tip aktuatora (servo / pumpa / ventil): kao opciona, unazad kompatibilna sekcija u
  Profilu; bez nje se aktuator prikazuje kao ime i vrednost.
- Položaj činča i tastera na skici: ne crtaju se dok ne postoje u Profilu (opciono polje).
- ID radnog prostora u kodu (`test` → `senzori`) i šta biva sa sačuvanim `eurosim.ws` (pada na podrazumevani prostor).
- Redosled zadataka u planu, uz uslov da je preimenovanje prvo i posebno.

## Kasnije (poseban posao, posebno odobrenje)

- ESP telemetrija, jedno polje po jedno: IR (`ir_raw`, `ir_mask`) i `w` (već stižu sa Nucleo-a u STATUS), INA3221
  (drajver + 3 kanala), stanje aktuatora, tasteri i činč, RSSI / RAM / krug petlje.
- Nucleo: enkoderi i zadato/stvarno po točku (firmver i protokol).
- Pololu G2: CS izlaz (struja po motoru) na ADC Nucleo-a, ako je ostao povezan.
- Ventili, imenovane pozicije servoa, položaji činča i tastera u Profilu.
- Prava visina lidara u Profilu (`[lidar] z`, danas 300 mm „(P)“) i da li pravi lidar na vrhu vidi protivnike; to menja
  i simulaciju, pa ide uz proveru sa robotom.
- Preimenovanje internih imena (`eurosim`, `~/.eurosim.json`…), uz prenos podešavanja.

## Provera

- Node testovi za čiste module: oznaka izvora i razlozi (sve kombinacije: robot danas, SIM, hibrid, snimak učitan,
  snimak pušten i pauziran, ništa),
  enkoderi iz `vl`/`vr`, pravila upozorenja, projekcija skice (levo/desno spreda i pozadi).
- Pytest: preimenovanje (prepoznavanje repoa sa `studio/`, poruka za stari `simulator/`, prenos fajlova iz starog
  `simulator/lidar/` bez prepisivanja), postojeći testovi prolaze sa novim putanjama.
- Ručno u browseru na 1366×768: stanja ništa / SIM / virtuelni robot / hibrid / snimak lidara; „Poveži robota“ iz
  Senzora i iz Vožnje; detalj svakog bloka; sve što je radilo u Test dela → Lidar radi u detalju lidara; Esc = STOP.
- Sa pravim robotom (ESP bez Nucleo-a, kao danas): Poveži robota → Senzori → Upali lidar, bez lutanja.
