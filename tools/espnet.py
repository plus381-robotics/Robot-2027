"""Klijent za upload server na ESP-u (ESP32/lib/upload.py, port 8267)."""
import pathlib
import re
import socket
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PORT = 8267


def password(arg=None):
    if arg:
        return arg
    cfg = ROOT / "ESP32" / "webrepl_cfg.py"
    m = re.search(r"PASS\s*=\s*['\"](.*)['\"]", cfg.read_text()) if cfg.exists() else None
    if not m:
        sys.exit("nema lozinke: napravi ESP32/webrepl_cfg.py ili daj --password")
    return m.group(1)


def request(host, pw, command, data=b"", timeout=60):
    """Pošalji komandu (i podatke), ispisuj redove odgovora. Vraća True ako je kraj 'OK'."""
    with socket.create_connection((host, PORT), timeout=10) as s:
        s.settimeout(timeout)
        s.sendall(pw.encode() + b"\n" + command.encode() + b"\n" + data)
        last = ""
        for line in s.makefile("r", encoding="utf-8", errors="replace"):
            line = line.rstrip()
            print("  " + line)
            last = line
    return last.startswith("OK")
