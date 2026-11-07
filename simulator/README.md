# Simulator taktika (eurosim)

Pušta taktike iz `ESP32/tactics/` bez robota, sa **istim ESP kodom** koji radi na robotu
(`tac.py`, `robot.py`, `runner.py`, `match.py`, `app.py`...) i simuliranim STM32-jem.

## Web interfejs

    pip install -r simulator/requirements.txt      # jednom (aiohttp)
    python simulator/sim.py serve                  # otvara http://localhost:8270

- Gore: taktika, strana, režim (meč ili test), **Simulate** (Ctrl+Enter). Simulacija ide do kraja (meč od
  100 s za par sekundi), pa se snimak pušta.
- Sto u 3D ili odozgo (**Top**): robot, pređena putanja (bela), odometrija (narandžasto; robot-duh kad se
  razlikuje od stvarne poze), početak svakog koraka (broj, boja po ishodu), ciljevi GOTO komandi,
  protivnik. Miš: okretanje / pomeranje / zum; pozicija miša u koordinatama terena i taktike;
  **dupli klik kopira koordinate** za taktiku.
- Desno: stanje u trenutku (poza, odometrija i greška, v/ω i reference, točkovi, faza regulacije na
  STM32, IR, aktuatori, vreme meča), trenutni korak sa trakom do timeout-a, lista koraka i dnevnik
  (i poruke ESP<->STM32). Klik na korak ili red dnevnika skače na taj trenutak.
- Dole: pusti/pauza (razmak), brzina ×0.25..×25, frame napred/nazad (←/→), korak napred/nazad
  (Shift+←/→), klizač sa oznakama koraka, grafici brzine, okretanja i točkova (klik = skok).
- **Save run** čuva snimak u `simulator/runs/` (ide u git), **Saved runs** ga učitava.

## Komandna linija

    python simulator/sim.py run primer                     # meč na plavoj (naoružan -> činč -> 100 s)
    python simulator/sim.py run primer --side zuta --test  # odmah, kao tools/tactic.py
    python simulator/sim.py run primer --opp 800,1000      # protivnik 300x300 mm na (800, 1000)
    python simulator/sim.py run primer -v                  # i sve poruke ESP <-> STM32
    python simulator/sim.py run primer --out run.json.gz   # sačuvaj snimak

Komandna linija treba samo Python 3.11+. Testovi: `python -m pytest simulator/tests`
(posebno od `ESP32/tests/host`, jer oba imaju svoj `conftest.py`).

## Kako radi

```
taktika.py -> tac.py -> runner/match/app -> robot.py ==UART bajtovi (COBS+CRC)==> SimSTM
             (pravi ESP kod iz ESP32/lib, nepromenjen)                            ├ comm.c      (eurosim/stm.py)
                                                                                  ├ comm_port.c (eurosim/stm.py)
                                                                                  ├ control.c   (eurosim/control.py)
                                                                                  └ model robota (eurosim/plant.py)
```

- **Granica je UART.** `robot.py` ne zna da li priča sa pravim ili simuliranim STM32. ESP kod se ne kopira
  i ne menja; simulator ga uvozi iz `ESP32/` kao `ESP32/tests/host`.
- **Virtuelno vreme.** Sat iz `compat.py` (`compat.fake`); STM32 deo se pomera u koracima od 1 ms (kao
  1 kHz petlja na STM32). Simulacija je brža od stvarnog vremena (meč od 100 s za par sekundi) i uvek
  daje isti rezultat za istu taktiku.
- **SimSTM** prati `comm.c` i `comm_port.c`: duplikat samo po poslednjem seq, PREEMPTED, STOP, pad veze
  posle 500 ms, STATUS na 50 ms, SET_POSE samo kad robot stoji, GOTO = vožnja pa okret na theta,
  ROTATE timeout 5 s, meč 100 s, statusi regulacije -1/-3/-4/-5 -> DONE/BLOCKED/TIMEOUT.
  Aktuatori (AX, pumpe): ACK pa DONE posle zadatog vremena, nikad FAIL.
- **Regulacija** (`control.py`) je Python prepis BlackPill `control.c` + `signal.c` (iste faze, isti
  profil brzine, tolerancije, "stacked"), parametri u profilu. Kad se regulacija na novom robotu promeni,
  menja se ovaj fajl i profil.
- **Model robota** (`plant.py`): diferencijalni pogon (razmak točkova iz profila), kašnjenje i ograničeno
  ubrzanje točkova, odometrija sa pasivnih točkova (sa opcionom greškom: tada se stvarna poza i ono što
  STM32 misli razilaze), sudar sa ivicom ili preprekom (robot stoji -> BLOCKED), IR senzori (4 napred,
  4 nazad) vide prepreku -> robot staje -> BLOCKED.
- **Snimak** (`record.py`): stanje na 20 ms (stvarna poza, odometrija, brzine, reference, stanje taktike
  i meča), poruke ESP <-> STM32, dnevnik, koraci. Iz njega crta web interfejs.
- **Server** (`server.py`, aiohttp): svaka simulacija u posebnom procesu (taktika sa beskonačnom petljom
  bez `wait()` se prekine posle 60 s). Frontend (`web/`) je običan JavaScript bez build koraka;
  three.js i uPlot su u `web/vendor/` (radi bez interneta).
- UI smoke test: `node simulator/tests/ui_smoke.js` dok radi `sim.py serve` (treba Playwright).

## Profil robota

`profiles/robot2027.toml`: dimenzije, pogon, odometrija, regulacija, IR, aktuatori. Vrednosti označene sa
**(P)** su pretpostavke (nema još merenja); kad stignu merenja ili snimak sa robota, menjaju se tu.

## Teren

`eurosim/field.py`: Eurobot 2027 (pravila, dodatak G.1): x 0..3000, y 0..2000, žuta startna zona
x 0..500, plava x 2500..3000 (y 750..1250). Elementi igre dolaze kasnije.
