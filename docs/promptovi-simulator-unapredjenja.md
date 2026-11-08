# Promptovi za nov chat (plan unapređenja simulatora)

> Stanje 2026-11-08: promptovi 1-7 su urađeni (vidi stanje na vrhu `docs/plan-simulator-unapredjenja.md`).
> Ostaju kao primer i za delove koji nisu urađeni.

Svaki prompt je samostalan: nalepi ga u nov chat (Claude Code, repo `plus381-robotics/Robot-2027`).
Plan sa detaljima je `docs/plan-simulator-unapredjenja.md`. Ako taj fajl još nije commit-ovan, nalepi i njegov
relevantan deo, ili ga prvo commit-uj.

Zajednička pravila (već su u svakom promptu):

> Pravila: piši mi na srpskom. Radi na posebnoj grani, ne push-uj bez pitanja. Commit-i bez "Co-Authored-By"
> linija, autor je samo vlasnik repoa. Pre svake izmene u `ESP32/` ili `protocol/` napiši šta i zašto i čekaj
> "da". `nucleo/` i `pogon-blackpill/` samo u delu protokola (`comm.c`, `comm_port.c`, `protocol.h`) i samo
> uz moje odobrenje. Ništa ne flešuj. Jasno piši šta je testirano, a šta nije. Testovi:
> `python -m pytest -q simulator/tests` i `cd ESP32/tests/host && python -m pytest -q` (odvojeno).

---

## Prompt 1: Faza A (bag plave strane, Save as, Tab, markeri, IR zraci)

```
Repo Robot-2027, simulator (simulator/eurosim, web UI u simulator/web: three.js, CodeMirror 6, uPlot).
Uradi fazu A iz docs/plan-simulator-unapredjenja.md (stavke S1, S2, S3, S5, S6). Samo simulator, ESP32/ se ne dira.

S1 bag (reprodukovan): u Live režimu, ako se Live pokrene sa žutom pa izabere plava i Arm/Pull cord, pravi
robot ostaje na žutoj (sim.py:109-110 postavlja robota samo na startu Live-a; arm/test u sim.py:345-349 ga ne
pomeraju; komanda place postoji na sim.py:358 ali je UI ne šalje), a odometrija i ciljevi idu na plavu
(greška odometrije ~1842 mm). Takođe meta (strana) ide u UI samo u prvoj poruci (sim.py:409), #side nema
change handler (web/app.js), ESP panel pokriva plavu startnu zonu u 3D. Popravka: kad robot miruje, promena
strane ili arm/test sa drugom stranom postavi robota na START taktike ogledano po strani; meta slati posle
promene; u brzom režimu promena strane označi snimak kao zastareo ili ponovo simulira; ESP panel da se može
skloniti. Napiši Playwright proveru tog scenarija (Chromium je instaliran, require('playwright')).

S2 Save as + Duplicate (+ Rename/Delete sa potvrdom): tactics.save (eurosim/tactics.py:318-331), provera
imena (mala slova, slova/brojevi/_, ne počinje brojem), 409 ako postoji dok se ne potvrdi.

S3 autocomplete (web/editor.js:31-62, keymap 89-97): Tab prihvata predlog kad je lista otvorena (inače polja
snippeta, inače uvlačenje), Ctrl+Space sve komande po grupama, snippet sa imenovanim poljima (x_mm, y_mm),
rangiranje prefiks pa sadrži.

S5 markeri (web/view3d.js:241-293, 445-453): veće tačke (~40 mm), natpisi iznad svega (depthTest false) sa
podlogom, broj + ime koraka, strelica ugla na cilju, putanja obojena po koraku i deblja, klizač veličine,
isto u Top pogledu.

S6 IR zraci: snimati ir_hits (plant.py:143), crtati zrake iz plant.sensors() (plant.py:215-257) sa dometom iz
profila, sivo bez pogotka, crveno do pogotka, kutija "IR".

Na kraju: testovi, screenshot-ovi pre/posle, commit lokalno na grani (bez push-a), kratak izveštaj.
Pravila: piši mi na srpskom. Radi na posebnoj grani, ne push-uj bez pitanja. Commit-i bez "Co-Authored-By"
linija, autor je samo vlasnik repoa. Pre svake izmene u ESP32/ ili protocol/ pitaj i čekaj "da". Ništa ne
flešuj. Jasno piši šta je testirano, a šta nije.
```

