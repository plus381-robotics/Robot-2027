# ESP32-S3 ploča: istraživanje za PCB

Verzija 2, 2026-11-09 (posle odgovora tima). Ulaz: slika „ESP32-S3 · povezivanje", kod u `ESP32/` (WROOM-32 sada),
`docs/faza4-esp32s3-lidar.md`, `docs/esp-ciscenje-analiza.md`, Nucleo `Kik.ioc`, Waveshare šema ESP32-S3-DEV-KIT.
Skice i šeme: [`esp32s3-pcb-skice.html`](esp32s3-pcb-skice.html) (pravi ga `esp32s3-pcb-skice-gen.py`).
U `ESP32/` kodu ništa nije menjano; izmene softvera koje ploča traži su u tački 11, za odobrenje.

Oznake: **[MORA]** bez toga ploča ne radi pouzdano ili nešto može da izgori; **[PREPORUKA]** uraditi na v1;
**[OPCIJA]** footprint postoji, lemi se kad zatreba.

---

## 0. Odluke (9. 11. 2026)

| Pitanje | Odluka |
|---|---|
| Baterija | 4S LiPo (12,0-16,8 V), **isti GND** za bateriju i logiku |
| Korisnički interfejs | **na istoj ploči**: tasteri i enkoder zalemljeni, ekran utaknut u ženski header (ne lemi se) |
| NeoPixel | **izbačen** (status može da pokazuje RGB LED koji već postoji na ESP ploči, GPIO38) |
| Lidar | RPLIDAR A2, na UART2 ESP-a |
| Baterija (merenje) | glavno: INA3221 na powerboard-u; rezerva: ADC na ESP-u (GPIO10) |
| TX/RX | dobijaju LED-ove, preko bafera (ne opterećuju liniju) |
| USB | samo za hitno flešovanje; inače sve preko WiFi-ja |
| PCB | 2 sloja, **manja od 100 × 100 mm**, PCBWay, ručno lemljenje, delovi sa DigiKey-a |
| Nucleo | posebna ploča, kabl < 0,5 m; na Nucleo strani verovatno redosled RX, GND, TX |
| DC-DC | sopstveni, SiC417 (Vishay, do 10 A, ulaz do 28 V), na powerboard-u |
| STOP taster | ostaje samo na ESP-u (ne ide direktno na STM32) |
| ESP ploča | kupuje se kod malina314: **Waveshare ESP32-S3-DEV-KIT-N16R8** (tačka 1) |

---

## 1. Koju ESP ploču kupiti

malina314 prodaje Waveshare ploče, ne Espressif DevKitC-1. Proverio sam Waveshare šemu ESP32-S3-DEV-KIT-N8R8
(N16R8 je ista ploča sa 16 MB fleša):
- Letvice 2 × 22, **isti raspored kao Espressif DevKitC-1** (P2: GND, U0TXD, U0RXD, 1, 2, 42, 41, 40, 39, 38, 37,
  36, 35, 0, 45, 48, 47, 21, 20, 19, GND, GND; P1 kao J1 kod DevKitC-1).
- **RGB LED (WS2812B) na GPIO38**, napajan sa 3V3. Kod Espressif DevKitC-1 je na GPIO38 (v1.1) ili GPIO48 (v1.0).
  Plan ispod ne koristi ni 38 ni 48 za ništa bitno, pa radi na svim ovim pločama.
- **Jedan USB-C** sa hub-om CH334F: na istom kablu su i nativni USB (REPL, mpremote) i CH343 (UART0, auto-reset).
  Za hitno flešovanje je to zgodno: jedan kabl.
- 5 V sa USB-a ide na 5V liniju ploče preko Schottky diode B5819WS, pa spoljnih 5 V ne ide nazad u računar.
- LDO SGM2212-3.3 (ili AMS1117), EN RC 10 kΩ / 1 µF, BOOT i RESET tasteri.

