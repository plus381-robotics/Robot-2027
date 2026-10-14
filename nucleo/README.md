# nucleo — STM32 Nucleo F401RE (kretanje)

Bare-metal firmware: odometrija sa pasivnih točkova, regulacija na 1 kHz, profil kretanja,
heartbeat, IWDG, tajmer meča. Sa RPi-jem komunicira preko USB-a (ST-LINK VCP, USART2,
460,800 bps) protokolom iz `protocol/`.

Polazna osnova je prošlogodišnji `PogonskiSTM-2026-BlackPill`, uz ispravke iz analize
(provera CRC-a, heartbeat, fault handleri, `float` umesto `double`, enkoderi TI12, HSE takt).

## Struktura

```
nucleo/
├── firmware/       CubeMX projekat sa CMake toolchain-om (glavni firmware)
└── echo_test/      echo za test USB veze (privremeno, koristi tools/echo_test.py)
```

## Pravljenje projekta u CubeMX-u (jednom)

1. **New Project → Board Selector → NUCLEO-F401RE**, na pitanje o podrazumevanoj inicijalizaciji: *Yes*.
2. **RCC:** HSE = *BYPASS Clock Source* (8 MHz sa ST-LINK-a). **Clock Configuration:** izvor PLL = HSE,
   SYSCLK = 84 MHz, APB1 = 42 MHz, APB2 = 84 MHz.
3. **SYS:** Debug = *Serial Wire*.
4. **USART2:** Asynchronous, 460800, 8N1. **DMA Settings:** dodati `USART2_RX` i `USART2_TX`, oba *Normal*.
   **NVIC:** uključiti *USART2 global interrupt*.
5. **Project Manager:**
   - Project Name: `firmware`, Project Location: `<repo>/nucleo`
   - Toolchain / IDE: **CMake**
   - Code Generator: *Copy only the necessary library files*
6. **Generate Code.**

`.ioc` fajl je izvor istine za konfiguraciju pinova i periferija i commituje se. Posle svake izmene
u CubeMX-u commituju se i `.ioc` i regenerisani fajlovi.

## Echo test (prvi firmware)

U `firmware/CMakeLists.txt`, u delu za korisničke izvore (CubeMX ga čuva pri regenerisanju):

```cmake
target_sources(${CMAKE_PROJECT_NAME} PRIVATE
    ${CMAKE_SOURCE_DIR}/../echo_test/echo_test.c)
target_include_directories(${CMAKE_PROJECT_NAME} PRIVATE
    ${CMAKE_SOURCE_DIR}/../echo_test
    ${CMAKE_SOURCE_DIR}/../../protocol/include)
```

U `Core/Src/main.c`:

```c
/* USER CODE BEGIN Includes */
#include "echo_test.h"
/* USER CODE END Includes */

/* USER CODE BEGIN 2 */
echo_test_start();
/* USER CODE END 2 */
```

Pisati samo između `USER CODE BEGIN` / `END` komentara, inače CubeMX briše izmene pri regenerisanju.

## Build i flešovanje

Na laptopu (STM32 VS Code ekstenzija ili terminal) i na RPi-ju isto:

```bash
cd nucleo/firmware
cmake --preset Release
cmake --build --preset Release
```

Flešovanje sa RPi-ja preko SSH-a (Nucleo priključen USB-om):

```bash
./tools/flash_nucleo.sh            # flešuje nucleo/firmware/build/Release/firmware.elf
./tools/flash_nucleo.sh --build    # prvo build, pa flešovanje
```

Na RPi-ju je za build potreban `gcc-arm-none-eabi` (instalira ga `rpi/system/setup.sh`).

## Pinovi

Raspored je definisan u `.ioc` fajlu i na dijagramu povezivanja. Rezervisano na Nucleo ploči:
PA2/PA3 (USART2 ↔ ST-LINK), PA5 (LD2), PA13/PA14 (SWD), PC13 (taster B1), PH0 (HSE bypass).
