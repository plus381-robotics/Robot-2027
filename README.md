# Robot-2027


## Struktura
Svaki folder je zaseban uredjaj i svaki treba da prati bar sledecu strukturu
- Da ima readme koji objasnjava vecinu stvari (uz gemini koji je besplatan ovo nema opravdanja da nepostoji)
- Da koristi github ignore za sve stoje preveliko i nema potrebe da se pull (npr biblioteke posto se one automatski skidaju pri kompile)
- 
## Šta je monorepo?

Monorepo je jedan Git repozitorijum u kome se nalazi više projekata ili modula.
U ovom slučaju, različiti delovi robota žive na jednom mestu, ali su podeljeni po folderima.

## Kako funkcioniše?

- Svaki deo robota je u svom folderu (npr. `nuc`, `stm32-motors`, `stm32-perfs`, `sima`, `beacon`).
- Svi koriste isti istorijat izmena, iste pull request-ove i isti proces pregleda koda.
- Niko ne commituje kod direktno na main vec preko se napravi novi branch i nakon zavrsetka dodavanja funckionalnosti se dodaje na main
- Promene koje utiču na više delova sistema lakše se prate i usklađuju jer su u istom repozitorijumu.

## Branchovanje
Najkompleksnija stvar je ovo zapravo, verovatno niste imali dodira sa ovim ali svaka funkcionalnost svaka promena koda mora da se branchuje prvo uradis par puta i udje ti u glavu kako se radi ali zasto je ovo dobro

Prvo vise ljudi moze da radi razlicite stvari u isto vreme 
recimo neko radi na senzorima robota dok drugi radi na hvataljkama i jedan i drugi si deo istog foldera i istog file pa ce biti konflikta 
Pre nebi moglo da se radi dok drugi radi na tome dok sad svako ima svoj branch pise kod na svom laptopu i nakon toga dodje kod robota na mini pc i uradi sledece:

1. git checkout repo xxxxx <-- stavlja ga na taj branch
pc pulluje taj repo i menja sve fajlove
2. radi se flash stm32 i ostalih stvari to pod obavezno
3. testira se ako radi kako treba onda napravis pull request ako ne radi kako treba ostavis tako odes na svoj laptop i gledas sto ne radi ili se povezes direktno na minipc gde ces da menjas brzo neke parametre dok ne proradi nakon cega ces da uradis commit pa pull request

zvuci komplikovano ali se workflow promenio samo tako sto sad mora da se pravi branch sto je svejedno common practice u kompanijama 

Benefiti:
- sve na jednom mestu - mnogo se lakse referencira kod od ostalih periferija jer je sve na jednom mestu
- laksa komunikacija izmedju uredjaja (ako se implementira komunikacija) iz gore navedenih razloga
- Mnogo bolja organizacija sve se zna gde je i svako moze da pogleda kod bilo cega i da pomogne oko bilo cega
- Na racunaru je mnogo lakse naci sta je gde jer je to sve jedan folder i jedan repo pa se i izbegavaju konfilkti kod pisanja koda
- Nema brige o tome da li svaki repo pullovan na najnoviji ako se radi na vise uredjaja

Mane:
- komplikovano u pocetku jer je potrebno neko razumevanje kako funckionise github
- Potrebno je skidati ceo repo umesto samo dela koji ti treba (nije problem velicina jer kod zauzima jako malo)

Kome nije jasno nek se obrati @itzpere za pomoc
