# Protivnik sa taktikom (plan E4): ide po svojoj taktici (ogledanoj na svoju stranu), PAMI kreće u poslednjih
# 15 s, stoji kad bi udario u naš robot, gura kamenolome, ponovljivo.
from eurosim import opponents
from eurosim.sim import simulate

WAIT = "from gambit import *\nSTART = (250, 1000, 0)\nwait({s})\n"


def write(tmp_path, src):
    (tmp_path / "t.py").write_text(src)
    return tmp_path


def at(r, t):
    return min(r.frames, key=lambda f: abs(f["t"] - t))["opp"]


def cord(r):
    return next(e[0] for e in r.of("sim") if "cinc" in e[2]["text"])


def test_gotove_taktike_postoje():
    assert {"patrola", "ka_kamenolomu", "nasumicno", "pami_napred"} <= set(opponents.available())


def test_patrola_na_svojoj_strani(tmp_path):
    r = simulate("t", tactics_dir=write(tmp_path, WAIT.format(s=12)), side="zuta",
                 obstacles=[dict(name="opp", x=2750, y=1000, tactic="patrola")])
    xs = [f["opp"][0][0] for f in r.frames if f["t"] > cord(r) + 3000]
    ys = [f["opp"][0][1] for f in r.frames if f["t"] > cord(r) + 3000]
    assert all(abs(x - 2300) < 5 for x in xs)                     # patrola na x = 700 ogledano na plavu
    assert max(ys) - min(ys) > 600                                 # ide gore-dole


def test_pami_krece_tek_posle_85s(tmp_path):
    r = simulate("t", tactics_dir=write(tmp_path, WAIT.format(s=97)), side="zuta",
                 obstacles=[dict(name="PAMI", kind="pami", x=2900, y=1600, w=150, h=120, z=130, th=180,
                                 tactic="pami_napred")])
    c = cord(r)
    assert at(r, c + 84000)[0][:2] == [2900, 1600]                 # stoji do 85. s
    assert at(r, c + 96000)[0][0] < 2300                           # pa vozi napred (ka sredini)


def test_protivnik_ne_prolazi_kroz_nas_robot(tmp_path):
    # naš robot stoji na x 1100; protivnik ide pravo na nas (ka_kamenolomu: 1900 ogledano = 1100, y 1500)
    src = "from gambit import *\nSTART = (1100, 1500, 0)\nwait(15)\n"
    r = simulate("t", tactics_dir=write(tmp_path, src), side="zuta", mode="test",
                 obstacles=[dict(name="opp", x=2750, y=1000, tactic="ka_kamenolomu")])
    f = r.frames[-1]
    assert f["opp"][0][0] > 1100 + 82 + 150 - 5                     # stao ispred našeg robota


def test_protivnik_gura_kamenolom_i_ponovljivo(tmp_path):
    kw = dict(tactics_dir=write(tmp_path, WAIT.format(s=10)), side="zuta",
              obstacles=[dict(name="opp", x=2750, y=1000, tactic="ka_kamenolomu")])
    r = simulate("t", **kw)
    ev = [e for e in r.events if e[1] == "elements"]
    q9 = [e for e in ev[-1][2] if e["name"] == "kamenolom 9"][0]
    assert q9["x"] < 1500 - 100                                    # srednji kamenolom gurnut ka nama
    r2 = simulate("t", **kw)
    assert [f["opp"] for f in r2.frames] == [f["opp"] for f in r.frames]
