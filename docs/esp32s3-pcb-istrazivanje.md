# ESP32-S3 ploča: istraživanje za PCB

Nacrt, 2026-11-09. Ulaz: slika „ESP32-S3 · povezivanje" (plan pinova), kod u `ESP32/` (WROOM-32 sada),
`docs/faza4-esp32s3-lidar.md`, `docs/esp-ciscenje-analiza.md` (6. Priprema za S3), Nucleo `Kik.ioc`.
Skice rasporeda i šeme ključnih delova: [`esp32s3-pcb-skice.html`](esp32s3-pcb-skice.html) (otvoriti u browseru).
Ovde se ništa ne menja u `ESP32/` kodu; spisak izmena softvera koje ploča traži je u tački 10, za odobrenje.

Oznake: **[MORA]** bez toga ploča ne radi pouzdano ili postoji rizik da nešto izgori; **[PREPORUKA]** treba
uraditi na v1 ploči jer kasnije košta više; **[OPCIJA]** za buduće dodatke (footprint bez lemljenja je jeftin).

---

## 0. Ukratko

**Izbor pinova je dobar.** Plan sa slike izbegava sve što na ESP32-S3-DevKitC-1 N16R8 ne sme da se koristi:
strapping pinove (0, 3, 45, 46), USB (19, 20), konzolu UART0 (43, 44) i octal PSRAM (35, 36, 37). Svi pinovi
koje taktika i meni koriste su na levoj letvici (J1), poređani skoro istim redom kao funkcije, pa se ploča
lako crta. Pinovi su u `config.py` (S-1), pa se na S3 menja samo fajl sa pinovima.

**Šta treba promeniti ili dodati (po važnosti):**

| # | Šta | Zašto | Oznaka |
|---|---|---|---|
| 1 | NRST preko N-MOSFET-a (2N7002), a ne direktno sa GPIO15 | GPIO15 pri uključenju ESP-a daje impuls u nulu od ~60 µs, a to resetuje STM32. Kad ESP nema napajanje, njegov pin drži NRST nisko i STM32 stoji u resetu. | MORA |
| 2 | Otpornik i dioda na LED strani optokaplera za E-STOP | LED u PC817 izdrži 50 mA i 6 V u suprotnom smeru; bez otpornika izgori na naponu baterije | MORA |
| 3 | Pomerač nivoa za NeoPixel (74AHCT1G125) | WS2812 traži bar 0,7·VDD = 3,5 V na DIN-u, ESP daje 3,3 V. Radi „ponekad", posebno ne sa dužim kablom. | MORA |
| 4 | Buzzer: otpornik u bazi/gejtu, pull-down, dioda preko zujalice | Bez pull-down-a zuji dok se ESP pali; bez diode indukcioni napon kvari tranzistor | MORA |
| 5 | Ulaz 5 V: zaštita od obrnutog polariteta, TVS, osigurač (PTC), dioda prema DevKitC 5V pinu | Espressif kaže da su USB, 5V pin i 3V3 pin „međusobno isključivi" izvori napajanja, a mi ćemo imati i USB i bateriju | MORA |
| 6 | Konektori koji ne mogu da se zamene na opasan način | Na slici su tri XH-2 (napajanje 5 V, E-STOP sa naponom baterije, buzzer): E-STOP kabl u buzzer konektoru pusti napon baterije na 5 V liniju | MORA |
| 7 | Lidar MOTOCTL pin (GPIO42) i XH-6 konektor | U planu (faza4 L-2) lidar je na UART2, a konektor na slici nema MOTOCTL | PREPORUKA |
| 8 | Redni otpornici 470 Ω na UART-u ka STM32 | GPIO18 pri uključenju kratko vuče liniju (sudar sa TX-om STM32), a otpornik ograničava i struju kad je jedna strana bez napajanja | PREPORUKA |
| 9 | Drugi I2C (I2C1) za spoljne senzore, ekran ostaje sam na I2C0 | Pokvaren kabl senzora koji drži SDA nisko ne obara ekran i meni; ekran ide na 800 kHz, senzori na 400 kHz | PREPORUKA |
| 10 | Pin za prekid ili XSHUT na konektoru senzora (GPIO39) | Više ToF senzora (VL53L0X/L1X) ima istu adresu 0x29, pa se adresa dodeljuje preko XSHUT-a | PREPORUKA |
| 11 | Merenje baterije (GPIO10 = ADC1) ili INA3221 na I2C | U planu (PROVERA, ROBOT, ikonica); na slici ga nema | OPCIJA |
| 12 | Konektor za proširenje 2×8 sa svim slobodnim pinovima | Pinovi za buduće dodatke (CAN, servo ploča, kamera) bez nove ploče | PREPORUKA |

**Raspored ploče:** za v1 nosač-ploča sa DevKitC-1 na ženskim letvicama (opcija A, 100 × 63 mm, dva sloja).
Ako ekran, tasteri i enkoder stoje zajedno na jednom panelu, prave se dve ploče sa jednim trakastim kablom
(opcija B). ESP modul zalemljen direktno na ploču (opcija C) tek za v2, kad v1 proradi. Skice su u HTML fajlu.

---

## 1. Šta softver danas koristi od hardvera

