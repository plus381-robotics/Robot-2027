# Putanje do repoa. Simulator koristi ESP kod direktno iz ESP32/ (ništa se ne kopira).
import os
import pathlib

SIM = pathlib.Path(__file__).resolve().parent.parent           # simulator/
ROOT = pathlib.Path(os.environ.get("EUROSIM_ROOT") or SIM.parent)   # koren repoa
ESP = ROOT / "ESP32"
TACTICS = ESP / "tactics"
PROFILES = SIM / "profiles"
DEFAULT_PROFILE = PROFILES / "robot2027.toml"
