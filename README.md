# Robot-2027

[![yt video koji objasnjava repo](https://img.youtube.com/vi/ONZMAUEJe-c/0.jpg)](https://www.youtube.com/watch?v=ONZMAUEJe-c)

[![protocol](../../actions/workflows/protocol.yml/badge.svg)](../../actions/workflows/protocol.yml)
[![rpi](../../actions/workflows/rpi.yml/badge.svg)](../../actions/workflows/rpi.yml)
[![nucleo](../../actions/workflows/nucleo.yml/badge.svg)](../../actions/workflows/nucleo.yml)

## Struktura

| Folder | Uređaj | Sadržaj |
|---|---|---|
| [`rpi/`](rpi/) | Raspberry Pi 4 | ROS 2 paketi, konfiguracija sistema, udev pravila |
| [`nucleo/`](nucleo/) | STM32 Nucleo F401RE | firmware za kretanje (CubeMX + CMake) |
| [`pico/`](pico/) | Raspberry Pi Pico | aktuatori, OLED, enkoder, NeoPixel |
| [`protocol/`](protocol/) | svi | zajednički COBS + CRC-16 protokol (header-only C++) |
| [`sima/`](sima/) | SIMA roboti | |
| [`beacon/`](beacon/) | beacon | |
| [`tools/`](tools/) | razvojni računar / RPi | echo test, flešovanje Nucleo-a |
| [`docs/`](docs/) | ceo robot | log book, dijagrami, specifikacija protokola |

Svaki folder uređaja mora da ima bar:
- `README.md` koji objašnjava šta radi, kako se gradi i kako se flešuje (uz gemini/Claude koji su besplatni ovo nema opravdanja da ne postoji)
- `.gitignore` za sve što je preveliko i nema potrebe da se pull-uje (build izlazi, biblioteke koje se automatski skidaju pri kompajliranju)

**Izuzetak:** `nucleo/firmware/Drivers/` (STM32 HAL) se **commituje**, jer se ne skida automatski.
Bez njega projekat ne može da se izgradi na RPi-ju i u CI-ju, gde nema CubeMX-a.

## Šta je monorepo?

Monorepo je jedan Git repozitorijum u kome se nalazi više projekata ili modula.
U ovom slučaju, različiti delovi robota žive na jednom mestu, ali su podeljeni po folderima.

## Kako funkcioniše?

- Svaki deo robota je u svom folderu.
- Svi koriste isti istorijat izmena, iste pull request-ove i isti proces pregleda koda.
- Niko ne commituje kod direktno na `main`, već napravi novi branch i nakon završetka funkcionalnosti otvori pull request ka `main`-u. GitHub to i sprečava (pravilo za `main` granu).
- Promene koje utiču na više delova sistema lakše se prate i usklađuju jer su u istom repozitorijumu. Najbolji primer je `protocol/`: kada se promeni poruka, RPi, Nucleo i Pico se menjaju u **istom** PR-u.
- Na svaki PR GitHub Actions automatski gradi i testira samo delove koji su promenjeni (zelena/crvena oznaka na PR-u).

## Branchovanje

Najkompleksnija stvar je ovo zapravo, verovatno niste imali dodira sa ovim, ali svaka funkcionalnost i svaka promena koda mora da se branchuje. Uradiš par puta i uđe ti u glavu kako se radi.

Zašto je ovo dobro: više ljudi može da radi različite stvari u isto vreme. Recimo neko radi na senzorima robota dok drugi radi na hvataljkama, a obojica menjaju isti folder i isti fajl, pa bi bilo konflikta. Pre se nije moglo raditi dok drugi radi na tome, a sad svako ima svoj branch, piše kod na svom laptopu i nakon toga dođe do robota.

**Imenovanje grana:** `<uredjaj>/<kratak-opis>`, npr. `nucleo/heartbeat`, `rpi/nucleo-bridge`, `protocol/goal-poruka`.

**Na laptopu:**

```bash
git switch main && git pull
git switch -c nucleo/heartbeat
# ... izmene ...
git add -A && git commit -m "nucleo: heartbeat timeout zaustavlja motore"
git push -u origin nucleo/heartbeat
```

**Na robotu (RPi, preko SSH-a):**

1. `git fetch && git switch nucleo/heartbeat` — RPi prelazi na tvoju granu
2. build i flešovanje, to pod obavezno: `colcon build ...` i/ili `./tools/flash_nucleo.sh --build`
3. testiraš. Ako radi kako treba, otvoriš pull request. Ako ne radi, vratiš se na laptop i gledaš šta ne radi, ili na RPi-ju brzo menjaš parametre dok ne proradi, pa commit i pull request.
4. kada završiš, vrati RPi na `main`: `git switch main && git pull`

Detalji (pristup GitHub-u sa RPi-ja, ko je autor commita): [`rpi/README.md`](rpi/README.md).

Zvuči komplikovano, ali se workflow promenio samo tako što sad mora da se pravi branch, što je svejedno common practice u kompanijama.

## Benefiti i mane

Benefiti:
- sve na jednom mestu, mnogo se lakše referencira kod ostalih periferija
- lakša komunikacija između uređaja: protokol je jedan zajednički kod, ne tri kopije
- mnogo bolja organizacija, sve se zna gde je i svako može da pogleda kod bilo čega i da pomogne
- nema brige o tome da li je svaki repo pull-ovan na najnoviji ako se radi na više uređaja

Mane:
- komplikovano u početku jer je potrebno neko razumevanje kako funkcioniše GitHub
- potrebno je skidati ceo repo umesto samo dela koji ti treba (nije problem, kod zauzima jako malo)

## Prethodna sezona

Kod iz 2026: `PogonskiSTM-2026-BlackPill` i `DrugiSTM-2026-BlackPill` (zasebni repoi, samo za referencu).

Kome nije jasno nek se obrati @itzpere za pomoć.
