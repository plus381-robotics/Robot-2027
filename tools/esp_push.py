#!/usr/bin/env python3
"""Pošalji ESP kod preko WiFi-ja i restartuj ESP (umesto mpremote preko USB-a).

    python tools/esp_push.py                      # main.py, config.py, lib/, tactics/ (samo izmenjeno)
    python tools/esp_push.py ESP32/lib/app.py     # samo neki fajlovi
    python tools/esp_push.py --prune              # i obriši sa ESP-a ono iz lib/ i tactics/ čega lokalno nema
    python tools/esp_push.py --list               # samo prikaži šta se razlikuje

Šalje se atomično: svaki fajl prvo u /.new/ sa proverom sha256, pa COMMIT sve odjednom stavi na
mesto i upiše /version.txt (git describe). Prekid usred slanja ne ostavlja pola starog, pola novog koda.
lib/ se šalje prekompajliran (.mpy, mpy-cross iste verzije kao firmver): kompajliranje na ESP-u
pri uvozu uzme toliko RAM-a da WiFi ostane bez memorije. Stari lib/*.py se posle COMMIT-a briše
(imao bi prednost nad .mpy). --py šalje izvorne .py (samo za traženje grešaka).
Prvi put (dok na ESP-u nema lib/upload.py) ide preko USB-a, vidi ESP32/README.md.
secrets.py i webrepl_cfg.py se ne šalju (osim ako se navedu).
"""
import argparse
import os
import subprocess
import sys
import tempfile

from espnet import ROOT, password, query, request, sha256

ESP = ROOT / "ESP32"


def local_files(args):
    if args:
        return [(ROOT / f).resolve() for f in args]
    return [ESP / "main.py", ESP / "config.py"] + sorted((ESP / "lib").glob("*.py")) \
        + sorted((ESP / "tactics").glob("*.py"))


MPY_VERSION = "1.29"         # mora da se poklapa sa MicroPython firmverom na ESP-u


def mpy_cross(src):
    """Prekompajliraj .py u .mpy (bajtovi). Treba: pipx install mpy-cross==1.29.0.post2"""
    out = os.path.join(tempfile.gettempdir(), "esp_push.mpy")
    try:
        import mpy_cross
        p = mpy_cross.run("-o", out, str(src))
        p.wait()
        if p.returncode:
            sys.exit("mpy-cross nije uspeo: %s" % src)
    except ImportError:
        try:
            subprocess.run(["mpy-cross", "-o", out, str(src)], check=True)
        except (OSError, subprocess.CalledProcessError):
            sys.exit("treba mpy-cross %s: pipx install mpy-cross==%s.0.post2 (ili --py)" % (MPY_VERSION, MPY_VERSION))
    with open(out, "rb") as f:
        return f.read()


def git_version():
    try:
        return subprocess.run(["git", "-C", str(ROOT), "describe", "--always", "--dirty"],
                              capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "nepoznato"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*")
    ap.add_argument("--host", default="eurokik.local")
    ap.add_argument("--password")
    ap.add_argument("--no-reset", action="store_true")
    ap.add_argument("--prune", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--py", action="store_true", help="lib/ kao izvorni .py (bez mpy-cross)")
    a = ap.parse_args()
    pw = password(a.password)
    files = {}
    for f in (p.resolve() for p in local_files(a.files)):
        rel = "/" + f.relative_to(ESP.resolve()).as_posix()
        if rel.startswith("/lib/") and rel.endswith(".py") and not a.py:
            files[rel[:-3] + ".mpy"] = mpy_cross(f)
        else:
            files[rel] = f.read_bytes()

    lines = query(a.host, pw, "LIST")
    if not lines or not lines[-1].startswith("OK"):          # stari server: bez LIST/STAGE/COMMIT
        print("stari server na ESP-u: šaljem sve fajlove sa PUT")
        for path, data in files.items():
            if not request(a.host, pw, "PUT %s %d %s" % (path, len(data), sha256(data)), data):
                sys.exit("nije uspelo: " + path)
        remote = {}
        changed = []
    else:
        remote = {p: sha for p, _, sha in (l.split() for l in lines[:-1])}
        changed = [p for p, d in files.items() if remote.get(p) != sha256(d)]
        mine = set(p.rsplit(".", 1)[0] for p in files)          # naši moduli (bez ekstenzije)
        extra = sorted(p for p in remote if p.startswith(("/lib/", "/tactics/")) and p not in files
                       and not a.files and (p.endswith(".py") or p.rsplit(".", 1)[0] in mine))
        # .mpy koji nije naš (npr. ssd1306 iz mip-a) se ne dira; stari .py našeg modula mora da ode
        shadow = [p for p in extra if p.startswith("/lib/") and p.rsplit(".", 1)[0] in mine]
        print("izmenjeno: %d, isto: %d, višak na ESP-u: %d" % (len(changed), len(files) - len(changed), len(extra)))
        for p in changed:
            print("  ~ " + p)
        for p in extra:
            print("  %s %s" % ("-" if a.prune or p in shadow else "?", p))
        if a.list:
            return
        for p in changed:
            d = files[p]
            if not request(a.host, pw, "STAGE %s %d %s" % (p, len(d), sha256(d)), d):
                sys.exit("nije uspelo: %s (na ESP-u se ništa nije promenilo)" % p)
        if changed and not request(a.host, pw, "COMMIT " + git_version()):
            sys.exit("COMMIT nije uspeo")
        for p in extra:
            if a.prune or p in shadow:      # stara verzija istog modula (.py pored .mpy) se uvek briše
                request(a.host, pw, "DEL " + p)
        if not changed and not shadow and not (a.prune and extra):
            print("ništa za slanje")
            return
    if not a.no_reset:
        try:
            request(a.host, pw, "RESET")
        except (OSError, SystemExit):
            pass                                # ESP prekine vezu restartom
        print("ESP se restartuje")


if __name__ == "__main__":
    main()