---

## Prompt 2: Faza B1 (putanja uživo dok se piše + x, y pomoć)

```
Repo Robot-2027, simulator. Uradi S7 i S8 iz docs/plan-simulator-unapredjenja.md.

Cilj: dok pišem taktiku u editoru (web/editor.js, CodeMirror 6), putanja se crta odmah, bez Run.
1) Brz nacrt: server izvršava taktiku sa lažnim tac modulom (isti potpisi kao ESP32/lib/tac.py, __all__)
   koji samo beleži komande i računa idealnu putanju (goto = okret + prava, move = prava, okreti, aktuatori
   kao oznake, wait kao vreme; komande vraćaju True; limit 200 komandi / 100 s; ogledanje po strani istim
   mirror_xy), sa brojem reda za svaku komandu. Debounce ~200 ms, izvršavanje u izolovanom procesu sa
   timeout-om. Prikaz: isprekidana linija + numerisane tačke, druga boja od snimka.
2) Prava simulacija u pozadini kad stanem sa kucanjem (~1 s), prekida se na novu izmenu; kutija auto-sim.
3) Veza kod-mapa: kursor u redu sa goto ističe tačku; klik na tačku skače na red; greška = poslednji dobar
   nacrt posiveo.
S8: uvek vidljiv lenjir po ivicama (100 mm podeoci, brojevi na 500), oznaka 0,0 dole levo i strelice x→ y↑;
dok je kursor u komandi sa x,y: krst na mapi sa linijama do ivica i natpisom "x = ... od leve ivice";
dugme/Alt+klik "tačka sa mape" ubacuje goto(x, y) ili menja brojeve; prevlačenje tačke nacrta menja brojeve
kad su literali; tihi inlay natpisi x= y= (može da se isključi). Koordinate u editoru su uvek žute strane.

Postojeće: static_check u eurosim/tactics.py:180-276, tac_api iz tactics.py:40-79, prikaz koordinata ispod
miša app.js:771-785, mreža view3d.js:40-50.
Testovi: pytest za lažni tac (petlje, promenljive, plava strana), Playwright za prikaz.
Pravila: piši mi na srpskom. Radi na posebnoj grani, ne push-uj bez pitanja. Commit-i bez "Co-Authored-By"
linija, autor je samo vlasnik repoa. ESP32/ se ne menja bez mog "da". Ništa ne flešuj. Jasno piši šta je
testirano.
```

---

## Prompt 3: Faza B2 (API panel "Gambit Micro" + jasniji opisi + timeline)

