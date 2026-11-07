"""Simulator taktika (komandna linija).

    python -m eurosim run primer                     # meč na plavoj: činč, START poza, taktika, 100 s
    python -m eurosim run primer --side zuta --test  # odmah, kao tools/tactic.py
    python -m eurosim run primer --opp 900,1000      # protivnik 300x300 mm na (900, 1000)
    python -m eurosim run primer --out run.json.gz   # sačuvaj snimak
    python -m eurosim run primer -v                  # i sve poruke ESP <-> STM32
    python -m eurosim list                           # taktike u ESP32/tactics

Pokreće se iz simulator/ (ili: python simulator/sim.py ...).
"""
import argparse
import sys
import time

from . import paths, profile as profmod


def _opp(s):
    v = [float(x) for x in s.split(",")]
    keys = ("x", "y", "w", "h", "th")
    return dict(zip(keys, v))


def cmd_run(a):
    from .sim import Sim
    prof = profmod.load(a.profile)
    t0 = time.time()
    sim = Sim(a.name, side=a.side, mode="test" if a.test else "mec", prof=prof, tactics_dir=a.dir,
              max_s=a.max_s, cord_s=a.cord, obstacles=[_opp(o) for o in a.opp or []])
    rec = sim.run()
    wall = time.time() - t0
    for t, kind, d in rec.events:
        if kind == "log":
            print("%7.2fs  %s" % (t / 1000, d))
        elif kind == "sim":
            print("%7.2fs  [sim] %s" % (t / 1000, d["text"]))
        elif a.verbose and kind in ("rx", "tx"):
            arrow = "ESP->STM" if kind == "rx" else "STM->ESP"
            print("%7.2fs  %s %-8s seq=%-3d %s" % (t / 1000, arrow, d["name"], d["seq"], d["f"] or ""))
    r = rec.result
    print()
    print("koraci:")
    for idx, nm, ok, reason, ms in rec.steps():
        print("  %2d %-28s %-6s %6.2fs" % (idx, nm, "OK" if ok else (reason or "FAIL"), ms / 1000))
    print()
    print("ishod: %s%s" % ("OK" if r["ok"] else "NIJE OK", "" if not r["how"] else " (%s)" % r["how"]))
    print("poza na stolu: x=%.0f y=%.0f ugao=%.1f   odometrija: x=%.0f y=%.0f ugao=%.1f"
          % tuple(r["pose"] + r["odom"]))
    print("u svojoj zoni na kraju: %s" % ("da" if r["in_own_zone"] else "ne"))
    print("simulirano %.1fs za %.2fs" % (r["sim_ms"] / 1000, wall))
    if a.out:
        rec.save(a.out)
        print("snimak: %s" % a.out)
    return 0 if r["ok"] else 1


def cmd_list(a):
    d = a.dir or paths.TACTICS
    import pathlib
    for f in sorted(pathlib.Path(d).glob("*.py")):
        print(f.stem)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="eurosim", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="simuliraj taktiku")
    r.add_argument("name")
    r.add_argument("--side", choices=("plava", "zuta"), default="plava")
    r.add_argument("--test", action="store_true", help="odmah, bez meča (kao tools/tactic.py)")
    r.add_argument("--profile", help="profil robota (.toml), podrazumevano profiles/robot2027.toml")
    r.add_argument("--dir", help="folder sa taktikama (podrazumevano ESP32/tactics)")
    r.add_argument("--max-s", type=float, dest="max_s", help="najduže trajanje (s)")
    r.add_argument("--cord", type=float, default=1.0, help="činč posle N s od naoružavanja")
    r.add_argument("--opp", action="append", help="protivnik x,y[,w,h[,ugao]] u mm (može više puta)")
    r.add_argument("--out", help="sačuvaj snimak (.json.gz)")
    r.add_argument("-v", "--verbose", action="store_true", help="i poruke ESP <-> STM32")
    r.set_defaults(fn=cmd_run)
    li = sub.add_parser("list", help="taktike")
    li.add_argument("--dir")
    li.set_defaults(fn=cmd_list)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
