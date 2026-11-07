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