| Ploča (malina314) | Cena | Za nas |
|---|---|---|
| ESP32-S3-DEV-KIT-**N16R8** (WROOM-1, 16 MB fleš, 8 MB octal PSRAM) | 1.390 RSD | ✅ **kupiti 2 komada** (robot + razvoj/rezerva) |
| ESP32-S3-DEV-KIT-N8R8 | 1.290 RSD | ✅ isto radi (8 MB fleša je dovoljno za MicroPython) |
| ESP32-S3-DEV-KIT-N16R8-U (spoljna antena, SMA, štap 155 mm) | 1.490 RSD | samo ako ploča završi u metalnom kućištu |
| ESP32-S3 WROOM-2, 32 MB / 16 MB (N32R16V) | 1.890 RSD | ❌ memorija na 1,8 V: GPIO47/48 rade na 1,8 V, treba drugi firmver |
| ESP32-S3-Nano, ESP32-S3-Pico | 1.190 / 1.290 RSD | ❌ drugi raspored pinova (Pico ima i samo 2 MB PSRAM) |
| ESP32-P4 i ESP32-C5 ploče | | ❌ drugi čip (P4 nema WiFi u čipu, C5 je RISC-V), sve bi se menjalo |
| ESP32-S3 RGB LCD driver, RGB Matrix | | ❌ pinovi zauzeti za ekran |

Napomene:
- Pinovi dolaze nezalemljeni (4 letvice po 20): na ESP ploču se leme muški pinovi (20 + 2 po strani), a na našu
  ploču ženske letvice 1 × 22.
- **Pre narudžbe PCB-a izmeriti ploču kad stigne** (razmak redova letvica, dužina, gde je USB-C i antena) i
  prema tome napraviti footprint. Za Espressif DevKitC-1 forum navodi 22,86 mm između redova; Waveshare nije
  zvanično potvrdio da je isto.
- Za MicroPython: firmver ESP32_GENERIC_S3, varijanta SPIRAM_OCT, verzija 1.29 kao do sada.

---

## 2. Plan pinova (konačno)

U odnosu na sliku menja se: UART2 RX sa GPIO48 na **GPIO21** (NeoPixel je izbačen, a 48 je RGB LED na
Espressif v1.0), novi pinovi za lidar MOTOCTL, I2C1, INT i VBAT.

| GPIO | Letvica | Funkcija | Napomena |
|---|---|---|---|
| 4 | J1-4 | T1 · NAZAD (žuti) | taster na ploči |
| 5 | J1-5 | T2 · OK (zeleni) | |
| 6 | J1-6 | T3 · STOP (crveni) | šalje STOP odmah |
| 7 | J1-7 | E-STOP stanje (PC817) | 1 = E-STOP pritisnut ili kabl prekinut |
| 15 | J1-8 | STM NRST preko 2N7002 | 1 = reset (obrnuta logika) |
| 16 | J1-9 | STM BOOT0 | 470 Ω redno, 10 kΩ na GND |
| 17 | J1-10 | UART1 TX → PA10 | 470 Ω redno |
| 18 | J1-11 | UART1 RX ← PA9 | 470 Ω redno |
| 8 | J1-12 | I2C0 SDA (ekran) | 2,2 kΩ |
| 9 | J1-15 | I2C0 SCL (ekran) | 2,2 kΩ |
| 10 | J1-16 | **VBAT (ADC1_CH9)** | delitelj 100 k / 18 k, rezerva za INA3221 |
| 11, 12, 13 | J1-17..19 | enkoder A, B, SW | na ploči |
| 14 | J1-20 | buzzer (PWM) | MOSFET |
| 1, 2 | J3-4, 5 | analogna rezerva (ADC1) | na konektor za proširenje |
| 42 | J3-6 | **LIDAR MOTOCTL** (PWM) | |
| 41, 40 | J3-7, 8 | **I2C1 SDA, SCL** (senzori) | 4,7 kΩ |
| 39 | J3-9 | **INT / XSHUT senzora** | |
| 38 | J3-10 | RGB LED na ESP ploči | samo softver (status umesto NeoPixel-a) |
| 48 | J3-16 | rezerva | konektor za proširenje (na Espressif v1.0 je LED) |
| 47 | J3-17 | **UART2 TX → lidar RX** | 3,3 V na WROOM-1 |
| 21 | J3-18 | **UART2 RX ← lidar TX** | |

Ne koriste se: 0, 3, 45, 46 (strapping), 19, 20 (USB), 43, 44 (UART0), 35-37 (octal PSRAM).

