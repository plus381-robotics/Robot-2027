# Putanje. Simulator radi na dva načina:
#
#  - iz repoa (python simulator/sim.py ... ili izvršni fajl pokrenut unutar repoa): ESP kod, taktike,
#    profili i snimci su u repou (ESP32/, simulator/), pa se izmene vide odmah i idu u git;
#  - samostalno (izvršni fajl van repoa, npr. skinut sa GitHub-a): ESP kod je spakovan u fajl, a taktike,
#    profili i snimci su u ~/Eurosim (prvi put se tamo kopiraju primeri).
# Repo se traži od trenutnog foldera i od foldera izvršnog fajla naviše, ili se zada sa EUROSIM_ROOT, ili je to
# repo koji je korisnik ranije izabrao u aplikaciji ("Open repo folder" / "Clone repo", plan S10), zapamćen u
# ~/.eurosim.json.
import json
import os
import pathlib
import shutil
import sys

FROZEN = bool(getattr(sys, "frozen", False))
BUNDLE = pathlib.Path(getattr(sys, "_MEIPASS", pathlib.Path(__file__).resolve().parents[2]))
WEB = BUNDLE / "simulator" / "web"            # interfejs uvek iz istog paketa kao server (iste verzije)


def _is_repo(p):
    return (p / "ESP32" / "lib" / "tac.py").exists() and (p / "simulator").is_dir()


USER_CFG = pathlib.Path(os.environ.get("EUROSIM_CONFIG") or pathlib.Path.home() / ".eurosim.json")


def user_cfg():
    try:
        return json.loads(USER_CFG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def remember_repo(path):
    """Zapamti izabrani repo za sledeće pokretanje (i kad se exe pokrene van repoa)."""
    cfg = user_cfg()
    cfg["repo"] = str(pathlib.Path(path).resolve())
    USER_CFG.write_text(json.dumps(cfg, indent=1), encoding="utf-8")


def is_repo(p):
    return _is_repo(pathlib.Path(p))


def find_repo():
    if os.environ.get("EUROSIM_NO_REPO") == "1":      # testovi: kao exe pokrenut van repoa
        return None
    env = os.environ.get("EUROSIM_ROOT")
    if env:
        return pathlib.Path(env).resolve()
    starts = [pathlib.Path.cwd()]
    if FROZEN:
        starts.append(pathlib.Path(sys.executable).resolve().parent)
    else:
        starts.insert(0, BUNDLE)
    for s in starts:
        for p in [s, *s.parents]:
            if _is_repo(p):
                return p
    saved = user_cfg().get("repo")
    if saved and _is_repo(pathlib.Path(saved)):
        return pathlib.Path(saved)
    return None


def configure(root=None, home=None):
    """Postavi globalne putanje (root = repo ili None za samostalni rad)."""
    global ROOT, ESP, TACTICS, SIM, PROFILES, RUNS, TOOLS, DEFAULT_PROFILE, HOME, MODE, SCENARIOS
    if root:
        os.environ["EUROSIM_ROOT"] = str(root)        # i za procese simulacije (spawn)
    if home:
        os.environ["EUROSIM_HOME"] = str(home)
    ROOT = pathlib.Path(root).resolve() if root else find_repo()
    if ROOT:
        MODE = "repo"
        HOME = None
        ESP = ROOT / "ESP32"
        TACTICS = ESP / "tactics"
        SIM = ROOT / "simulator"
        PROFILES = SIM / "profiles"
        RUNS = SIM / "runs"
        SCENARIOS = SIM / "scenarios"              # izmenjen sto (kamenolomi, protivnici), deli se kroz git
        TOOLS = ROOT / "tools"
    else:
        MODE = "standalone"
        HOME = pathlib.Path(home or os.environ.get("EUROSIM_HOME") or pathlib.Path.home() / "Eurosim")
        ESP = BUNDLE / "ESP32"
        SIM = BUNDLE / "simulator"
        TOOLS = BUNDLE / "tools"
        TACTICS, PROFILES, RUNS = HOME / "tactics", HOME / "profiles", HOME / "runs"
        SCENARIOS = HOME / "scenarios"
        for d, src in ((TACTICS, ESP / "tactics"), (PROFILES, SIM / "profiles")):
            if not d.exists():
                d.mkdir(parents=True)
                for f in src.glob("*.*"):
                    shutil.copy(f, d)
    DEFAULT_PROFILE = PROFILES / "robot2027.toml"
    if not DEFAULT_PROFILE.exists():
        found = sorted(PROFILES.glob("*.toml"))
        DEFAULT_PROFILE = found[0] if found else SIM / "profiles" / "robot2027.toml"


def describe():
    return {"mode": MODE, "root": str(ROOT) if ROOT else None, "home": str(HOME) if HOME else None,
            "tactics": str(TACTICS), "profiles": str(PROFILES), "runs": str(RUNS), "frozen": FROZEN,
            "user_home": str(pathlib.Path.home()), "app": str(pathlib.Path(sys.executable).name) if FROZEN else None}


configure()
