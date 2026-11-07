"""Klijent za upload server na ESP-u (ESP32/lib/upload.py, port 8267).

Prijava: server pošalje "EURO2 <nonce>", klijent odgovori sha256(lozinka + nonce). Stari server
(bez pozdrava) dobije lozinku kao prvi red, da bi prvo slanje novog koda radilo.
Komande koje ništa ne pokreću (LIST, LOG, STAT, PUT, STAGE) se ponavljaju ako mreža zapne.
"""
import hashlib
import pathlib
import re
import socket
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
PORT = 8267
RETRY = ("LIST", "LOG", "STAT", "PUT", "STAGE")


def password(arg=None):
    if arg:
        return arg
    cfg = ROOT / "ESP32" / "webrepl_cfg.py"
    m = re.search(r"PASS\s*=\s*['\"](.*)['\"]", cfg.read_text()) if cfg.exists() else None
    if not m:
        sys.exit("nema lozinke: napravi ESP32/webrepl_cfg.py ili daj --password")
    return m.group(1)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def _talk(host, pw, command, data, timeout, port):
    with socket.create_connection((host, port or PORT), timeout=5) as s:
        # Novi server pozdravi odmah ("EURO2 <nonce>"); stari ništa ne šalje i čeka lozinku 0.5 s.
        # Pozdrav se čita direktno (makefile posle isteklog čitanja više ne radi).
        s.settimeout(0.35)
        got = b""
        try:
            while not got.endswith(b"\n") and len(got) < 100:
                d = s.recv(100 - len(got))
                if not d:
                    break
                got += d
        except socket.timeout:
            pass
        hello = got.decode("ascii", "replace").strip()
        f = s.makefile("rb")
        if hello.startswith("EURO2 "):
            auth = sha256((pw + hello.split()[1]).encode())
        else:
            auth = pw                          # stari server
        s.settimeout(timeout)
        s.sendall(auth.encode() + b"\n" + command.encode() + b"\n" + data)
        return [l.decode("utf-8", "replace").rstrip("\n") for l in f]


def query(host, pw, command, data=b"", timeout=10, port=None, tries=3):
    """Pošalji komandu, vrati listu redova odgovora (bez ispisa)."""
    cmd = command.split()[0]
    if cmd == "LIST":
        timeout = max(timeout, 60)             # fajl sistem na ESP-u je spor (prvi LIST računa sha)
    for i in range(tries if cmd in RETRY else 1):
        try:
            return _talk(host, pw, command, data, timeout, port)
        except (socket.timeout, ConnectionError, OSError) as e:
            err = e
            if cmd not in RETRY or i == tries - 1:
                break
            time.sleep(0.5 * (i + 1))
    if isinstance(err, socket.gaierror):
        sys.exit("ne mogu da nađem %s (ESP nije na mreži? probaj IP sa ekrana VEZA)" % host)
    raise SystemExit("%s: %s (%s)" % (host, err, command.split()[0]))


def request(host, pw, command, data=b"", timeout=60, port=None):
    """Kao query(), ali ispisuje odgovor. Vraća True ako je poslednji red 'OK'."""
    lines = query(host, pw, command, data, timeout, port)
    for l in lines:
        print("  " + l)
    return bool(lines) and lines[-1].startswith("OK")