| Funkcija | WROOM-32 (`config.py`) | S3 (slika) | Kod | Napomena |
|---|---|---|---|---|
| UART ka STM32 | UART2 TX 17, RX 16, 115200 | UART1 TX 17, RX 18, 921600 | `main.py`, `robot.py` | `rxbuf=1024`; STM32 na USART1 (PA9 TX, PA10 RX), i Nucleo i BlackPill |
| Ekran | I2C0 SDA 21, SCL 22, 400 kHz | I2C SDA 8, SCL 9 | `screen.py` | SSD1306 128×64 na 0x3C; bez ekrana sve radi |
| Tasteri | NAZAD 25, OK 26, STOP 27 | T1 4, T2 5, T3 6 | `inputs.py` | na GND, interni pull-up; STOP šalje STOP odmah na pritisak (20 ms debounce) |
| Enkoder | A 32, B 33, SW 14 | 11, 12, 13 | `inputs.py` | hard IRQ, `ENC_STEPS`; na S3 i PCNT (faza4) |
| STM32 NRST / BOOT0 | nije povezano | 15 / 16 | `match.py` (`StmReset`), `stmflash.py` | NRST kao `Pin.OPEN_DRAIN` (0 = reset), BOOT0 `Pin.OUT`; impuls 20 ms |
| E-STOP stanje | - | 7 | (plan) | faza4: samo prikaz i prekid taktike |
| Buzzer | - | 14 | (plan K-2) | PWM |
| NeoPixel | - | 21 | (plan K-1) | boja po stanju meča |
| UART2 | - | 47 / 48 | (plan L-2) | lidar RPLIDAR A2 (faza4) ili kamera/PAMI (slika) |
| WDT, WiFi, upload, telemetrija | da | da | `match.py`, `net.py`, `upload.py`, `telem.py` | antena mora da „vidi" spolja (tačka 8) |

Iz koda koji zavisi od hardvera, a utiče na ploču:
- `match.py`: kad STM32 ostane u starom meču ili se ne javlja 1,5 s u meču, ESP ga resetuje preko NRST-a.
  Znači da **lažni impuls na NRST-u usred meča resetuje pogon** (odometrija se vraća preko RESUME, ali korak
  koji je bio u toku vraća `False`). Zato je tačka 4 (NRST) važna.
- `stmflash.py`: flešovanje STM32 preko WiFi-ja: BOOT0 = 1, NRST impuls, pa AN3155 protokol preko istog UART-a.
- `inputs.py`: STOP reaguje na pritisak, a ne na puštanje, pa smetnja na liniji STOP tastera duža od 20 ms
  zaustavlja robota u meču. Zato su predloženi spoljni pull-up i RC filter (tačka 5.6).

---

## 2. Šta fali na slici u odnosu na softver i planove

1. **Lidar MOTOCTL.** `faza4` L-2: RPLIDAR A2 na UART2, „pin za MOTOCTL (PWM motora)". A2 ima: 5 V, GND,
   TX i RX (3,3 V TTL), MOTOCTL (ulaz, aktivno visoko, PWM; Slamtec navodi 20 kHz, druga tabela 24,5-25 kHz,
   proveriti za vaš model). Konektor na slici (TX, RX, 5V, 3V3, GND) nema MOTOCTL. Predlog: **GPIO42**
   (LEDC PWM), konektor **XH-6** (tačka 7).
2. **UART2 je samo jedan.** S3 ima tri UART-a: UART0 (ROM ispis pri pokretanju, REPL), UART1 (STM32), UART2.
   Na slici je UART2 „kamera, PAMI ili drugi modul", u planu je lidar. Za lidar **i** kameru treba treći
   UART: UART0 preusmeren na druge pinove (firmver bez UART REPL-a; REPL ionako ide preko USB-CDC) ili
   SC16IS752 (I2C → 2 × UART). Na v1 ploči dovoljno je da konektor za proširenje (5.10) ima dva slobodna pina.
3. **Koji taster je koji.** Softver ima NAZAD, OK i STOP, slika T1, T2 i T3 (crven, žut, zelen). Predlog:
   T1 = NAZAD (žuti), T2 = OK (zeleni), T3 = STOP (crveni). Upisati u board fajl i na silkscreen.
