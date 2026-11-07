#!/usr/bin/env python3
"""Telemetrija sa robota uživo (UDP, port 8268): poza, stanje, korak taktike, dnevnik.

    python tools/watch.py                    # ispis u terminalu
    python tools/watch.py --csv log.csv      # i zapis u CSV (za kasniju analizu)

Samo čitanje; ništa se ne pokreće. Ctrl+C za kraj.
"""
import argparse
import csv
import json
import socket
import time

FIELDS = ("t", "x", "y", "th", "sp", "st", "mm", "tac", "i", "step", "el", "side", "mec")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", default="eurokik.local")
    ap.add_argument("--port", type=int, default=8268)
    ap.add_argument("--csv")
    a = ap.parse_args()
    addr = (socket.gethostbyname(a.host), a.port)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0.5)
    w = None
    if a.csv:
        f = open(a.csv, "w", newline="")
        w = csv.DictWriter(f, FIELDS, extrasaction="ignore")
        w.writeheader()
    t_sub = 0
    last = 0
    try:
        while True:
            if time.time() - t_sub > 3:
                s.sendto(b"WATCH", addr)
                t_sub = time.time()
            try:
                d = json.loads(s.recv(2048))
            except socket.timeout:
                if time.time() - last > 2:
                    print("... nema podataka sa %s:%d" % addr)
                    last = time.time()
                continue
            last = time.time()
            for l in d.get("log", []):
                print("  | " + l)
            if w:
                w.writerow(d)
            pose = "x=%5s y=%5s th=%6s v=%4s" % (d.get("x", "-"), d.get("y", "-"), d.get("th", "-"), d.get("sp", "-"))
            tac = ""
            if "tac" in d:
                tac = " | %s %s/%s %s %.1fs" % (d["tac"], d["i"], d.get("n") or "?", d.get("step") or "", (d.get("el") or 0) / 1000)
            print("\r%s %s %s%s" % ("OK " if d.get("ok") else "-- ", pose, d.get("mec", ""), tac) + " " * 10, end="", flush=True)
    except KeyboardInterrupt:
        print()


if __name__ == "__main__":
    main()
