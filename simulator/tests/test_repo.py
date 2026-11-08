# Repo kao radni prostor (plan S10): zapamćen repo, otvaranje foldera, stanje, pull i save, sa privremenim git
# repoima (lokalni "GitHub" je bare repo), bez mreže.
import os
import pathlib
import subprocess

import pytest

from eurosim import paths, repo

ROOT = pathlib.Path(__file__).resolve().parents[2]


def git(cwd, *a):
    return subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True, text=True).stdout


def mini_repo(path):
    """Najmanji Robot-2027: ESP32/lib/tac.py, simulator/, taktika i profil."""
    (path / "ESP32" / "lib").mkdir(parents=True)
    (path / "ESP32" / "tactics").mkdir()
    (path / "simulator" / "profiles").mkdir(parents=True)
    (path / "ESP32" / "lib" / "tac.py").write_text("x = 1\n")
    (path / "ESP32" / "tactics" / "a.py").write_text("a = 1\n")
    (path / "simulator" / "profiles" / "robot2027.toml").write_text((ROOT / "simulator" / "profiles" / "robot2027.toml").read_text())
    (path / "README.md").write_text("x\n")


@pytest.fixture
def team(tmp_path, monkeypatch):
    """bare "GitHub" + dva klona (ja i kolega); vraća (moj, kolegin)."""
    hub = tmp_path / "Robot-2027.git"
    git(tmp_path, "init", "--bare", "-b", "main", str(hub))
    seed = tmp_path / "seed"
    seed.mkdir()
    mini_repo(seed)
    git(seed, "init", "-b", "main")
    git(seed, "-c", "user.name=t", "-c", "user.email=t@t", "add", "-A")
    git(seed, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-m", "init")
    git(seed, "remote", "add", "origin", str(hub))
    git(seed, "push", "-u", "origin", "main")
    me, mate = tmp_path / "me" / "Robot-2027", tmp_path / "mate" / "Robot-2027"
    for d in (me, mate):
        d.parent.mkdir()
        git(d.parent, "clone", str(hub), str(d))
        git(d, "config", "user.name", "t")
        git(d, "config", "user.email", "t@t")
    old = paths.ROOT
    monkeypatch.setenv("EUROSIM_CONFIG", str(tmp_path / "cfg.json"))
    monkeypatch.setattr(paths, "USER_CFG", tmp_path / "cfg.json")
    yield me, mate
    paths.configure(root=old)


def test_open_folder_pamti_repo_i_odbija_tudji_folder(team, tmp_path):
    me, _ = team
    with pytest.raises(ValueError):
        repo.open_repo(tmp_path)                                   # nije Robot-2027
    r = repo.open_repo(me)
    assert paths.MODE == "repo" and paths.TACTICS == me.resolve() / "ESP32" / "tactics"
    assert paths.user_cfg()["repo"] == str(me.resolve())
    assert r["note"] == ""                                         # origin je Robot-2027 (ovde lokalni bare repo)


def test_status_pull_i_save(team):
    me, mate = team
    repo.open_repo(me)
    # kolega promeni profil i taktiku i pošalje
    (mate / "simulator" / "profiles" / "robot2027.toml").write_text("# promenjeno\n" + (mate / "simulator" / "profiles" / "robot2027.toml").read_text())
    git(mate, "commit", "-am", "profil")
    git(mate, "push")
    st = repo.status(fetch=True)
    assert st["behind"] == 1 and st["profile_changed_upstream"] == ["simulator/profiles/robot2027.toml"]
    st = repo.pull()
    assert st["behind"] == 0 and "# promenjeno" in (me / "simulator" / "profiles" / "robot2027.toml").read_text()
    # moja nova taktika -> Save to GitHub; README (nije deljeno) se ne šalje
    (me / "ESP32" / "tactics" / "b.py").write_text("b = 2\n")
    (me / "README.md").write_text("lokalno\n")
    st = repo.status()
    assert [c["file"] for c in st["changed"]] == ["ESP32/tactics/b.py"]
    with pytest.raises(ValueError):
        repo.save("")                                              # poruka je obavezna
    st = repo.save("b: nova taktika")
    assert st["changed"] == [] and st["ahead"] == 0
    git(mate, "pull")
    assert (mate / "ESP32" / "tactics" / "b.py").exists() and (mate / "README.md").read_text() == "x\n"
    with pytest.raises(ValueError):
        repo.save("ništa")                                         # nema izmena


def test_bez_repoa_status_kaze_da_nije_repo(monkeypatch, tmp_path):
    old = paths.ROOT
    monkeypatch.setenv("EUROSIM_NO_REPO", "1")
    try:
        paths.configure(home=tmp_path / "home")
        assert paths.MODE == "standalone" and repo.status() == {"repo": False}
        assert (tmp_path / "home" / "tactics" / "primer.py").exists()             # lokalno, samo na ovom računaru
    finally:
        monkeypatch.delenv("EUROSIM_NO_REPO")
        os.environ.pop("EUROSIM_HOME", None)
        paths.configure(root=old)
