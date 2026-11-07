#!/usr/bin/env python3
"""Flešuj STM32 preko ESP-a (WiFi), bez kabla.

    python tools/flash_stm32.py pogon-blackpill/Debug/PogonskiSTM-2026-BlackPill.elf --host eurokik.local

Prima .bin ili .elf (.elf se pretvara u .bin sa arm-none-eabi-objcopy iz PATH-a ili iz CubeIDE-a).
ESP pošalje ENTER_BOOTLOADER, flešuje preko ugrađenog bootloader-a (AN3155), proveri upis
čitanjem i pokrene novi firmver.
"""
import argparse
import glob
import shutil
import subprocess
import sys
import tempfile
import pathlib

from espnet import password, request


def objcopy():
    p = shutil.which("arm-none-eabi-objcopy")
    if p:
        return p
    found = sorted(glob.glob("/opt/st/stm32cubeide_*/plugins/*gnu-tools-for-stm32*/tools/bin/arm-none-eabi-objcopy"))
    if not found:
        sys.exit("nema arm-none-eabi-objcopy; daj .bin (CubeIDE: Convert to binary)")
    return found[-1]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", help=".bin ili .elf")
    ap.add_argument("--host", default="eurokik.local")
    ap.add_argument("--password")
    a = ap.parse_args()
    path = pathlib.Path(a.file)
    if path.suffix == ".elf":
        out = pathlib.Path(tempfile.gettempdir()) / (path.stem + ".bin")
        subprocess.run([objcopy(), "-O", "binary", str(path), str(out)], check=True)
        path = out
    data = path.read_bytes()
    data += b"\xff" * (-len(data) % 4)
    print("%s: %d B -> %s" % (path.name, len(data), a.host))
    ok = request(a.host, password(a.password), "FLASH %d" % len(data), data, timeout=120)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