4. **Baterija.** U planu (faza4: INA3221; PROVERA i ROBOT stranice, ikonica, „dug zvuk = slaba baterija").
   Dve mogućnosti: INA3221 na I2C (na power ploči ili ovde) ili delitelj na **GPIO10** (ADC1_CH9). ADC2
   (GPIO11-20) ne raditi analogno: deli se sa WiFi-jem. Vidi pitanje 7.
5. **Senzori na I2C (IMU, ToF, senzor boje).** VL53L0X i VL53L1X imaju istu adresu (0x29): za više njih treba
   XSHUT pin po senzoru ili I2C multiplekser (TCA9548A). IMU obično ima INT pin. Konektor na slici ima samo
   SDA, SCL, 3V3 i GND. Predlog: konektor senzora XH-5 sa 5. pinom **GPIO39** (INT ili XSHUT) i mesto za
   TCA9548A (bez lemljenja dok ne zatreba).
6. **Veći ekran (U-3, SSD1309 2,42").** Ti moduli su često 7-pinski (GND, VCC, SCL, SDA, RES, DC, CS); u I2C
   režimu RES mora da dobije impuls posle uključenja (RC na modulu ili GPIO). Predlog: ostaviti mesto za RC
   reset (10 kΩ / 1 µF) na OLED konektoru ili koristiti slobodan pin sa konektora za proširenje.
7. **LED-ovi na UART linijama.** Na slici LED ide sa linije na GND: UART u mirovanju drži 1, pa LED stalno
   svetli i samo trepne pri prenosu. Bolje: LED od 3V3 preko 2,2-4,7 kΩ na liniju (svetli na nulama, tj.
   kad ima saobraćaja) ili preko bafera (74LVC2G34). Mogu i da se izostave: stranica VEZA već pokazuje vezu.
8. **ESP reset spolja.** Ako je DevKitC zatvoren u robotu, EN pin (J1-3) izvesti na konektor za proširenje
   (spoljni taster za reset ESP-a).
9. **Činč** je na STM32 (Nucleo PA12), ESP ga vidi preko STATUS-a. Direktna veza do ESP-a nije potrebna;
   ako se ikad zatraži, ide preko konektora za proširenje.

---

## 3. Provera izbora pinova

### 3.1 Pinovi koji se ne koriste na DevKitC-1 N16R8

| Pinovi | Zašto |
|---|---|
| 0, 3, 45, 46 | strapping (režim pokretanja, JTAG izvor, napon VDD_SPI); GPIO0 je taster BOOT |
| 19, 20 | nativni USB (D-, D+): REPL i mpremote preko USB-CDC |
| 43, 44 | UART0: drugi USB-C (USB-UART čip) i ROM ispis pri pokretanju |
| 26-32 | interni fleš (nisu izvedeni) |
| 35, 36, 37 | octal PSRAM kod N16R8 (izvedeni na J3, ali zauzeti) |
| 38 | RGB LED na DevKitC-1 v1.1 |
| 48 | RGB LED na DevKitC-1 **v1.0** (na v1.1 je slobodan) |

### 3.2 Pin po pin

| GPIO | J1/J3 | Funkcija (slika) | Ocena | Napomena |
|---|---|---|---|---|
| 4, 5, 6 | J1-4..6 | T1, T2, T3 | ✅ | ADC1 pinovi „potrošeni" na tastere; ok jer ostaju 1, 2, 10 |
| 7 | J1-7 | E-STOP | ✅ | |
| 15 | J1-8 | NRST | ⚠️ | XTAL_32K_P: impuls u nulu ~60 µs pri uključenju. STM32 NRST propušta impuls duži od ~300 ns. Direktno vezan = reset STM32 kad se ESP uključi ili kad napon ESP-a padne (brownout). Rešenje: MOSFET (tačka 4); tada je impuls u nulu bezopasan. |
| 16 | J1-9 | BOOT0 | ✅ | isti impuls u nulu, a nula je bezbedno stanje za BOOT0 |
| 17 | J1-10 | UART1 TX | ✅ | impuls u nulu pri uključenju = jedan pogrešan bajt; COBS okvir to preživi (0x00 je kraj okvira) |
| 18 | J1-11 | UART1 RX | ⚠️ | impuls u 0 ili 1 pri uključenju: pin kratko gura liniju protiv TX-a STM32. Rešenje: 470 Ω redno. |
| 8, 9 | J1-12, J1-15 | I2C SDA, SCL | ✅ | između njih su 3 i 46 (strapping): ne vezivati ništa na njih |
| 11, 12, 13 | J1-17..19 | enkoder | ✅ | PCNT radi na bilo kom pinu |
| 14 | J1-20 | buzzer | ✅ | impuls u nulu = tranzistor ugašen, bezopasno |
| 21 | J3-18 | NeoPixel | ✅ | bez impulsa pri uključenju |
| 47, 48 | J3-17, 16 | UART2 | ⚠️ | 48 = RGB LED na v1.0 ploči (LED bi treptao od podataka). Oba pina su u naponskom domenu VDD_SPI: 3,3 V kod N16R8, ali **1,8 V** kod varijanti sa 1,8 V memorijom (npr. R8V, R16V). Ne menjati modul bez provere. |

Izvor za impulse pri uključenju: Espressif „Schematic Checklist" za ESP32-S3 (tabela Power-up glitches):
GPIO1-14, XTAL_32K_P/N (15, 16) i 17 imaju impuls u nulu ~60 µs, GPIO18 u nulu ili jedinicu, 19 i 20 po dva.

### 3.3 Slobodni pinovi posle plana

| GPIO | J1/J3 | Predlog |
|---|---|---|
| 10 | J1-16 | VBAT preko delitelja (ADC1_CH9), ili slobodan na konektoru za proširenje |
| 1, 2 | J3-4, 5 | ADC1: analogna rezerva (struja, potenciometar, IR analogni) na konektoru za proširenje |
| 42 | J3-6 | LIDAR MOTOCTL (PWM) |
| 41, 40 | J3-7, 8 | I2C1 SDA, SCL (senzori) |
| 39 | J3-9 | INT ili XSHUT senzora |
| 38 | J3-10 | samo ako se RGB LED na v1.1 ne koristi (na konektor za proširenje preko kratkospojnika) |

GPIO39-42 su i JTAG pinovi, ali S3 podrazumevano koristi JTAG preko USB-a, pa su slobodni. Analogni ulazi koji
rade uz WiFi (ADC1) su samo GPIO1-10; od njih ostaju 1, 2 i 10. Zato se na njih ne stavlja ništa digitalno.

### 3.4 Gde su pinovi na ploči (važno za raspored)

DevKitC-1 (letvice 2 × 22, korak 2,54 mm; ploča 62,7 × 25,4 mm; razmak redova proveriti u Espressif DXF-u):

    J1 (levo, od antene ka USB-u):  3V3 3V3 RST | 4 5 6 | 7 | 15 16 | 17 18 | 8 3 46 9 | 10 | 11 12 13 | 14 | 5V G
    J3 (desno, od antene ka USB-u): G 43 44 | 1 2 | 42 41 40 39 | 38 37 36 35 0 45 | 48 47 | 21 | 20 19 G G

Sve od plana osim NeoPixela i UART2 je na J1, i to redom: tasteri, E-STOP, NRST i BOOT0, UART, I2C,
enkoder, buzzer, pa 5V. Ako se konektori poređaju oko leve strane ploče istim redom, veze se ne ukrštaju.
J3 strana dobija senzore (I2C1), lidar, NeoPixel i konektor za proširenje.

**Zaključak:** pinovi ostaju kako su na slici; menja se samo način vezivanja NRST-a (MOSFET) i dodaju se
pinovi 42, 41, 40, 39 (i opciono 10).

---

## 4. NRST i BOOT0 na odvojenom konektoru

Odvojeni konektor je dobra ideja:
- **BlackPill (test robot)** koristi samo UART (ulazak u bootloader komandom ENTER_BOOTLOADER), pa se kabl za
  NRST i BOOT0 ne vezuje.
- **Bezbednost u meču:** izvučen kabl znači da ESP ne može da resetuje pogon ni u slučaju greške u softveru.
  To je najjednostavniji hardverski „isključi" za tu funkciju.
- **Različiti kablovi i dužine:** UART može da ide na jednu ploču, a NRST i BOOT0 na morpho letvicu Nucleo-a.

### 4.1 Šema (slika u HTML fajlu)

**NRST [MORA]:**

    GPIO15 ──[1 kΩ]──┬── G   Q1 2N7002 (ili BSS138)
                     │    D ─────────────── J_CTRL-2 (NRST) ──> Nucleo CN7-14 (ili CN6-3 RESET)
                  [100 kΩ] S ── GND
                     │
                    GND

- GPIO = 1 → Q1 provodi → NRST = 0 (reset). GPIO = 0, ESP se restartuje ili je bez napajanja → gejt na
  GND preko 100 kΩ → Q1 ne provodi → STM32 radi.
- Impuls u nulu na GPIO15 pri uključenju sada nema efekta. Neutralizuje se i problem kad ESP nema napajanje
  (zaštitne diode pina bi držale NRST na ~0,6 V, a to je za STM32 nula).
- Pull-up za NRST postoji u STM32 (~40 kΩ) i na Nucleo-u (sa 100 nF); na ploču se ne stavlja.
- Druga mogućnost bez izmene softvera: 74LVC1G07 (open-drain bafer koji je u visokoj impedansi kad je bez
  napajanja) + RC filter 10 kΩ / 100 nF na ulazu (guši impuls od 60 µs, a propušta impuls od 20 ms). Više
  delova za istu stvar; MOSFET je jednostavniji.

**BOOT0 [MORA]:**

    GPIO16 ──[470 Ω]──┬────────────── J_CTRL-3 (BOOT0) ──> Nucleo CN7-7
                     [10 kΩ]  (pull-down; Nucleo ima svoj ~10 kΩ, MB1136, proveriti na svojoj reviziji)
                      │
                     GND

- Sa oba pull-down-a (5 kΩ ukupno): 3,3 V · 5 / 5,47 ≈ 3,0 V kad ESP drži 1. Dovoljno.
- Kad ESP nema napajanje ili se pali, BOOT0 ostaje 0 (pull-down). Opciono žuti LED „BOOT0" preko 2N7002.

**Konektor J_CTRL:** JST-PH 3 pina (ili GH): 1 GND, 2 NRST, 3 BOOT0. Na Nucleo strani: CN7-8 (GND),
CN7-14 (NRST), CN7-7 (BOOT0); RESET je i na Arduino letvici CN6-3.

**Konektor J_UART (odvojen):** JST-PH 3 pina: 1 GND, 2 TX (GPIO17 → PA10, Arduino D2), 3 RX (GPIO18 ← PA9,
D8). Redno 470 Ω na obe linije, kod ESP-a. Na 921600 baud-a: 470 Ω × ~50 pF ≈ 25 ns, bit traje 1,08 µs.

Zamena J_CTRL i J_UART kablova nije opasna (obe strane su 3,3 V signali sa otpornicima), samo ne radi.

### 4.2 Softver za NRST i BOOT0 (za kasnije, tačka 10)
- `match.StmReset` i `stmflash.flash_file`: NRST postaje običan izlaz sa obrnutom logikom (1 = reset).
  Predlog: `STM_NRST_ACTIVE = 1` u board fajlu; isti kod radi i za direktno vezan pin (`0`).
- `stmflash.flash_file` koristi `uart_args` sa `cfg.UART_BAUD`. Ugrađeni bootloader STM32 (AN2606) prepoznaje
  brzinu samo do 115200; kad UART pređe na 921600, za flešovanje treba privremeno 115200.

---

## 5. Blok po blok: šta ide na ploču

### 5.1 Napajanje [MORA]
- Ulaz 5 V iz DC-DC-a (≥ 3 A, vidi tačku 6) na konektor koji ne liči na signalne (XT30 ili 2-polna stezaljka).
- Zaštita od obrnutog polariteta: P-MOSFET (npr. AO3401A) ili Schottky dioda (pad ~0,4 V, jednostavnije).
- TVS SMBJ5.0A preko ulaza (skokovi napona kad se motori pale i gase), PTC osigurač 3 A, 470 µF / 10 V + 10 µF + 100 nF.
- **DevKitC 5V pin preko Schottky diode (ili idealne diode, LM66100).** Espressif: USB, 5V pin i 3V3 pin su
  međusobno isključivi izvori. Sa diodom: kad je priključen samo USB (sto u radionici), USB ne napaja
  NeoPixel i lidar preko 5V pina; kad je priključena baterija, 5 V iz DC-DC-a ne ide nazad u USB.
  Pad na diodi (~0,4 V) ne smeta: LDO na DevKitC-u od 4,6 V i dalje daje 3,3 V.
- NeoPixel i lidar ne napajati preko DevKitC-a: direktno sa 5 V ulaza, svaki preko svog PTC-a (1,5 A i 1 A),
  da kratak spoj u kablu ne obori ESP.
- 3,3 V za spoljne uređaje: LDO na DevKitC-u napaja i ESP (WiFi vršno ~350-500 mA). Spolja ne vući više od
  ~200-300 mA. Za više (više ToF senzora, kamera na 3,3 V) [OPCIJA]: zaseban 3V3_AUX LDO (AP2112K-3.3 ili
  TLV75533, 500-600 mA) samo za I2C1 i UART2 konektore.

### 5.2 E-STOP preko optokaplera [MORA]
- LED strana: E-STOP+ → R → PC817 anoda; katoda → E-STOP−. 1N4148 suprotno, paralelno sa LED-om (zaštita od
  obrnutog napona, LED izdrži samo 6 V).
- R = (Vbat_max − 1,2 V) / 5 mA: 2S (8,4 V) 1,5 kΩ; 3S (12,6 V) 2,2 kΩ; 4S (16,8 V) 3,3 kΩ; 6S (25,2 V) 4,7 kΩ
  0,25 W (1206). Opciono Zener na red (npr. 6,8 V), da se „prazna" ili isključena linija ne vidi kao uključena.
- Izlaz: kolektor → GPIO7 + 10 kΩ pull-up na 3V3 + 100 nF na GND; emiter → GND.
- Logika: motori pod naponom → LED svetli → GPIO7 = 0. E-STOP pritisnut **ili kabl prekinut** → GPIO7 = 1,
  pa se prekid kabla vidi kao pritisnut E-STOP (bezbedna strana).
- Na ploči: E-STOP konektor i LED strana optokaplera u ćošku, odvojeni od ostatka (razmak ≥ 2 mm, bez
  razlivenog bakra ispod optokaplera između strana).

### 5.3 Buzzer [MORA]
- Ne zna se da li je aktivan ili pasivan, magnetni ili piezo (pitanje 6). Plan K-2 kaže PWM: pasivni.
- Predlog: N-MOSFET (AO3400A ili 2N7002 do ~200 mA) sa niske strane: GPIO14 → 100 Ω → gejt, 100 kΩ gejt → GND,
  buzzer između +5V i drejna, 1N4148 (ili BAT54) preko buzzera, opciono 10-47 Ω na red (jačina).
- Ako ostaje BC547 sa slike: 1 kΩ u bazi, 10 kΩ baza → GND, ista dioda.
- PWM na rezonantnoj frekvenciji buzzera (obično 2,7 ili 4 kHz).

### 5.4 NeoPixel [MORA]
- GPIO21 → 74AHCT1G125 (napajan sa 5 V, OE na GND) → 330 Ω → DIN. AHCT prima 3,3 V kao jedinicu (prag 2 V),
  a daje 5 V.
- Na konektoru: 470-1000 µF / 10 V, PTC 1,5 A. Struja: do 60 mA po LED-u na punoj beloj (12 LED = 0,7 A,
  16 LED = 1 A); softver ograničava svetlinu (plan K-1), ali osigurač mora da izdrži najgori slučaj.

### 5.5 I2C [PREPORUKA]
- **I2C0 (GPIO8, 9) samo za ekran**, kratak kabl. Pull-up 2,2 kΩ (za 800 kHz, T-3). ESP32-S3 I2C radi do
  800 kbit/s (TRM), ne do 1 MHz. Modul ekrana ima svoj pull-up (obično 4,7 ili 10 kΩ); paralelno sa 2,2 kΩ
  je i dalje ispod 3 mA struje kad je linija u nuli.
- **I2C1 (GPIO41 SDA, 40 SCL) za spoljne senzore**, 400 kHz, pull-up 4,7 kΩ. Kvar na kablu senzora ne obara
  ekran i meni. Ako se ostane na jednom bus-u kao na slici: pull-up 2,2 kΩ i 400 kHz.
- Konektori senzora: XH-5 (1 GND, 2 3V3, 3 SCL, 4 SDA, 5 INT/XSHUT = GPIO39). Mesto za TCA9548A [OPCIJA].
- Konektor nikad ne daje 5 V na I2C konektoru: modul sa pull-up-om na 5 V bi doveo 5 V na pin ESP-a.
- 100 nF na 3V3 pinu svakog konektora.

### 5.6 Tasteri [PREPORUKA]
- Interni pull-up S3 je ~45 kΩ; sa dugim kablom pored motora to je slabo. Na ploči: 10 kΩ pull-up na 3V3,
  1 kΩ redno (ESD), 100 nF na GND (RC ≈ 1 ms, softver ionako čeka 20 ms).
- Najvažniji je STOP (reaguje na pritisak): smetnja ne sme da ga „pritisne".

### 5.7 Enkoder [PREPORUKA]
- KY-040 ima svoje pull-up-ove 10 kΩ na „+". Na ploči: mesto za 10 kΩ pull-up (bez lemljenja ako je KY-040),
  10 kΩ redno i 10 nF na GND na A i B (Bourns preporuka za PEC11, RC ≈ 100 µs). Za SW: kao taster.
- 10 nF sa slike bez rednog otpornika: kontakt enkodera direktno prazni kondenzator (varničenje kontakta);
  redni otpornik to sprečava.

### 5.8 UART2 i lidar [PREPORUKA]
- Konektor XH-6: 1 GND, 2 5V, 3 TX (GPIO47), 4 RX (GPIO48), 5 MOTOCTL (GPIO42), 6 3V3.
- Redno 220-470 Ω na TX i RX. 5 V preko PTC 1 A + 100 µF. Lidar A2 troši reda 0,5 A, više pri startu
  motora (proveriti datasheet za A2M8 ili A2M12; A2M8 radi na 115200, A2M12 na 256000).
- Softver (faza4 L-2): UART rxbuf ≥ 4 KB (A2 šalje ~20 KB/s, krug petlje do ~45 ms).

### 5.9 Zaštita svih spoljnih signala [PREPORUKA]
- Redni otpornik (100 Ω-1 kΩ) na svakom signalu koji izlazi sa ploče, blizu konektora.
- ESD diode (npr. TPD4E05U06 ili PESD5V0S1BA) na konektorima do kojih ruke dolaze (tasteri, enkoder, ekran).
- 100 nF na svakom pinu za napajanje na konektoru.

### 5.10 Konektor za proširenje [PREPORUKA]
Kutijasti 2 × 8 (2,54 mm, sa ključem):

| Pin | Signal | Pin | Signal |
|---|---|---|---|
| 1 | GND | 2 | GND |
| 3 | 3V3 | 4 | 5V (preko PTC 1 A) |
| 5 | I2C1 SDA (41) | 6 | I2C1 SCL (40) |
| 7 | GPIO1 (ADC1) | 8 | GPIO2 (ADC1) |
| 9 | GPIO39 | 10 | GPIO10 (ADC1, ako nije VBAT) |
| 11 | UART2 TX (47) | 12 | UART2 RX (48) |
| 13 | GPIO42 | 14 | GPIO38 (kratkospojnik, samo bez RGB LED-a) |
| 15 | EN (reset ESP-a) | 16 | GND |

Šta može da ide na njega: CAN/TWAI (SN65HVD230 na maloj ploči, bilo koja 2 pina), servo ploča (PCA9685 na
I2C1), više ToF senzora sa XSHUT-om, kamera, drugi lidar, spoljni taster za reset ESP-a.

---

## 6. Napajanje i struja (procena)

| Potrošač | 5 V (mA), tipično | najviše | Napomena |
|---|---|---|---|
| ESP32-S3 + PSRAM (preko LDO-a na DevKitC) | 120 | 500 | WiFi slanje do ~350 mA na 3,3 V |
| OLED 0,96" / 2,42" | 20 | 40 | |
| NeoPixel (12-16 LED) | 100-200 | 700-1000 | puna bela; softver ograničava svetlinu |
| Lidar RPLIDAR A2 | 450 | 600 + start | proveriti datasheet |
| Buzzer | 30 | 60 | |
| Senzori I2C (IMU, 2-3 ToF, boja) | 50 | 100 | na 3,3 V |
| Kamera (opciono, na UART2) | 150-300 | 400 | zavisi od kamere |
| **Ukupno** | **~1 A** | **~2,5-3 A** | DC-DC 5 V **≥ 3 A**, bolje 5 A ako napaja još nešto |

Šema napajanja je i u HTML fajlu (dijagram).

---

## 7. Konektori

**Pravilo:** konektori istog tipa i istog broja pinova imaju napajanje na istim pozicijama (ili ga nemaju), a
pin 1 je uvek GND. Onda pogrešno uključen kabl menja samo signale (3,3 V ulazi sa otpornikom), a ne pušta
napajanje na signal ili na GND. Napajanje i E-STOP (napon baterije) idu na konektore drugog tipa.

Zašto: na slici su XH-2 za napajanje 5 V, E-STOP i buzzer. E-STOP kabl (napon baterije) u konektoru za
buzzer: E-STOP+ ide na drejn tranzistora, pa kroz buzzer (i diodu) pravo na 5 V liniju ESP-a, a E-STOP− spaja
5 V sa GND-om. XH-5 enkodera
i UART2 sa slike: enkoder u UART2 konektoru dobija 5 V na SW, pritisak na dugme pravi kratak spoj na 5 V.
Kabl tastera u I2C konektoru: T3 je na 3V3, pa pritisak na taster T3 kratko spaja 3V3 sa GND.

| Konektor | Tip | Pinovi | Napomena |
|---|---|---|---|
| PWR_IN | XT30 ili stezaljka 5,08 mm | +5V, GND | jedini takav |
| ESTOP | stezaljka 3,5 mm, 2 pina (ili JST-VH) | E-STOP+, E-STOP− | domen baterije, u ćošku |
| STM_UART | JST-PH 3 | 1 GND, 2 TX→PA10, 3 RX←PA9 | 470 Ω redno |
| STM_CTRL | JST-PH 3 | 1 GND, 2 NRST, 3 BOOT0 | odvojen (tačka 4) |
| OLED (I2C0) | XH-4 | 1 GND, 2 3V3, 3 SCL, 4 SDA | isti redosled kao većina OLED modula (GND VCC SCL SDA) |
| TASTERI | XH-5 | 1 GND, 2 3V3, 3 T1, 4 T2, 5 T3 | 3V3 za tastere sa LED-om, inače prazan |
| ENKODER | XH-5 | 1 GND, 2 3V3, 3 SW, 4 B (DT), 5 A (CLK) | obrnut redosled od KY-040 (CLK DT SW + GND) |
| SENZORI ×2 (I2C1) | XH-5 | 1 GND, 2 3V3, 3 SCL, 4 SDA, 5 INT/XSHUT | isti profil kao tasteri i enkoder |
| BUZZER | XH-2 | 1 BUZ−, 2 +5V | jedini XH-2 |
| NEOPIXEL | XH-3 | 1 GND, 2 +5V, 3 DIN | jedini XH-3 |
| LIDAR / UART2 | XH-6 | 1 GND, 2 5V, 3 TX, 4 RX, 5 MOTOCTL, 6 3V3 | jedini XH-6 |
| PROŠIRENJE | kutijasti 2×8 | tačka 5.10 | sa ključem |

JST-XH ima samo blagu kopču, a vibracije u robotu ga mogu izvući. Za kablove koji idu daleko (STM32, lidar)
bolji je JST-PH ili GH (GH ima pravu bravicu, ali traži klešta za krimpovanje). Na Nucleo strani su muški
pinovi: kabl sa Dupont kućištem ili (bolje) isti PH konektor na ploči pogona.

---

## 8. Raspored ploče: opcije

Skice su u [`esp32s3-pcb-skice.html`](esp32s3-pcb-skice.html).

### A. Nosač-ploča sa DevKitC-1 (preporuka za v1)
100 × 63 mm, dva sloja. DevKitC u sredini na ženskim letvicama 2 × 22, antena na gornjoj ivici iznad izreza
u ploči, USB-C na donjoj ivici (dostupni spolja). Leva „krila" prate J1: gore E-STOP i tasteri, levo
STM_CTRL, STM_UART, OLED, enkoder, dole buzzer i 5 V ulaz (5V pin DevKitC-a je baš tu, J1-21). Desno
krilo prati J3: gore konektor za proširenje, desno senzori (I2C1), dole lidar i NeoPixel. 5 V za NeoPixel i
lidar ide širokim vodom po donjem sloju ispod DevKitC-a.
- Za: DevKitC se menja za minut, USB za razvoj ostaje, najmanje rizika, ispod 100 × 100 mm (najjeftinija
  izrada).
- Protiv: letvice su visoke (~8,5 mm + DevKitC), treba držač protiv vibracija (vezica kroz dve rupe ili
  odštampan klin), sve od korisničkog interfejsa ide kablovima.

### B. Nosač-ploča + ploča panela (ako je korisnički interfejs na jednom panelu)
Nosač kao A, bez konektora za tastere, enkoder, OLED, buzzer i NeoPixel; umesto njih jedan kutijasti 2×8
(16 žila trakastog kabla, GND između brzih signala). Panel: OLED, 3 tastera, enkoder i buzzer zalemljeni
direktno, konektor za NeoPixel prsten.
- Za: jedan kabl umesto pet, tasteri i enkoder bez letećih žica, panel se menja nezavisno.
- Protiv: dve ploče; trakasti kabl mora da se učvrsti; panel zavisi od mehanike (rupe za tastere).
- Žile (16): 5V, 5V, GND, GND, GND, 3V3, SDA, SCL, T1, T2, T3, ENC A, ENC B, ENC SW, BUZ, NEO DIN (5 V,
  posle pomerača nivoa na nosaču). Buzzer drajver i NeoPixel kondenzator na panelu.

### C. ESP32-S3-WROOM-1-N16R8 zalemljen na ploču (v2)
~70 × 50 mm. Modul na ivici (antena van ploče ili bez bakra ispod), USB-C (nativni USB, ESD zaštita USBLC6-2),
sopstveni 3,3 V regulator (1 A), EN RC (10 kΩ / 1 µF), tasteri BOOT i RESET. USB-UART čip nije potreban:
MicroPython i flešovanje rade preko nativnog USB-a.
- Za: najmanja i najotpornija (nema letvica), sve na jednom mestu.
- Protiv: više projektovanja (regulator, USB, EN, strapping), pokvaren modul = lemljenje; raditi tek kad v1
  potvrdi šemu.

### D. Matična ploča: Nucleo + ESP na istoj ploči
~160 × 100 mm. Nucleo ide u ženske morpho letvice, DevKitC pored. UART, NRST i BOOT0 su vodovi na ploči.
- Za: nema kablova između ESP-a i STM32.
- Protiv: velika ploča, logika i snaga motora na istoj ploči, deo je ploča pogona (Lea), i ne slaže se sa
  odvojenim konektorom za NRST i BOOT0. Za razgovor, ne za v1.

**Preporuka:** A (ili A + B ako je korisnički interfejs na panelu) za 2027. C posle sezone, kad se šema potvrdi.

---

## 9. Smernice za crtanje

- **Antena:** ni bakra ni delova ispod antene modula i ~15 mm oko nje, na oba sloja. Najbolje izrez u ploči
  ispod antene (između letvica, ~19 mm širine) ili antena preko ivice. U robotu: ESP na gornjem nivou, ne
  pored baterije, motora ni metalnih ploča. Ako je kućište od metala ili karbona: varijanta sa spoljnom
  antenom (WROOM-1U, U.FL), proveriti da li postoji DevKitC-1U u potrebnoj memorijskoj varijanti.
- **Masa:** donji sloj ceo GND (izrez samo ispod antene). Gornji sloj: signali, posle toga GND razliven i
  povezan vijama na svakih ~10 mm.
- **5 V:** glavni vod ≥ 1,5 mm (3 A, bakar 35 µm), grane od 1 A ≥ 0,5 mm; svaki NeoPixel i lidar konektor
  sa svojim kondenzatorom.
- **E-STOP zona:** konektor i ulaz optokaplera u ćošku, ≥ 2 mm do ostalog bakra, oznaka na silkscreen-u.
- **Letvice DevKitC-a:** ženske 2 × 22 visine 8,5 mm; ispod DevKitC-a samo SMD delovi; prolaz za USB-C utikač
  na donjoj ivici bez visokih delova; 2 rupe za vezicu ili klin protiv vibracija. Razmak redova letvica uzeti
  iz Espressif DXF crteža (forum navodi 22,86 mm; nije zvanično potvrđeno).
- **Rupe:** 4 × M3 u ćoškovima; ako je šasija od metala, rupe bez veze sa GND (ili preko 0 Ω da može da se bira).
- **Merne tačke:** 5V, 3V3, GND, TX, RX, NRST, BOOT0, SDA0, SCL0, NEO_DIN, GPIO7.
- **LED-ovi:** 5V (zeleni), 3V3 (zeleni), BOOT0 (žuti), opciono TX/RX aktivnost (tačka 2.7).
- **Silkscreen:** ime i raspored pinova pored svakog konektora, pin 1, funkcija tastera (NAZAD, OK, STOP),
  verzija ploče, „ESP32-S3-DevKitC-1 N16R8" i strelica za smer umetanja.
- **Izrada:** JLCPCB 2 sloja, ≤ 100 × 100 mm, delovi 0805 i SOT-23 (lako se leme ručno; isti delovi postoje za
  JLC montažu).

---

## 10. Izmene softvera kad ploča bude gotova (za odobrenje; ovde nije rađeno)

1. **S-1 board fajl** `board_s3.py`: svi pinovi sa slike + `LIDAR_MOTOCTL=42`, `I2C1_SDA=41`, `I2C1_SCL=40`,
   `SENS_INT=39`, `VBAT_ADC=10` (ako se uradi), `STM_NRST_ACTIVE=1`, `ESTOP_ACTIVE=1` (1 = pritisnut),
   `UART_ID=1`, mapiranje T1/T2/T3 → `BTN_BACK/BTN_OK/BTN_STOP`.
2. `match.StmReset` i `stmflash.flash_file`: NRST sa obrnutom logikom (MOSFET), BOOT0 isto kao sada.
3. `stmflash.flash_file`: bootloader uvek na 115200, nezavisno od `UART_BAUD`.
4. `screen.py`: frekvencija I2C iz board fajla (800 kHz tek sa pull-up-om 2,2 kΩ).
5. E-STOP (GPIO7): prikaz na PROVERA/ROBOT, prekid taktike; ulaz sa pull-up-om i 20 ms filtrom kao tasteri.
6. NeoPixel (K-1) i buzzer (K-2) prema planu; svetlina ograničena u podešavanjima.
7. Lidar (L-1..L-3): UART2 sa rxbuf ≥ 4 KB, MOTOCTL kao PWM 20-25 kHz.
8. Host testovi: board fajl ima sve pinove, nijedan pin se ne ponavlja, nijedan nije iz zabranjene liste (3.1).

---

## 11. Pitanja

1. **Napon baterije** (2S, 3S, 4S, 6S)? Treba za otpornik u E-STOP-u i za delitelj VBAT-a.
2. **Da li su GND baterije i GND logike isti** (obični DC-DC bez izolacije)? Ako jesu, VBAT može direktno preko
   delitelja na ADC; ako ne, samo preko INA na power ploči.
3. **Nucleo:** na posebnoj ploči (kabl, koliko dug?) ili da razmotrimo matičnu ploču (D)? Da li ploča pogona
   ima mesto za PH konektor umesto Dupont žica?
4. **Korisnički interfejs:** da li su ekran, tasteri i enkoder na jednom panelu (opcija B)? Gde je NeoPixel
   (traka ili prsten, koliko LED-ova)?
5. **Koja revizija DevKitC-1** (v1.0 ili v1.1, piše na ploči)? Na v1.0 GPIO48 vozi RGB LED.
6. **Buzzer:** aktivni ili pasivni, magnetni ili piezo, 5 V?
7. **Baterija:** INA3221 na I2C (gde: ovde ili na power ploči) ili delitelj na GPIO10?
8. **UART2:** lidar (A2M8 ili A2M12?) ili kamera/PAMI? Ako oba: treći UART (tačka 2.2).
9. **Izrada:** JLCPCB, 2 sloja? Ručno lemljenje ili montaža kod proizvođača?
10. **Mehanika:** najveće dimenzije ploče, gde je u robotu, ima li metala oko antene?
11. **DC-DC:** koji modul i koliko struje daje?
12. Da li STOP taster treba da ide i direktno na STM32 (radi i kad je ESP zaglavljen, pre nego što WDT
    restartuje ESP za 3 s)? Ako da: još jedan pin na STM_CTRL konektoru.

---

## Izvori
- [ESP32-S3-DevKitC-1 v1.1 user guide](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/user_guide_v1.1.html):
  raspored J1 i J3, RGB LED (v1.0 GPIO48, v1.1 GPIO38), GPIO35-37 i octal PSRAM, „mutually exclusive" napajanje.
- [ESP32-S3 Schematic Checklist](https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32s3/schematic-checklist.html):
  strapping, impulsi pri uključenju, ADC1, EN RC.
- [ESP32-S3 datasheet](https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf):
  GPIO47/48 (SPICLK_P/N) u domenu VDD_SPI, 1,8 V kod R8V/R16V; interni pull-up ~45 kΩ. Forum:
  [GPIO47/48 1,8 V](https://esp32.com/viewtopic.php?p=115415).
- [PCB crtež DevKitC-1](https://dl.espressif.com/dl/PCB_ESP32-S3-DevKitC-1_V1_20210312CB.pdf) (62,74 × 25,4 mm),
  [KiCad forum: razmak letvica](https://forum.kicad.info/t/pin-distance-in-esp32-s3-devkitc-1/71001).
- [UM1724 Nucleo-64](https://www.st.com/resource/en/user_manual/um1724-stm32-nucleo64-boards-mb1136-stmicroelectronics.pdf),
  [šema MB1136](https://pages.hmc.edu/brake/class/e155/fa21/assets/doc/Nucleo-64_Schematic_MB1136.pdf): CN7-7 BOOT0,
  CN7-14 NRST, BOOT0 podrazumevano 0 (10 kΩ).
- STM32F401 datasheet: NRST filtrira impulse < 100 ns, propušta > 300 ns; interni pull-up ~40 kΩ.
  AN2606: USART bootloader na PA9/PA10, prepoznavanje brzine do 115200.
- [Slamtec RPLIDAR A2 manual](https://manuals.plus/slamtec/rplidar-a2-low-cost-360-degree-laser-range-scanner-manual):
  5 V, TX/RX 3,3 V, MOTOCTL aktivno visoko, PWM.
- WS2812B datasheet (VIH = 0,7·VDD), PC817 datasheet (IF 50 mA, VR 6 V), 74AHCT1G125 (VIH 2 V na 5 V),
  Bourns PEC11 (preporučeno kolo enkodera).
