#!/usr/bin/env python3
"""Pošalji taktiku na ESP preko WiFi-ja, pokreni je i prati dnevnik. Ctrl+C = STOP.

    python tools/tactic.py primer            # ESP32/tactics/primer.py
    python tools/tactic.py primer --no-push  # pokreni ono što je već na ESP-u
    python tools/tactic.py primer --side plava # druga strana (koordinate se ogledaju); podrazumevano zuta
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
    ap.add_argument("--side", choices=("zuta", "plava"), default="zuta",
                    help="strana (podrazumevano zuta, REF_SIDE); uvek se šalje, ne zavisi od izbora na robotu")
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
    print("strana: %s" % a.side)
    if not request(a.host, pw, "RUN %s %s" % (a.name, a.side)):
        sys.exit(1)
    try:
        running = True
        while running:
            time.sleep(0.3)
            try:
                lines = query(a.host, pw, "LOG %d" % pos)
            except SystemExit as e:                  # mreža pukla: probaj STOP i jasno reci šta se zna
                print("\nveza pukla (%s): saljem STOP..." % e)
                try:
                    ok = request(a.host, pw, "STOP", timeout=5)
                except SystemExit:
                    ok = False
                print("STOP potvrden" if ok else "ROBOT NIJE POTVRDJENO ZAUSTAVLJEN: taster STOP na robotu!")
                sys.exit(1)
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