```
Repo Robot-2027, simulator. Uradi S4 i S9 iz docs/plan-simulator-unapredjenja.md.

S4: "tac API" je sad kartica pored Problems ispod editora (web/index.html:80-85, style.css:124-127) i ne vidi
se. Napravi dugme "📖 Komande" u traci editora i desni panel (može da se skloni) sa pretragom; za svaku
komandu: rečenica običnim jezikom, tabela parametara sa jedinicama, šta vraća, primer, za x,y mala SVG slika
stola sa osama; klik ubacuje komandu. Ime u UI: "Gambit Micro". Podaci iz ESP32/lib/tac.py preko ast
(eurosim/tactics.py:40-79). Opisi treba da budu za ljude koji nisu programeri; predlog za goto je u planu.
Docstring-ovi su u ESP32/lib/tac.py: to je izmena u ESP32/, pa mi PRVO pokaži nove tekstove i čekaj "da"
(samo tekst, ponašanje isto; mpy-cross izbacuje docstring-ove, pa nema cene u RAM-u). Dodaj test da svaka
komanda iz __all__ ima opis, parametre, Vraća i Primer.

S9 timeline (web/app.js:211-221 renderMarks, charts.js): traka koraka iznad klizača (pravougaonik po koraku,
boja po ishodu, broj i ime, klik skače), tačke na grafiku brzine na početku/kraju koraka, uže trake za
aktuatore i događaje (pad veze, restart STM32, prepreka), zastavica ČINČ i NAORUŽAN, os "vreme meča" (0 =
činč, senka napada od 85 s), u Live veliko dugme ČINČ na traci i natpis "čeka činč", hover ističe tačku na
mapi i red u kodu.

Pravila: piši mi na srpskom. Radi na posebnoj grani, ne push-uj bez pitanja. Commit-i bez "Co-Authored-By"
linija, autor je samo vlasnik repoa. Pre izmene u ESP32/ ili protocol/ pitaj i čekaj "da". Ništa ne flešuj.
Jasno piši šta je testirano.
```

---

## Prompt 4: Faza C (sync: repo kao radni prostor, pokretanje bez instalacije)

```
Repo Robot-2027. Uradi S10 iz docs/plan-simulator-unapredjenja.md: tim treba da deli taktike i profil robota i da uvek
ima najnoviju aplikaciju, bez instaliranja.

Postojeće: eurosim/paths.py:22-66 (find_repo traži ESP32/lib/tac.py od foldera exe-a naviše: iz repoa radi
nad ESP32/tactics i simulator/profiles; inače ~/Eurosim), PyInstaller exe (simulator/eurosim.spec,
.github/workflows/simulator.yml).

Predlog za implementaciju:
1) start.bat i start.sh u korenu repoa preko uv (jedan izvršni fajl, bez admin prava, sam skine Python i
   zavisnosti): simulator/pyproject.toml sa zaključanim verzijama (uv.lock); ako uv nema, skripta ponudi
   da ga skine u .tools/ (gitignore). Dvoklik pokreće server i otvara pregledač.
2) Panel "Repo" u aplikaciji: grana, ispred/iza, izmenjeni fajlovi (taktike, profili), "Povuci najnovije"
   (git pull --ff-only), "Sačuvaj na GitHub" (add samo taktike/profile, commit sa porukom, push), upozorenje
   kad je profil promenjen na GitHub-u (posle fetch), konflikt = poruka + uputstvo za GitHub Desktop.
   Preko git komande (subprocess); jasna poruka ako git nije instaliran.
3) Exe se stavlja u koren kloniranog repoa. Ako se pokrene van repoa (find_repo ne nađe ESP32/lib/tac.py):
   crvena traka na vrhu koja se ne može zatvoriti: "Aplikacija nije u repou Robot-2027. Taktike i profil
   se NE čuvaju u timski repo i niko ih neće videti. Stavi ovaj fajl u koren kloniranog repoa, ili:"
   + dugmad [Kloniraj repo…] (izbor foldera, git clone, zapamti putanju, ponudi da kopira exe u koren),
   [Otvori folder repoa…] (izbor postojećeg klona, provera ESP32/lib/tac.py i git remote, putanja se pamti
   u ~/.eurosim.json), [Nastavi bez repoa] (traka ostaje žuta, svaki Save kaže gde je sačuvano).
   "Bez repoa" čuva lokalno u ~/Eurosim kao sada (odlučeno), uz upozorenje "samo na ovom računaru".
   Naslov prozora "Eurosim (BEZ REPOA)". Test: prazan folder -> traka; otvori privremeni klon -> traka
   nestaje; ponovno pokretanje pamti izbor.
4) README: kako se koristi (clone + exe u koren ili start) i pravila za tim (taktike svako svoj fajl; profili preko PR).
Proveri na Linux-u; za Windows napiši šta nije provereno. Testovi za git panel sa privremenim repoom.

Pravila: piši mi na srpskom. Radi na posebnoj grani, ne push-uj bez pitanja. Commit-i bez "Co-Authored-By"
linija, autor je samo vlasnik repoa. ESP32/ i protocol/ se ne menjaju bez mog "da". Jasno piši šta je
testirano.
```