Zašto ovako (detaljno u verziji 1, ostaje isto):
- GPIO15 pri uključenju ESP-a ~60 µs ide u nulu (Espressif, tabela impulsa pri uključenju). Direktno vezan na
  NRST bi resetovao STM32. Preko 2N7002 je impuls u nulu bezopasan, a STM32 radi i kad ESP nema napajanje.
- GPIO18 pri uključenju kratko vuče liniju (0 ili 1) protiv TX-a STM32: zato 470 Ω.
- ADC2 (GPIO11-20) ne radi pouzdano uz WiFi, pa su analogni samo 1, 2 i 10.

---

## 3. NRST i BOOT0 (odvojen konektor) i UART ka Nucleo-u

- **J_UART** (JST-PH 3): 1 TX (ESP → PA10), 2 GND, 3 RX (ESP ← PA9). Odgovara Nucleo strani „RX, GND, TX" sa
  kablom 1:1 (pin 1 na pin 1). GND u sredini: obrnut utikač samo zameni TX i RX, ništa ne kvari. **Proveriti
  redosled na Nucleo strani pre nego što se napravi kabl.**
- **J_CTRL** (JST-PH 3): 1 NRST, 2 GND, 3 BOOT0. Na Nucleo-u: CN7-14 (ili CN6-3), CN7-8 (GND), CN7-7.
  Isti profil (GND u sredini), pa zamena kablova sa J_UART ne kvari ništa.
- NRST: GPIO15 → 1 kΩ → gejt 2N7002, 100 kΩ gejt-GND, drejn → NRST, sors → GND.
- BOOT0: GPIO16 → 470 Ω → BOOT0, 10 kΩ na GND (Nucleo ima i svoj ~10 kΩ; zajedno ≈ 3,0 V kad je ESP na 1).
- Kabl < 0,5 m na 921600 baud-a: 470 Ω × ~40 pF ≈ 20 ns, bit traje 1,08 µs. Uvrnuti TX sa GND-om ako je kabl duži.

### 3.1 LED-ovi za TX i RX (ne opterećuju liniju)

LED direktno na liniji je loš izbor: opterećuje liniju (1-3 mA), na 921600 baud-a bajt traje ~11 µs pa se
treptaj ne vidi, a LED sa linije na GND (kao na slici) svetli stalno jer UART miruje u jedinici.

Rešenje: jedan **SN74LVC14ADR** (6 Schmitt invertora, SOIC-14) za oba kanala, sa „produživačem impulsa":

    linija ──> [LVC14 A] ──>|── 1N4148W ──┬───────┬──> [LVC14 B] ──> 680 Ω ── LED ── 3V3
    (ESP strana R)                     220 nF    220 kΩ           (LED svetli kad je izlaz B na 0)
                                          │       │
                                         GND     GND

- Ulaz invertora na liniji: ~4 pF i < 1 µA, linija se ne oseća.
- Nula na liniji (start bit, podaci) → izlaz A = 1 → kondenzator se puni preko diode za nekoliko µs → izlaz
  B = 0 → LED svetli. Posle poslednjeg bajta kondenzator se prazni kroz 220 kΩ (τ ≈ 48 ms) → LED se gasi
  posle ~50 ms. Svaki okvir je vidljiv treptaj.
- RX (STATUS na 20 Hz) izgleda kao skoro stalno svetlo kad STM32 šalje; TX trepće sa PING-om.
- Dva preostala invertora: ulaze vezati na GND.
- Ulaz se uzima na ESP strani rednog otpornika (posle 470 Ω), da otpornik ograničava struju kad je ESP ploča bez
  napajanja.
- **BOOT0 LED** (žuti): 2N7002, gejt na liniji BOOT0, LED + 1 kΩ od 3V3 na drejn. **5V i 3V3 LED** (zeleni).

---

## 4. E-STOP i baterija (4S)

**Konektor BAT** (stezaljka 3,5 mm, 3 pina; drugi tip konektora od svih ostalih): 1 GND, 2 VBAT, 3 VMOT.
- VBAT: baterija posle glavnog prekidača i osigurača, pre E-STOP-a.
- VMOT: posle E-STOP-a (napon motora).

