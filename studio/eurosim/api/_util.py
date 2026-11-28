# Zajednički delovi HTTP slojeva (STATE ključ, JSON pomoćne funkcije).
import json

from aiohttp import web

from .. import paths

STATE = web.AppKey("state", dict)          # {"profile": Profile, "last": poslednji snimak (dict)}


def _tactic_names():
    """Imena taktika iz ESP32/tactics (bez .py)."""
    return {f.stem for f in paths.TACTICS.glob("*.py")}


def _dumps(o):
    """Zbijen JSON za veće odgovore i WebSocket poruke."""
    return json.dumps(o, separators=(",", ":"))


def _elements_arg(v):
    """Kamenolomi iz zahteva: True/False/"1"/"0" (po pravilima ili bez) ili lista (izmenjen sto, JSON)."""
    if isinstance(v, str):
        if v in ("0", "1", ""):
            return v != "0"
        try:
            v = json.loads(v)
        except ValueError:
            return True
    return v if isinstance(v, list) else bool(v)


def columns(frames):
    """Frame-ovi (lista dict-ova) -> kolone (dict lista), za grafike i manji JSON."""
    keys = []
    for f in frames:
        for k in f:
            if k not in keys:
                keys.append(k)
    return {k: [f.get(k) for f in frames] for k in keys}


def pack(rec):
    d = dict(rec)
    d["cols"] = columns(d.pop("frames"))
    return d
