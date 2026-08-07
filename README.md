# Robot-2027

## Šta je monorepo?

Monorepo je jedan Git repozitorijum u kome se nalazi više projekata ili modula.
U ovom slučaju, različiti delovi robota žive na jednom mestu, ali su podeljeni po folderima.

## Kako funkcioniše?

- Svaki tim radi u svom folderu (npr. `nuc`, `stm32-motors`, `stm32-perfs`, `sima`, `beacon`).
- Svi koriste isti istorijat izmena, iste pull request-ove i isti proces pregleda koda.
- Promene koje utiču na više delova sistema lakše se prate i usklađuju jer su u istom repozitorijumu.