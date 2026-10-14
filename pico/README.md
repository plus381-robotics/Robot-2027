# pico — Raspberry Pi Pico / RP2040 (I/O hab)

Pumpe i ventili, servo motori, napon baterije, prekidač strane, OLED 1.3" (SH1106),
rotary enkoder sa dugmetom i NeoPixel status. Sa RPi-jem komunicira preko USB CDC-a,
istim protokolom kao Nucleo (`protocol/`).

## Plan

- **C/C++ Pico SDK** (ne MicroPython), da bi se `protocol/` delio bez prepisivanja.
- Pico SDK se **ne commituje**: CMake ga sam preuzima (`PICO_SDK_FETCH_FROM_GIT=ON`
  sa `pico_sdk_import.cmake`), ili se koristi lokalna instalacija preko `PICO_SDK_PATH`.
- Raspored pinova: vidi detaljni dijagram povezivanja u `docs/arhitektura/`.

## Build (kada projekat postoji)

```bash
cd pico
cmake -B build -DPICO_SDK_FETCH_FROM_GIT=ON
cmake --build build
# build/<ime>.uf2 kopirati na Pico u BOOTSEL modu
```