**E-STOP [MORA]:** VMOT → **BZT52C8V2** (Zener 8,2 V) → **1,5 kΩ** (1206) → anoda PC817; katoda → GND;
**1N4148W** suprotno paralelno sa LED-om. Izlaz: kolektor → GPIO7 + 10 kΩ na 3V3 + 100 nF; emiter → GND.
- 16,8 V: (16,8 − 8,2 − 1,2) / 1,5 kΩ ≈ 4,9 mA. 12 V: ≈ 1,7 mA. PC817 sa CTR ≥ 50 % daje ≥ 0,85 mA, a pull-up
  od 10 kΩ traži 0,33 mA.
- Zener: E-STOP se vidi čim napon motora padne ispod ~9,4 V. Bez njega LED svetli dok kondenzatori drajvera ne
  padnu na ~2 V, a to može da traje. Bez Zener-a: samo 3,3 kΩ.
- Logika: motori pod naponom → GPIO7 = 0; E-STOP pritisnut ili kabl prekinut → GPIO7 = 1 (bezbedna strana).

**VBAT na ADC (rezerva) [PREPORUKA]:** VBAT → **100 kΩ** → GPIO10, **18 kΩ** na GND, **100 nF** na GND.
- 16,8 V → 2,56 V; 12 V → 1,83 V. ESP32-S3 ADC sa slabljenjem 11 dB meri do ~3,1 V.
- Struja delitelja 0,14 mA. Kad ESP nema napajanje, napon na pinu je i dalje < 3,3 V.
- Softver: prosek više merenja, kalibracija jednom na pravom naponu.

Zona baterije na ploči: stezaljka, Zener, otpornik i LED strana optokaplera, 100 kΩ; ≥ 2 mm do ostalog bakra,
bez razlivenog bakra između strana optokaplera.

---

## 5. Buzzer: vrste i izbor

