# SimSTM na nivou bajtova: ponašanje comm.c / comm_port.c koje ESP kod očekuje.
import math

import pytest

from eurosim import profile
from eurosim.stm import SimSTM, P
from link import build_frame, FrameParser


class Bench:
    """Šalje okvire kao ESP i skuplja odgovore; sat se pomera ručno."""

    def __init__(self, **over):
        self.now = [0]
        self.stm = SimSTM(profile.load(**over), lambda: self.now[0])
        self.parser = FrameParser()
        self.rx = []
        self.stm.plant.place(1000, 1000, 0)
        self.stm.plant.set_odom(1.0, 1.0, 0.0)

    def send(self, name, seq, **f):
        t, pl = P.encode(name, **f)
        self.stm.write(build_frame(t, seq, pl))
        self.read()

    def read(self):
        d = self.stm.read()
        for t, seq, pl in self.parser.feed(d or b""):
            nm, f = P.decode(t, pl)
            self.rx.append((self.now[0], nm, seq, f))

    def run(self, ms, ping=True):
        end = self.now[0] + ms
        while self.now[0] < end:
            self.now[0] += 10
            if ping and self.now[0] % 150 == 0:
                self.send("PING", 0)
            self.read()

    def replies(self, seq=None):
        return [(nm, f) for _, nm, s, f in self.rx if nm not in ("PONG", "STATUS") and (seq is None or s == seq)]

    def statuses(self):
        return [f for _, nm, _, f in self.rx if nm == "STATUS"]


def test_ping_pong_verzija_i_status_20hz():
    b = Bench()
    b.send("PING", 0)
    assert ("PONG", {"version": 4, "reset_cause": P.ResetCause.POWER}) in [(nm, f) for _, nm, _, f in b.rx]
    b.run(1000)
    assert 19 <= len(b.statuses()) <= 21


def test_goto_ack_pa_done_i_moving_bit():
    b = Bench()
    b.send("GOTO", 1, x=1300, y=1000, theta=0, flags=P.GotoFlags.NO_THETA, max_speed=500)
    assert b.replies(1) == [("ACK", {})]
    b.run(300)
    assert b.statuses()[-1]["state"] & P.State.MOVING
    b.run(3000)
    assert b.replies(1)[-1] == ("DONE", {})
    s = b.statuses()[-1]
    assert not s["state"] & P.State.MOVING
    assert abs(s["x"] - 1300) <= 20 and abs(s["y"] - 1000) <= 20


def test_duplikat_samo_ponovi_odgovor():
    b = Bench()
    b.send("GOTO", 7, x=1300, y=1000, theta=0, flags=2, max_speed=500)
    b.send("GOTO", 7, x=1300, y=1000, theta=0, flags=2, max_speed=500)
    assert b.replies(7) == [("ACK", {}), ("ACK", {})]
    assert [x for x in b.stm.trace if x[1] == "rx"][-1][2] == "GOTO"
    assert len([x for x in b.stm.trace if x[1] == "rx" and x[2] == "GOTO"]) == 2   # primljen 2x
    assert b.stm.motion_seq == 7                                                    # izvršen 1x


def test_nova_komanda_prekida_staru_preempted():
    b = Bench()
    b.send("GOTO", 1, x=1800, y=1000, theta=0, flags=2, max_speed=500)
    b.run(200)
    b.send("ROTATE", 2, theta=9000)
    assert ("FAIL", {"reason": P.Reason.PREEMPTED}) in b.replies(1)
    b.run(3000)
    assert b.replies(2)[-1] == ("DONE", {})


def test_stop_fail_stopped_i_ack():
    b = Bench()
    b.send("MOVE", 1, dist=500, max_speed=500)
    b.run(200)
    b.send("STOP", 2)
    assert b.replies(1)[-1] == ("FAIL", {"reason": P.Reason.STOPPED})
    assert b.replies(2) == [("ACK", {})]


def test_set_pose_dok_vozi_invalid():
    b = Bench()
    b.send("MOVE", 1, dist=500, max_speed=500)
    b.run(50)
    b.send("SET_POSE", 2, x=0, y=0, theta=0)
    assert b.replies(2) == [("FAIL", {"reason": P.Reason.INVALID})]


