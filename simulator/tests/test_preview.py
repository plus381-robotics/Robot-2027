# Nacrt putanje iz teksta taktike (plan S7): lažni tac, bez simulacije.
from eurosim import paths, preview as pv, tactics


def test_lazni_tac_ima_sve_komande_pravog():
    """Ako se u ESP32/lib/tac.py doda komanda, nacrt mora da je zna (inače NameError u nacrtu)."""
    api = tactics.tac_api()
    fk = pv._Fake("zuta", "zuta", 3000, True)
    m = pv._module(fk)
    missing = [n for n in api["funcs"] if not hasattr(m, n)]
    assert not missing, missing


def test_primer_nacrt_i_redovi():
    src = (paths.TACTICS / "primer.py").read_text(encoding="utf-8")
    r = pv.preview(src, "zuta")
    assert not r["error"] and not r["truncated"]
    kinds = [(c["kind"], c["label"]) for c in r["cmds"]]
    assert kinds == [("goto", "GOTO 600,1000"), ("turn", "OKRET na 90"), ("move", "MOVE -200")]
    g = r["cmds"][0]
    assert (g["x0"], g["y0"], g["x1"], g["y1"]) == (250, 1000, 600, 1000)
    assert src.splitlines()[g["line"] - 1].lstrip().startswith("if not goto(600")      # red u kodu
    m = r["cmds"][2]
    assert round(m["y1"]) == 800 and round(m["x1"]) == 600
    assert 3 < r["t"] < 5                                                              # simulacija: 3,4 s


def test_plava_ogledano_i_promenljive():
    src = "from tac import *\nSTART = (250, 1000, 0)\nX0 = 700\nfor i in range(2):\n    goto(X0 + 100 * i, 1500, deg=90)\n"
    r = pv.preview(src, "plava")
    assert [(c["x1"], c["y1"]) for c in r["cmds"]] == [(2300, 1500), (2200, 1500)]
    assert r["cmds"][0]["target"][2] == 90                                             # 180 - 90
    assert r["start"] == [2750, 1000, -180]


def test_beskonacna_petlja_i_previse_komandi_se_skracuju():
    r = pv.preview("from tac import *\nwhile True:\n    x = 1\n")
    assert r["truncated"] and "petlja" in r["truncated"]
    r = pv.preview("from tac import *\nwhile True:\n    move(10)\n")
    assert r["truncated"] and len(r["cmds"]) <= pv.MAX_CMDS


def test_greska_u_taktici_daje_red():
    r = pv.preview("from tac import *\ngoto(600, 1000)\nx = 1 / 0\n")
    assert r["error"]["line"] == 3 and "ZeroDivision" in r["error"]["msg"]
    assert len(r["cmds"]) == 1                                                        # ono pre greške ostaje
    r = pv.preview("goto(1,\n")
    assert r["error"]["line"] and r["error"]["msg"].startswith("sintaksa")


def test_timeup_i_except_exception_ne_gutaju_prekid():
    src = "from tac import *\ntry:\n    while True:\n        move(10)\nexcept Exception:\n    pass\n"
    r = pv.preview(src)
    assert r["truncated"]                                                             # _Stop nije Exception
