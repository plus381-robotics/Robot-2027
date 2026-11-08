# Protokol v3: STATUS.last_seq/last_result (ishod kretanja i kad se DONE/FAIL izgubi); stari STATUS (v2).
import struct

import protocol as P
from conftest import run
from link import build_frame


def test_stari_status_v2_se_dekodira():
    payload = struct.pack("<hhhhBI", 100, 200, 9000, 50, 1, 1234)      # 13 B, bez v3 polja
    name, d = P.decode(P.STATUS, payload)
    assert name == "STATUS" and d["x"] == 100 and d["match_ms"] == 1234
    assert d["last_seq"] is None and d["last_result"] is None
    assert P.decode(P.STATUS, payload[:12]) == (None, {})                # pokvaren (ne na granici polja)


def test_izgubljen_fail_ishod_iz_statusa(app, stm):
    """FAIL STOPPED se izgubi: ranije je "kraj po STATUS-u" vraćao True; sad stiže tačan ishod."""
    from runner import run_tactic
    (app.tactics_dir / "t.py").write_text("from tac import *\nlog('rez %s' % move(300))\n")
    stm.motion_ms = 3000
    send = stm._send
    stm._send = lambda name, seq=0, **f: None if name == "FAIL" else send(name, seq, **f)
    run(app, 300)
    import compat
    t_stop = compat.ticks_ms() + 500
    done = []

    def spolja_stop():                       # npr. STOP sa drugog mesta: kretanje prekinuto, FAIL izgubljen
        if not done and compat.ticks_ms() >= t_stop:
            done.append(1)
            t, pl = P.encode("STOP")
            stm.write(build_frame(t, 250, pl))
    app.loop.services.insert(0, ("stop", spolja_stop))
    run_tactic(app, "t")
    assert "rez False" in app.log
    assert any("STOPPED po STATUS-u" in l for l in app.log)


def test_izgubljen_done_ok_iz_statusa(app, stm):
    from runner import run_tactic
    (app.tactics_dir / "t.py").write_text("from tac import *\nlog('rez %s' % move(200))\n")
    stm.drop_done = 1
    run(app, 300)
    run_tactic(app, "t")
    assert "rez True" in app.log and any("OK po STATUS-u" in l for l in app.log)


def test_esp_radi_sa_starim_stm32_v2(app, stm):
    from runner import run_tactic
    stm.version = 2
    (app.tactics_dir / "t.py").write_text("from tac import *\nlog('rez %s' % move(200))\n")
    run(app, 300)
    assert app.robot.ok and not app.robot.can("result")
    run_tactic(app, "t")
    assert "rez True" in app.log