---

## Prompt 5: Faza D1 (ime Gambit Micro na ESP-u, opciono)

```
Repo Robot-2027. API taktika (ESP32/lib/tac.py) se zove "Gambit Micro"; funkcije ostaju iste, ništa se ne
preuzima iz repoa Gambit. Predloži kako da modul na ESP-u dobije ime gambit (from gambit import *) uz tac kao
omotač za stare taktike, sa RAM procenom, i čekaj moje "da" pre izmene u ESP32/.
Simulator (autocomplete, API panel, nacrt putanje, šablon) mora da radi sa oba imena.
Pravila: piši mi na srpskom. Radi na posebnoj grani, ne push-uj bez pitanja. Commit-i bez "Co-Authored-By"
linija, autor je samo vlasnik repoa. Ništa ne flešuj. Jasno piši šta je testirano.
```

---

## Prompt 6: Faza D2 (prilaz elementima: IR vidi kamenolom)

```
Repo Robot-2027. Uradi analizu i predlog za S12 iz docs/plan-simulator-unapredjenja.md, pa čekaj moje "da" pre izmena.

Nalaz: u simulatoru taktika koja prilazi kamenolomu (field.py QUARRIES, visina 330 mm) dobija BLOCKED na
svakom prilazu: IR domet 250 mm, see_elements = true, visok senzor na 320 mm (profil [ir]). Robot ne može
bliže od ~270 mm; kamenolomi na x 1250 se ne mogu prići jer IR vidi i srednji kamenolom (x 1445).
Opcije: (1) mehanika: visoki senzori iznad 330 mm (proveri u simulatoru menjanjem [ir] high_z);
(2) protokol v5: zastavica u GOTO/MOVE koja za tu komandu ignoriše niske senzore (API goto(..., prilaz=True)),
STM comm_port.c prosleđuje regulaciji (goal.obstacle); (3) manji domet u prilazu.
Predlog: prvo (1) u simulatoru sa stvarnim visinama; ako ne može, (2) samo za niske senzore.
Izmena protokola/ESP/STM tek posle mog "da". STM: samo comm.c/comm_port.c/protocol.h; proveri sintaksu sa
gcc -fsyntax-only, ništa ne flešuj.
Pravila: piši mi na srpskom. Posebna grana, ne push-uj bez pitanja. Commit-i bez "Co-Authored-By" linija,
autor je samo vlasnik repoa. Jasno piši šta je testirano.
```

---

## Prompt 7: primer taktike (sve komande, kamenolom do kamenoloma)

```
Repo Robot-2027. Dodaj u ESP32/tactics dve taktike iz dodatka A u docs/plan-simulator-unapredjenja.md (sve_komande.py
i kamenolomi.py). To je izmena u ESP32/: pokaži mi fajlove i čekaj "da". Proveri u simulatoru na obe strane:
  cd simulator && python -m eurosim run sve_komande --side zuta   (i plava, i kamenolomi)
Ako je S12 (prilaz elementima) već urađen, kamenolomi.py da prilazi bliže i da obiđe i kamenolome 2 i 6.
"Bunt" = kamenolom (gomila od 3 kamena)? Pitaj me ako nisi siguran.
Pravila: piši mi na srpskom. Posebna grana, ne push-uj bez pitanja. Commit-i bez "Co-Authored-By" linija,
autor je samo vlasnik repoa. Ništa ne flešuj. Jasno piši šta je testirano.
```
