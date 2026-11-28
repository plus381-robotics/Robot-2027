# Prenos lokalnih fajlova iz starog simulator/ u studio/ (preimenovanje u Gambit Studio). Fajlovi koji nisu u gitu
# (snimci lidara, sačuvane vožnje, lični scenariji, protivnici, profili) ostaju u starom folderu posle git pull-a;
# ovde se jednom premeštaju na isto mesto pod studio/. Ništa se ne prepisuje: ako ime već postoji, stari fajl ostaje.
# .venv i sve ostalo u starom folderu se ne dira. Rezultat: {"moved": [...], "skipped": [...], "why": {fajl: razlog}}
# (putanje relativne prema simulator/; why kaže zašto je preskočen: isto ime već postoji ili greška pri premeštanju).
import pathlib
import shutil

SUBDIRS = ("lidar", "runs", "scenarios", "opponents", "profiles")


def move_old_local(root):
    root = pathlib.Path(root)
    out = {"moved": [], "skipped": [], "why": {}}
    old, new = root / "simulator", root / "studio"
    if not old.is_dir() or not new.is_dir():
        return out
    for sub in SUBDIRS:
        src = old / sub
        if not src.is_dir():
            continue
        for f in sorted(src.rglob("*")):
            if not f.is_file():
                continue
            rel = f.relative_to(old)
            dst = new / rel
            if dst.exists():
                out["skipped"].append(rel.as_posix())
                out["why"][rel.as_posix()] = "isto ime već postoji u studio/"
                continue
            try:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(f), str(dst))
            except OSError as e:
                out["skipped"].append(rel.as_posix())
                out["why"][rel.as_posix()] = "greška: %s" % (e.strerror or e)
                continue
            out["moved"].append(rel.as_posix())
        for d in sorted((p for p in src.rglob("*") if p.is_dir()), reverse=True) + [src]:
            try:
                d.rmdir()                                   # samo prazni; sa fajlovima ostaje
            except OSError:
                pass
    return out
