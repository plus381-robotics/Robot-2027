#!/usr/bin/env python3
"""Pošalji taktiku na ESP preko WiFi-ja, pokreni je i prati dnevnik. Ctrl+C = STOP.

    python tools/tactic.py primer            # ESP32/tactics/primer.py
    python tools/tactic.py primer --no-push  # pokreni ono što je već na ESP-u
    python tools/tactic.py primer --side plava # druga strana (koordinate se ogledaju)
    python tools/tactic.py --stop            # samo STOP
"""
import argparse
import sys
import time

from espnet import ROOT, password, request, query


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("name", nargs="?")
    ap.add_argument("--host", default="eurokik.local")
    ap.add_argument("--password")
    ap.add_argument("--no-push", action="store_true")
    ap.add_argument("--stop", action="store_true")
    ap.add_argument("--side", choices=("plava", "zuta"))
    a = ap.parse_args()
    pw = password(a.password)
    if a.stop or not a.name:
        request(a.host, pw, "STOP")
        return
    if not a.no_push:
        f = ROOT / "ESP32" / "tactics" / (a.name + ".py")
        if not request(a.host, pw, "PUT /tactics/%s.py %d" % (a.name, f.stat().st_size), f.read_bytes()):
            sys.exit(1)
    pos = int(query(a.host, pw, "LOG 0")[-1].split()[1])      # ne ispisuj stare redove
    if not request(a.host, pw, "RUN %s %s" % (a.name, a.side or "")):
        sys.exit(1)
    try:
        running = True
        while running:
            time.sleep(0.3)
            lines = query(a.host, pw, "LOG %d" % pos)
            *text, last = lines
            for l in text:
                print(l)
            _, pos, r = last.split()
            pos, running = int(pos), r == "1"
    except KeyboardInterrupt:
        request(a.host, pw, "STOP")
        print("STOP poslat")


if __name__ == "__main__":
    main()