| Vrsta | Kako radi | Upravljanje | Primer (DigiKey) |
|---|---|---|---|
| **Aktivni** (internally driven) | ima svoj oscilator, na 5 V sam zvoni na jednoj frekvenciji | uključi/isključi (GPIO), PWM ne menja ton | Same Sky **CMI-1275-05TH**: 12 mm, 5 V, 110 mA, 2,7 kHz, 85 dB |
| **Pasivni** (externally driven, „transducer") | samo membrana, zvuči na frekvenciji koju mu pošalješ | PWM (LEDC), može više tonova | Same Sky **CEM-1206S**: 12 mm, 5 V, 45 mA, 2,4 kHz, 85 dB |

Obe vrste postoje kao **magnetne** (kalem i membrana, mala otpornost, traže tranzistor i diodu, glasne već na
5 V) i **piezo** (kristal, skoro bez struje, tiše na 5 V, bez diode ali sa otpornikom paralelno).

**Preporuka: pasivni magnetni (CEM-1206S)**, PWM na 2,4 kHz. Plan K-2 (1 kratak = potvrda, 2 = upozorenje,
3 = greška) radi i sa aktivnim, ali pasivni daje i različite tonove (greška niže, potvrda više). Kolo je isto
za obe: AO3400A (ili 2N7002), 100 Ω u gejtu, 100 kΩ gejt-GND, 1N4148W preko buzzera. Na footprint-u ostaviti
rupe za oba razmaka nožica (proveriti u datasheet-u).

---

## 6. ESD zaštita: gde tačno i koji deo

**Deo: TI TPD4E1U06DBVR** (4 kanala, SOT-23-6, 0,8 pF, 5,5 V radni napon, IEC 61000-4-2 ±15 kV kontakt).
DigiKey: [TPD4E1U06DBVR](https://www.digikey.com/en/products/detail/texas-instruments/TPD4E1U06DBVR/3929533),
oko 0,60 $ za 1 kom, 0,37 $ od 10 kom (cena iz keša pretrage, proveriti). Kapacitet od 0,8 pF ne smeta ni
UART-u na 921600 ni I2C-u. Za pojedinačnu liniju: Nexperia PESD5V0S1BA (SOD-323) (na DigiKey-u proveriti
dostupnost, Farnell ga vodi kao ukinut).

**Pravilo postavljanja:** ESD dioda **odmah do pinova konektora** (≤ 5 mm), redosled konektor → ESD → redni
otpornik → ESP. GND pin diode vijom direktno na GND sloj, kratko. Nekorišćen kanal ostaje nepovezan.

| Oznaka | Gde | Linije |
|---|---|---|
| U_ESD1 | između J_UART i J_CTRL | UART1 TX, UART1 RX, NRST, BOOT0 |
| U_ESD2 | kod LIDAR konektora | UART2 TX, UART2 RX, MOTOCTL |
| U_ESD3 | između SENS1 i SENS2 | SDA1, SCL1, INT |
| U_ESD4 | kod konektora za proširenje | GPIO1, GPIO2, GPIO48, EN |
| U_ESD5 | kod konektora za proširenje | SDA1, SCL1, UART2 TX, UART2 RX |

Gde **ne treba** ESD niz i zašto:
- **Tasteri i enkoder** (na ploči): metalno kućište enkodera (držači) i tastera na GND, pa udar iz prsta ide u
  masu. Linije imaju 1 kΩ redno i 100 nF (tasteri) odnosno 10 kΩ i 10 nF (enkoder), što guši ostatak.
- **Ekran** (na ploči, u header-u): nema spoljnog kabla.
- **BAT** (VBAT, VMOT): 100 kΩ i 1,5 kΩ + Zener su veliki redni otpori; 100 nF na ADC pinu.
- **5 V ulaz**: TVS SMBJ6.0A (snaga, pokriva i ESD).
- **USB**: na ESP ploči, koristi se samo u hitnim slučajevima.

---

## 7. Napajanje

- DC-DC na powerboard-u (SiC417) **podesiti na 5,2 V**: RPLIDAR A2 traži 4,9-5,5 V, a na ploči se gubi
  ~0,1-0,2 V (zaštita polariteta, osigurači).
- **PWR_IN** (JST VH, 2 pina, 3,96 mm; ne može da se pomeša sa ostalima) → **AO3401A** (zaštita polariteta,
  P-MOSFET, pad ~30 mV; Schottky od 0,4 V bi spustio lidar ispod 4,9 V) → **PTC 2 A** (Bourns MF-MSMF200-2) →
  **SMBJ6.0A** → 100 µF + 10 µF + 100 nF.
- Grane:
  - ESP ploča: **B5819W** (Schottky) → 5V pin (štiti od mešanja sa USB-om; LDO na ploči radi i od 4,8 V).
  - Lidar: **PTC 1,1 A** (MF-MSMF110-2) + 100 µF kod konektora.
  - Konektor za proširenje: **PTC 0,5 A** (MF-MSMF050-2).
  - Buzzer: direktno sa 5 V.

| Potrošač | Tipično | Najviše |
|---|---|---|
| ESP32-S3 + PSRAM (LDO na ploči) | 120 mA | 500 mA |
| OLED | 20 mA | 40 mA |
| RPLIDAR A2 | ~450 mA | ~600 mA + start |
| Buzzer | 30 mA | 60 mA |
| Senzori I2C | 50 mA | 100 mA |
| Proširenje | - | 500 mA (PTC) |
| **Ukupno** | **~0,7 A** | **~1,8 A** |

---

## 8. Konektori (konačno)

Na ploči ostaju samo konektori za ono što je van ploče. Svaki ima tip ili broj pinova koji ga razlikuje od
ostalih, ili isti profil (pin za GND na istom mestu), pa pogrešan kabl ne pušta napon na pogrešno mesto.

| Konektor | Tip (DigiKey MPN) | Pinovi |
|---|---|---|
| PWR_IN | JST VH 2 (B2P-VH) | 1 +5V, 2 GND |
| BAT | stezaljka 3,5 mm, 3 pina (npr. Phoenix MKDS 1/3-3,5, 1751251; proveriti) | 1 GND, 2 VBAT, 3 VMOT |
| J_UART | JST PH 3 (B3B-PH-K-S) | 1 TX→PA10, 2 GND, 3 RX←PA9 |
| J_CTRL | JST PH 3 (B3B-PH-K-S) | 1 NRST, 2 GND, 3 BOOT0 |
| LIDAR | JST XH 5 (B5B-XH-A) | po kablu A2: 1 VCC 5V, 2 TX lidara (→ GPIO21), 3 RX lidara (← GPIO47), 4 GND, 5 MOTOCTL |
| SENS1, SENS2 | JST PH 5 (B5B-PH-K-S) | 1 GND, 2 3V3, 3 SCL1, 4 SDA1, 5 INT |
| EXP | kutijasti 2 × 8 (npr. On Shore 302-S161) | tačka 9 |
| OLED | ženski header 1 × 4 (Sullins PPTC041LFBN-RC) + 2-4 rupe M2 za odstojnike | po modulu, vidi ispod |
| ESP ploča | 2 × ženski header 1 × 22 (Sullins PPTC221LFBN-RC) | |

- **LIDAR:** RPLIDAR A2 ima utikač XH 5-pin, redosled (Robotshop crtež, kontakti okrenuti nagore, s leva):
  VCC (crvena), TX (žuta), RX (zelena), GND (crna), PWM/MOTOCTL (plava). Ploča prima originalni kabl bez
  adaptera. **Proveriti na komadu pre narudžbe PCB-a.** Jedini XH na ploči, pa nema mešanja.
- **OLED:** moduli 0,96" postoje sa redosledom GND-VCC-SCL-SDA i VCC-GND-SCL-SDA. Na ploči dva lemna
  kratkospojnika (SJ1, SJ2) koji biraju da li je pin 1 GND ili 3V3, a pin 2 obrnuto. Zalemiti prema modulu koji
  se kupi. Rupe M2 da modul ne visi samo na header-u.

---

## 9. Konektor za proširenje (2 × 8)

| Pin | Signal | Pin | Signal |
|---|---|---|---|
| 1 | GND | 2 | GND |
| 3 | 3V3 | 4 | 5V (PTC 0,5 A) |
| 5 | SDA1 (41) | 6 | SCL1 (40) |
| 7 | GPIO1 (ADC1) | 8 | GPIO2 (ADC1) |
| 9 | GPIO39 (INT) | 10 | GPIO48 |
| 11 | UART2 TX (47) | 12 | UART2 RX (21) |
| 13 | EN (reset ESP-a) | 14 | GND |
| 15 | GND | 16 | GND |

UART2 je deljen sa lidarom: ili lidar ili uređaj na proširenju (npr. kamera). Proširenja idu najlakše preko
I2C1: PCA9685 (servoi), MCP23017 (GPIO), ADS1115 (analogno), TCA9548A (više ToF senzora).

---

## 10. Raspored ploče (100 × 100 mm, korisnički interfejs na ploči)

Skica u HTML fajlu (slika 4), 1 mm = 5 px. Gornja strana ploče je gornja strana robota.

- **ESP ploča** uspravno uz desnu ivicu (x 72,6-98, y 0-62,7), **antena na gornjoj ivici** iznad izreza u ploči
  između letvica (~19,5 × 8 mm), bez bakra i vodova ~10 mm oko antene (x ≥ 65, y ≤ 16). WiFi je glavni put za
  programiranje, pa antena ima prednost.
- **USB-C** gleda nadole, u ploču: ispod njega „prolaz" (x 78-93, do donje ivice) bez visokih delova, samo SMD,
  da utikač može da uđe u hitnom slučaju.
- **Gore levo: ekran** (0,96" modul 27 × 28 mm, mesto za 1,3" 36 × 34 mm).
- **Gornja ivica, između ekrana i antene:** J_UART i J_CTRL; ispod njih ESD, redni otpornici, NRST MOSFET,
  LVC14 i LED-ovi TX, RX, BOOT0 (blizu pinova 15-18 na J1).
- **Sredina:** tri tastera 12 × 12 mm (STOP crveni levo, NAZAD žuti, OK zeleni) i enkoder (Ø dugmeta 20 mm)
  desno od njih, ~4 mm od letvice ESP-a.
- **Levo dole:** konektor za proširenje (uspravno), buzzer i njegov drajver.
- **Donja ivica:** BAT (zona baterije, levo), PWR_IN, SENS1, SENS2, LIDAR (uz prolaz za USB).
- **Rupe M3:** (4, 4), (4, 96), (96, 96), (96, 70). Gore desno nema rupe: tu je antena.
- 5 V vodom ≥ 1,5 mm od PWR_IN do grana (ESP 5V pin J1-21, lidar, proširenje, buzzer).

Pravila za crtanje (ostaju iz verzije 1): donji sloj ceo GND (izrez samo kod antene), merne tačke (5V, 3V3,
GND, TX, RX, NRST, BOOT0, SDA0, SCL0, GPIO7, VBAT), silkscreen sa rasporedom pinova pored svakog konektora i
nazivima tastera, 0805 i SOT-23 za ručno lemljenje. Držači kućišta enkodera i tastera na GND.

Opcija za v2 (posle sezone): ESP32-S3-WROOM-1-N16R8 zalemljen direktno na ploču (bez letvica, niža i otpornija
ploča), sopstveni 3V3 regulator i USB-C sa ESD-om. Waveshare ploča ima i polu-rupe na ivici, pa može i da se
zalemi ravno na ploču, ali se onda teško menja.

---

## 11. Izmene softvera kad ploča stigne (za odobrenje; ovde nije rađeno)

1. **board_s3.py** (S-1): pinovi iz tačke 2, `UART_ID=1`, `UART2_TX=47`, `UART2_RX=21`, `LIDAR_MOTOCTL=42`,
   `I2C1_SDA=41`, `I2C1_SCL=40`, `SENS_INT=39`, `VBAT_ADC=10` (+ odnos delitelja 118/18), `RGB_LED=38`,
   `STM_NRST_ACTIVE=1`, `ESTOP_ACTIVE=1`, `BUZZER=14`; T1/T2/T3 → `BTN_BACK/BTN_OK/BTN_STOP`.
2. `match.StmReset` i `stmflash`: NRST sa obrnutom logikom (MOSFET).
3. `stmflash`: bootloader STM32 uvek na 115200 (AN2606), nezavisno od `UART_BAUD`.
4. `screen.py`: I2C frekvencija iz board fajla (800 kHz sa 2,2 kΩ). Ako ekran bude 1,3" sa SH1106: drugi drajver.
5. E-STOP (GPIO7) na PROVERA/ROBOT i prekid taktike; VBAT na PROVERA kad INA3221 ne odgovara.
6. RGB LED na ESP ploči (GPIO38) kao status umesto NeoPixel-a (K-1, jedna boja po stanju); buzzer (K-2) PWM 2,4 kHz.
7. Lidar (L-1..L-3): UART2 rxbuf ≥ 4 KB, MOTOCTL kao PWM 20-25 kHz.
8. Host test: board fajl ima sve pinove, bez duplikata, bez zabranjenih pinova (0, 3, 19, 20, 35-37, 43-46).

---

## 12. Spisak delova (DigiKey, ručno lemljenje)

Cene proveriti na DigiKey-u; MPN su delovi koji se tamo prodaju (osim gde piše „proveriti").

| Deo | MPN | Kom | Gde |
|---|---|---|---|
| ESD 4 kanala | TI TPD4E1U06DBVR (SOT-23-6) | 5 | tačka 6 |
| N-MOSFET mali | 2N7002 (npr. onsemi 2N7002LT1G, SOT-23) | 2 | NRST, BOOT0 LED |
| N-MOSFET buzzer | AOS AO3400A (SOT-23) | 1 | buzzer |
| P-MOSFET polaritet | AOS AO3401A (SOT-23) | 1 | PWR_IN |
| Schmitt invertor | TI SN74LVC14ADR (SOIC-14) | 1 | TX/RX LED |
| Optokapler | Sharp PC817X1NSZ1B (DIP-4) | 1 | E-STOP |
| Zener 8,2 V | Diodes BZT52C8V2 (SOD-123) | 1 | E-STOP |
| Dioda signalna | 1N4148W (SOD-123) | 4 | E-STOP, buzzer, LED ×2 |
| Schottky | B5819W (SOD-123) | 1 | 5V → ESP ploča |
| TVS 5 V | Littelfuse SMBJ6.0A (SMB) | 1 | PWR_IN |
| PTC | Bourns MF-MSMF200-2, MF-MSMF110-2, MF-MSMF050-2 (1812) | 1+1+1 | PWR_IN, lidar, EXP |
| Buzzer | Same Sky CEM-1206S (pasivni) ili CMI-1275-05TH (aktivni) | 1 | tačka 5 |
| Enkoder | Bourns PEC11R-4220F-S0024 (20 mm osovina, taster) | 1 | |
| Tasteri | Omron B3F-4055 (12 × 12) + kapice B32 u boji | 3 | |
| Konektori | B2P-VH, B3B-PH-K-S ×2, B5B-PH-K-S ×2, B5B-XH-A, 302-S161, stezaljka 3 pina 3,5 mm | | tačka 8 |
| Header | Sullins PPTC221LFBN-RC ×2, PPTC041LFBN-RC ×1 | | ESP, OLED |
| Otpornici, kondenzatori, LED | 0805 (LED 0805 zeleni ×2, crveni/žuti/plavi) | | |

---

## 13. Otvorena pitanja

1. **Ekran:** 0,96" (SSD1306, radi sa sadašnjim kodom), 1,3" (obično SH1106: drugi drajver) ili 2,42"
   (SSD1309, podrazumevano SPI, treba prelemiti na I2C i RES pin)? Kakav je redosled pinova na modulu?
2. **Buzzer:** pasivni (CEM-1206S, preporuka) ili aktivni (CMI-1275-05TH)?
3. **Nucleo strana:** koji konektor i tačan redosled (RX, GND, TX)? Treba i konektor za NRST/BOOT0 na toj strani.
4. **Lidar kabl:** proveriti redosled na komadu (VCC, TX, RX, GND, MOTOCTL) i da li je baš XH.
5. **Mesto ploče na robotu:** gornja ploča robota (dostupna za tastere, antena gore)? Ima li metala iznad ili
   pored antene (npr. nosač bikona, lidar)?
6. **Tasteri:** 12 × 12 mm na ploči sa kapicama, ili veći tasteri na panelu sa kablom?

---

## Izvori
- [ESP32-S3-DevKitC-1 v1.1 user guide](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/user_guide_v1.1.html)
- [ESP32-S3 Schematic Checklist](https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32s3/schematic-checklist.html)
- [ESP32-S3 datasheet](https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf),
  [forum: GPIO47/48 na 1,8 V](https://esp32.com/viewtopic.php?p=115415)
- [Waveshare ESP32-S3-DEV-KIT-N8R8 šema](https://files.waveshare.com/wiki/ESP32-S3-DEV-KIT-N8R8/ESP32-S3-DEV-KIT-N8R8-schematic.pdf),
  [Waveshare dokumentacija](https://docs.waveshare.com/ESP32-S3-DEV-KIT-N8R8),
  [CIRCUITSTATE pinout](https://www.circuitstate.com/pinouts/waveshare-esp32-s3-dev-kit-nxr8-wi-fi-development-board-pinout-diagram-arduino-reference/)
- malina314: [N16R8](https://malina314.com/proizvod/esp32-s3-microcontroller-2-4ghz-wi-fi-development-board-240mhz-dual-core-processor-esp32-s3-wroom-1-module-options-for-8mb-16mb-flash/),
  [N8R8](https://malina314.com/proizvod/esp32-s3-microcontroller-2-4ghz-wi-fi-development-board-240mhz-dual-core-processor-esp32-s3-wroom-1-n8r8-module/),
  [N16R8-U](https://malina314.com/proizvod/esp32-s3-dev-kit-n16r8-u/)
- [UM1724 Nucleo-64](https://www.st.com/resource/en/user_manual/um1724-stm32-nucleo64-boards-mb1136-stmicroelectronics.pdf),
  [šema MB1136](https://pages.hmc.edu/brake/class/e155/fa21/assets/doc/Nucleo-64_Schematic_MB1136.pdf)
- [RPLIDAR A2M8 crtež sa utikačem (Robotshop)](https://cdn.robotshop.com/media/R/Rpk/RB-Rpk-27/pdf/rplidar-a2m8-360-laser-scanner-open-box-dimensional-drawing.pdf),
  [Slamtec A2 manual](https://manuals.plus/slamtec/rplidar-a2-low-cost-360-degree-laser-range-scanner-manual)
- [SiC417 datasheet (Vishay 69062)](https://datasheet.chipsmall.com/SIC417CD-T1-E3/131889.pdf)
- DigiKey: [TPD4E1U06DBVR](https://www.digikey.com/en/products/detail/texas-instruments/TPD4E1U06DBVR/3929533),
  [CEM-1206S](https://www.digikey.ca/en/products/detail/same-sky-formerly-cui-devices/CEM-1206S/412414),
  [CMI-1275-05TH](https://www.digikey.com.au/en/products/detail/same-sky-formerly-cui-devices/CMI-1275-05TH/25577239)
- STM32F401 datasheet (NRST filter), AN2606 (USART bootloader), PC817, 74LVC14, Bourns PEC11.
