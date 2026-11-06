#!/usr/bin/env python3
"""Pošalji ESP kod preko WiFi-ja i restartuj ESP (umesto mpremote preko USB-a).

    python tools/esp_push.py                      # main.py, config.py i sve iz lib/
    python tools/esp_push.py ESP32/lib/app.py     # samo neki fajlovi

Prvi put (dok na ESP-u nema lib/upload.py) ide preko USB-a, vidi ESP32/README.md.
secrets.py i webrepl_cfg.py se ne šalju (osim ako se navedu).
"""
import argparse
import sys

from espnet import ROOT, password, request


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*")
    ap.add_argument("--host", default="eurokik.local")
    ap.add_argument("--password")
    ap.add_argument("--no-reset", action="store_true")
    a = ap.parse_args()
    esp = ROOT / "ESP32"
    files = [ROOT / f if not f.startswith("/") else f for f in a.files] or \
        [esp / "main.py", esp / "config.py"] + sorted((esp / "lib").glob("*.py"))
    pw = password(a.password)
    for f in files:
        rel = f.resolve().relative_to(esp.resolve()).as_posix()
        if not request(a.host, pw, "PUT /%s %d" % (rel, f.stat().st_size), f.read_bytes()):
            sys.exit("nije uspelo: " + rel)
    if not a.no_reset:
        try:
            request(a.host, pw, "RESET")
        except OSError:
            pass                            # ESP prekine vezu restartom
        print("ESP se restartuje")


if __name__ == "__main__":
    main()
