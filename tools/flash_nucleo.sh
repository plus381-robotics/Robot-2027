#!/usr/bin/env bash
# Flesuje Nucleo preko ST-LINK-a (radi i sa RPi-ja preko SSH-a).
#   ./tools/flash_nucleo.sh                 # flesuje postojeci .elf
#   ./tools/flash_nucleo.sh --build         # prvo build (Release), pa flesovanje
#   ./tools/flash_nucleo.sh putanja/do.elf  # konkretan fajl
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FW_DIR="$REPO/nucleo/firmware"
ELF="$FW_DIR/build/Release/firmware.elf"

if [[ "${1:-}" == "--build" ]]; then
  (cd "$FW_DIR" && cmake --preset Release && cmake --build --preset Release)
elif [[ -n "${1:-}" ]]; then
  ELF="$1"
fi

if [[ ! -f "$ELF" ]]; then
  echo "Nema $ELF. Pokreni sa --build ili navedi putanju do .elf fajla." >&2
  exit 1
fi

echo "Flesujem $ELF"
openocd -f interface/stlink.cfg -f target/stm32f4x.cfg \
  -c "program $ELF verify reset exit"
