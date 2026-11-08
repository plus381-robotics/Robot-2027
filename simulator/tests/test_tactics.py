# F2: pomoć za API iz tac.py, provera taktike, linije koraka i izuzetaka u simulaciji, čuvanje.
import pytest

from eurosim import paths, tactics as T
from eurosim.sim import simulate


@pytest.fixture(scope="module")
def api():
    return T.tac_api()


def msgs(src, api):
    return [(d["line"], d["severity"], d["msg"]) for d in T.static_check(src, api)]


def test_api_iz_tac_py(api):
    f = api["funcs"]
    assert set(f) >= {"goto", "turn_to", "turn_by", "move", "wait", "actuator", "here", "Abort"}
    assert f["goto"]["sig"].startswith("goto(x, y, deg=None")
    assert "True" in f["goto"]["doc"] or f["goto"]["doc"]
    assert "staro ime za turn_to" in f["rotate"]["doc"]
    assert "hvataljka" in api["actuators"] and api["ref_side"] == "zuta"


@pytest.mark.parametrize("name", sorted(p.stem for p in paths.TACTICS.glob("*.py")))
def test_postojece_taktike_bez_gresaka(name, api):
    errs = [m for m in msgs((paths.TACTICS / (name + ".py")).read_text(encoding="utf-8"), api) if m[1] == "error"]
    assert errs == []


def test_greske_sa_linijama(api):
    src = ("from tac import *\nSTART = (X0, 1000)\ngoto(600)\ngoto(600, 1000, sped=3)\n"
           "actuator('hvatljka', 1)\nfoo(1)\ngoto(3500, 1000)\nwhile True:\n    x = 1\n")
    m = msgs(src, api)
    got = {(line, sev) for line, sev, _ in m}
    assert {(2, "error"), (3, "error"), (4, "error"), (5, "error"), (6, "error"), (7, "warning"), (8, "error")} <= got
    assert any("sped" in t for _, _, t in m) and any("hvatljka" in t for _, _, t in m)


def test_sintaksa(api):
    d = T.static_check("from tac import *\ngoto(1, 2\n", api)
    assert d[0]["source"] == "syntax" and d[0]["line"] == 2


def test_bez_from_tac_import(api):
    assert any("from gambit import" in t for _, _, t in msgs("START = (250, 1000, 0)\ngoto(1, 2)\n", api))


def test_gambit_micro_ime_modula(api):
    """from gambit import * (Gambit Micro) radi isto kao staro from tac import *."""
    for mod in ("gambit", "tac"):
        assert not [t for _, sev, t in msgs("from %s import *\nSTART = (250, 1000, 0)\ngoto(600, 1000)\n" % mod, api)
                    if sev == "error"]


def test_mpy_cross(api):
    mp = T.mpy_check("x = 1\n")
    if mp is None:
        pytest.skip("mpy-cross nije instaliran")
    assert mp == []


def test_linije_koraka_i_izuzetka(tmp_path):
    (tmp_path / "t.py").write_text("from tac import *\nSTART = (250, 1000, 0)\ngoto(600, 1000)\n\n"
                                   "turn_to(90)\nx = 1 / 0\n")
    r = simulate("t", tactics_dir=tmp_path, mode="test")
    assert [e[2] for e in r.of("line")] == [[1, 3], [2, 5]]
    assert r.of("exception")[0][2]["line"] == 6
    d = T.runtime_diags(r.to_dict())
    assert any(x["line"] == 6 and "ZeroDivisionError" in x["msg"] for x in d)


def test_cuvanje_i_konflikt(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "TACTICS", tmp_path)
    r = T.save("nova", "from tac import *\n")
    assert r["saved"] == "nova" and T.read("nova")["sha"] == r["sha"]
    assert T.save("nova", "x = 1\n", r["sha"])["saved"]
    assert T.save("nova", "x = 2\n", r["sha"]).get("conflict")             # stara verzija
    assert T.save("nova", "x = 3\n", None).get("conflict")                  # postoji, a editor misli da je nov
    with pytest.raises(ValueError):
        T.path_of("../zlo")


def test_gambit_micro_pomoc_za_svaku_komandu():
    """Plan S4: panel Commands ima objašnjenje običnim jezikom za svaku komandu iz tac.__all__."""
    from eurosim import apidoc
    api = T.tac_api()
    assert api["name"] == "Gambit Micro"
    missing = [n for n in api["funcs"] if not api["funcs"][n]["help"]]
    assert not missing, missing
    for n, h in apidoc.DOC.items():
        assert n in api["funcs"], "opis za komandu koje nema u tac.py: " + n
        assert h["say"] and h["group"] and "example" in h
        if api["funcs"][n]["kind"] == "function":                       # parametri kao u tac.py
            assert [p for p, _ in h["params"]] == [p for p, _ in api["funcs"][n]["params"]], n
