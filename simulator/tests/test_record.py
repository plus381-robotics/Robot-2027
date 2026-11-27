# Snimak v2: upgrade v1, telemetrija bez izmišljenih polja, step_end iz telemetrije.
import gzip
import json

from eurosim import record, robotlink


def test_v1_snimak_se_ucitava(tmp_path):
    v1 = {"version": 1, "meta": {"tactic": "primer", "source": "tekst taktike"}, "result": {},
          "frames": [{"t": 0, "x": 1}], "events": []}
    d = record.upgrade(json.loads(json.dumps(v1)))
    assert d["version"] == 2 == record.VERSION
    assert d["meta"]["origin"]["engine"] == "sim"
    assert d["meta"]["source"] == "tekst taktike"          # tekst taktike ostaje netaknut
    v1["result"] = {"robot": True}
    assert record.upgrade(v1)["meta"]["origin"]["engine"] == "robot"
    p = tmp_path / "a.json.gz"
    with gzip.open(p, "wt", encoding="utf-8") as f:
        json.dump({"version": 1, "meta": {}, "result": {}, "frames": [], "events": []}, f)
    assert record.Recording.load(p).meta["origin"]["engine"] == "sim"


def test_telemetrija_nema_laznih_polja():
    r = robotlink.TelemRecorder({})
    r.feed({"t": 1000, "x": 10, "y": 20, "th": 5, "sp": 100, "st": 1, "ok": True}, 0)
    f = r.frames[0]
    for k in ("ox", "oy", "oth", "w", "vl", "vr", "v_ref", "w_ref", "reg", "ir"):
        assert k not in f
    assert f["x"] == 10


def test_step_end_iz_telemetrije_ima_prednost():
    r = robotlink.TelemRecorder({})
    r.feed({"t": 1000, "step_end": [3, "x", True, None, 1200]}, 0)
    assert [e[2] for e in r.events if e[1] == "step_end"] == [[3, "x", True, None, 1200]]
    assert not r.pending


def test_robot_recording_ima_origin():
    link = robotlink.RobotLink("h", "pw", None, {"name": "p", "body": {}, "drive": {}})
    d = link.recording()
    assert d["version"] == 2
    assert d["meta"]["origin"] == {"engine": "robot", "parts": {"pogon": "pravi", "lidar": "pravi", "ir": "pravi",
                                                                "mehanizmi": "pravi", "protivnici": "pravi"}}
    assert d["meta"]["tactic_sha"] is None and d["meta"]["scenario"] is None
    assert d["result"]["robot"] is True


def test_sim_meta_ima_origin_i_sha():
    from eurosim import tactics
    from eurosim.sim import Sim
    m = Sim("primer", mode="test").rec.meta
    assert m["origin"]["engine"] == "sim"
    assert m["origin"]["parts"]["pogon"] == "sim" and m["origin"]["parts"]["lidar"] == "sim"
    assert m["tactic_sha"] == tactics.sha(m["source"])
    assert m["scenario"] is None and isinstance(m["source"], str)


def _steps(r):
    return [e[2] for e in r.events if e[1] == "step_end"]


def _pk(t, step=None, **kw):
    d = {"t": t, "tac": "tt", "i": 1, "side": "zuta", "n": 3}
    if step:
        d["step"] = step
    d.update(kw)
    return d


def test_step_end_log_pa_telemetrija_jedan_dogadjaj():
    r = robotlink.TelemRecorder({})
    r.feed(_pk(1000, "x"), 0)
    r.feed(_pk(1100, None, log=["x: OK 0.1s"]), 0)        # korak se zatvara, dnevnik daje ishod
    r.feed(_pk(1200, None, step_end=[1, "x", True, None, 100]), 0)
    assert len(_steps(r)) == 1


def test_step_end_ponovljen_korak_ne_gubi_ishod():
    r = robotlink.TelemRecorder({})
    r.feed(_pk(1000, "x"), 0)
    r.feed(_pk(1100, None, log=["x: OK 0.1s"]), 0)
    r.feed(_pk(1200, None, step_end=[1, "x", True, None, 100]), 0)
    r.feed(_pk(2000, "x"), 0)                              # isti indeks ponovo
    r.feed(_pk(2100, None, log=["x: BLOCKED"]), 0)
    s = _steps(r)
    assert len(s) == 2 and s[1][2] is False and s[1][3] == "BLOCKED"


def test_step_end_telemetrija_pre_zatvaranja_jedan_dogadjaj():
    r = robotlink.TelemRecorder({})
    r.feed(_pk(1000, "x"), 0)
    r.feed(_pk(1100, "x", step_end=[1, "x", True, None, 100]), 0)
    r.feed(_pk(1200, None, log=["x: OK 0.1s"]), 0)
    r.feed(_pk(3000, None), 0)
    assert len(_steps(r)) == 1
