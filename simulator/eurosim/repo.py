# Repo kao radni prostor (plan S10): taktike i profili robota žive u git repou Robot-2027, pa ih ceo tim deli,
# a git čuva istoriju. Ovde: otvaranje i kloniranje repoa iz aplikacije, stanje (grana, ispred/iza, izmenjeni
# fajlovi, profil promenjen na GitHub-u), "Pull latest" i "Save to GitHub". Sve preko komande git (mora biti
# instaliran: GitHub Desktop ili Git for Windows; prijava preko Git Credential Manager-a jer je repo privatan).
import pathlib
import shutil
import subprocess
import sys

from . import paths

URL = "https://github.com/plus381-robotics/Robot-2027"
SHARED = ("ESP32/tactics", "simulator/profiles")        # šta "Save to GitHub" šalje (ne ESP kod, ne simulator)


class GitError(Exception):
    pass


def _git(*args, cwd=None, timeout=60):
    if not shutil.which("git"):
        raise GitError("Git is not installed. Install GitHub Desktop or Git for Windows, then try again.")
    kw = {}
    if sys.platform == "win32":
        kw["creationflags"] = 0x08000000                # bez crnog prozora
    try:
        r = subprocess.run(["git", *args], cwd=cwd or paths.ROOT, capture_output=True, text=True, timeout=timeout,
                           encoding="utf-8", errors="replace", **kw)
    except subprocess.TimeoutExpired:
        raise GitError("git %s: no answer in %d s (network?)" % (args[0], timeout))
    if r.returncode:
        raise GitError(("git %s: " % args[0]) + (r.stderr or r.stdout).strip()[-600:])
    return r.stdout


def check_folder(path):
    """Da li je folder klon Robot-2027 (ESP32/lib/tac.py i simulator/). Vraća (ok, poruka)."""
    p = pathlib.Path(path).expanduser()
    if not p.is_dir():
        return False, "folder does not exist: %s" % p
    if not paths.is_repo(p):
        return False, "this is not the Robot-2027 repo (no ESP32/lib/tac.py and simulator/ in %s)" % p
    try:
        remote = _git("remote", "get-url", "origin", cwd=p).strip()
        if "robot-2027" not in remote.lower():
            return True, "warning: origin is %s, not Robot-2027" % remote
    except GitError:
        return True, "warning: not a git clone (no history, Save to GitHub will not work)"
    return True, ""


def open_repo(path):
    """Prebaci aplikaciju na repo u folderu path i zapamti ga za sledeće pokretanje."""
    ok, note = check_folder(path)
    if not ok:
        raise ValueError(note)
    p = pathlib.Path(path).expanduser().resolve()
    paths.remember_repo(p)
    paths.configure(root=p)
    return {"root": str(p), "note": note}


def clone(parent):
    """git clone u parent/Robot-2027, pa otvori. Može da traje (prvi put i prijava na GitHub)."""
    par = pathlib.Path(parent).expanduser()
    par.mkdir(parents=True, exist_ok=True)
    dst = par / "Robot-2027"
    if dst.exists() and any(dst.iterdir()):
        if paths.is_repo(dst):
            return open_repo(dst)
        raise ValueError("%s already exists and is not the repo" % dst)
    _git("clone", URL, str(dst), cwd=par, timeout=900)
    return open_repo(dst)


def status(fetch=False):
    if paths.MODE != "repo":
        return {"repo": False}
    out = {"repo": True, "root": str(paths.ROOT)}
    try:
        if fetch:
            _git("fetch", "--quiet", "origin", timeout=120)
        out["branch"] = _git("rev-parse", "--abbrev-ref", "HEAD").strip()
        out["commit"] = _git("log", "-1", "--format=%h %s").strip()
        try:
            ab = _git("rev-list", "--left-right", "--count", "HEAD...@{upstream}").split()
            out["ahead"], out["behind"] = int(ab[0]), int(ab[1])
            up = _git("diff", "--name-only", "HEAD...@{upstream}", "--", "simulator/profiles").split()
            out["profile_changed_upstream"] = up
        except GitError:
            out["ahead"] = out["behind"] = None                # grana bez upstream-a
            out["profile_changed_upstream"] = []
        changed = []
        for line in _git("status", "--porcelain", "--", *SHARED).splitlines():
            changed.append({"state": line[:2].strip() or "?", "file": line[3:]})
        out["changed"] = changed
    except GitError as e:
        out["error"] = str(e)
    return out


def pull():
    _git("pull", "--ff-only", timeout=180)
    return status()


def save(message):
    """Taktike i profili -> commit -> push. Ostali fajlovi se ne diraju."""
    message = (message or "").strip()
    if not message:
        raise ValueError("write what you changed (commit message)")
    _git("add", "--", *SHARED)
    if not _git("diff", "--cached", "--name-only").strip():
        raise ValueError("nothing to save: no changed tactics or profiles")
    _git("commit", "-m", message)
    try:
        _git("push", timeout=180)
    except GitError as e:
        raise GitError("saved locally (commit), but push failed: %s. Try Pull latest, then Save again." % e)
    return status()
