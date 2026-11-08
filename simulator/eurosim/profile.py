# Profil robota (simulator/profiles/*.toml): dimenzije, pogon, odometrija, regulacija, IR, aktuatori.
import tomllib

from . import paths


class Profile(dict):
    """Rečnik sekcija iz TOML-a; p.m("drive", "wheel_track") vraća metre."""

    def m(self, sec, key):
        return self[sec][key] / 1000.0


def load(path=None, **override):
    """Učitaj profil. override: {"drive.wheel_track": 180} menja pojedinačne vrednosti."""
    with open(path or paths.DEFAULT_PROFILE, "rb") as f:
        p = Profile(tomllib.load(f))
    for k, v in override.items():
        sec, key = k.split(".", 1)
        p.setdefault(sec, {})[key] = v
    return p


# ---------------- uređivanje iz interfejsa (čuva komentare u fajlu) ----------------

import re  # noqa: E402

_SEC = re.compile(r"^\s*\[([A-Za-z0-9_.]+)\]\s*(#.*)?$")
_KV = re.compile(r"^(\s*([A-Za-z0-9_]+)\s*=\s*)(\"[^\"]*\"|[^#\n]*?)(\s*(#.*)?)$")


def describe(path):
    """[{name, items: [{key, value, comment}]}] redom kao u fajlu; komentar iznad sekcije/ključa ili u istom redu."""
    secs, cur, note = [], {"name": "", "items": [], "comment": ""}, []
    secs.append(cur)
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    data = load(path)
    for line in lines:
        m = _SEC.match(line)
        if m:
            cur = {"name": m.group(1), "items": [], "comment": " ".join(note)}
            secs.append(cur)
            note = []
            continue
        m = _KV.match(line)
        if m:
            key = m.group(2)
            val = data.get(key) if cur["name"] == "" else data.get(cur["name"], {}).get(key)
            if isinstance(val, dict):
                continue
            c = (m.group(5) or "").lstrip("#").strip()
            cur["items"].append({"key": key, "value": val, "comment": " ".join(note + ([c] if c else []))})
            note = []
        elif line.strip().startswith("#"):
            t = line.strip().lstrip("#").strip()
            if t:
                note.append(t)
        else:
            note = []
    return [s for s in secs if s["items"]]


def _fmt(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(v)
    return '"%s"' % str(v).replace('"', "")


def update_file(path, changes):
    """changes: {"sekcija.ključ": vrednost} (ključ bez sekcije = vrh fajla). Tip mora da ostane isti."""
    old = load(path)
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    todo = dict(changes)
    sec = ""
    for i, line in enumerate(lines):
        m = _SEC.match(line)
        if m:
            sec = m.group(1)
            continue
        m = _KV.match(line)
        if not m:
            continue
        full = (sec + "." if sec else "") + m.group(2)
        if full not in todo:
            continue
        v = todo.pop(full)
        cur = old.get(m.group(2)) if not sec else old.get(sec, {}).get(m.group(2))
        if isinstance(cur, bool):
            v = v if isinstance(v, bool) else str(v).lower() in ("1", "true", "da", "yes")
        elif isinstance(cur, (int, float)):
            v = float(v)
            if isinstance(cur, int) and v.is_integer():
                v = int(v)
        lines[i] = m.group(1) + _fmt(v) + (m.group(4) or "")
    if todo:
        raise KeyError("nepoznato u profilu: %s" % ", ".join(todo))
    text = "\n".join(lines) + "\n"
    tomllib.loads(text)                          # mora i dalje da bude ispravan TOML
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