def test_nepoznata_komanda_invalid():
    b = Bench()
    b.send("ENTER_BOOTLOADER", 3)
    assert b.replies(3) == [("FAIL", {"reason": P.Reason.INVALID})]


def test_pad_veze_zaustavlja_i_nema_statusa():
    b = Bench()
    b.send("MOVE", 1, dist=800, max_speed=300)
    b.run(200)
    n = len(b.statuses())
    b.run(800, ping=False)
    assert b.replies(1)[-1] == ("FAIL", {"reason": P.Reason.LINK})       # v4: pad veze, ne STOP
    assert len(b.statuses()) - n <= 11                    # do 500 ms još šalje, posle ne
    b.send("PING", 0)                                     # ESP se vratio: seq ispočetka
    b.send("MOVE", 1, dist=100, max_speed=300)
    assert b.replies(1)[-1] == ("ACK", {})


def test_mec_100s_pa_match_over():
    b = Bench()
    b.send("MATCH_START", 1)
    b.run(1000)
    assert b.statuses()[-1]["state"] & P.State.MATCH_RUNNING
    b.send("MOVE", 2, dist=-200, max_speed=200)
    b.now[0] += 0
    b.run(100000)
    s = b.statuses()[-1]
    assert s["state"] & P.State.MATCH_OVER and s["match_ms"] == 100000
    b.send("GOTO", 3, x=0, y=0, theta=0, flags=2, max_speed=200)
    assert b.replies(3) == [("FAIL", {"reason": P.Reason.MATCH_OVER})]


def test_aktuator_ack_pa_done_posle_vremena():
    b = Bench(**{"actuators.default_ms": 400})
    b.send("ACTUATOR", 1, id=2, value=300)
    assert b.replies(1) == [("ACK", {})]
    b.run(300)
    assert b.replies(1) == [("ACK", {})]
    b.run(200)
    assert b.replies(1)[-1] == ("DONE", {})
    assert b.stm.act_state[2] == 300


def test_blackpill_bez_aktuatora_invalid():
    b = Bench(**{"actuators.enabled": False})
    b.send("ACTUATOR", 1, id=2, value=1)
    assert b.replies(1) == [("FAIL", {"reason": P.Reason.INVALID})]


@pytest.mark.parametrize("dist", [100, 500, 1200, -300])
def test_move_stize_u_toleranciji(dist):
    b = Bench()
    b.send("MOVE", 1, dist=dist, max_speed=800)
    b.run(6000)
    assert b.replies(1)[-1] == ("DONE", {})
    pl = b.stm.plant
    assert abs(pl.x * 1000 - (1000 + dist)) < 20 and abs(pl.y * 1000 - 1000) < 5


@pytest.mark.parametrize("deg", [90, -90, 179, 10])
def test_rotate_stize_u_toleranciji(deg):
    b = Bench()
    b.send("ROTATE", 1, theta=deg * 100)
    b.run(5000)
    assert b.replies(1)[-1] == ("DONE", {})
    err = (math.degrees(b.stm.plant.th) - deg + 180) % 360 - 180
    assert abs(err) < 1.0


def test_goto_sa_zavrsnim_uglom():
    b = Bench()
    b.send("GOTO", 1, x=1400, y=1300, theta=-9000, flags=0, max_speed=600)
    b.run(6000)
    assert b.replies(1)[-1] == ("DONE", {})
    pl = b.stm.plant
    assert math.hypot(pl.x * 1000 - 1400, pl.y * 1000 - 1300) < 20
    assert abs(math.degrees(pl.th) + 90) < 1.0


def test_zid_blocked():
    b = Bench()
    b.send("MOVE", 1, dist=-1500, max_speed=500)      # iza robota je ivica na x = 0
    b.run(6000)
    assert b.replies(1)[-1] == ("FAIL", {"reason": P.Reason.BLOCKED})
    assert b.stm.plant.x * 1000 == pytest.approx(82.5, abs=5)     # polovina dužine 165


def test_greska_odometrije_razdvaja_odometriju_i_stvarnu_pozu():
    b = Bench(**{"odometry.left_scale": 1.01})
    b.send("MOVE", 1, dist=1000, max_speed=600)
    b.run(5000)
    pl = b.stm.plant
    assert abs(pl.ox * 1000 - 2000) < 20                  # po odometriji je stigao
    assert abs(pl.y - pl.oy) * 1000 > 5                   # stvarno je skrenuo
