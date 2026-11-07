import compat
import protocol as P
from robot import Robot


def pump(r, ms):
    ev = []
    end = compat.ticks_ms() + ms
    while compat.ticks_ms() < end:
        ev += r.poll()
        compat.sleep_ms(5)
    return ev


def test_veza_i_verzije(stm):
    r = Robot(stm)
    pump(r, 200)
    assert r.ok and r.version == P.VERSION
    stm.version = 1                            # Nucleo sa protokolom v1 (P-4)
    r2 = Robot(stm)
    pump(r2, 200)
    assert r2.ok and not r2.can("bootloader")
    stm.version = 99
    r3 = Robot(stm)
    pump(r3, 200)
    assert r3.alive and not r3.ok


def test_stop_posle_izgubljenog_ack_ne_pokrece_ponovo_goto(stm):
    """P-1: GOTO izvršen, ACK izgubljen, pa STOP. Stari kod je ponovio GOTO posle STOP-a."""
    r = Robot(stm)
    pump(r, 200)
    stm.drop_ack = 1
    g = r.send("GOTO", x=500, y=0, theta=0, flags=2, max_speed=300)
    compat.sleep_ms(10)
    r.send("STOP")
    ev = pump(r, 400)
    assert stm.executed == ["GOTO", "STOP"]
    assert (g, "GOTO", "timeout", "SUPERSEDED") in ev


def test_ponavljanje_i_bez_odgovora(stm):
    r = Robot(stm)
    pump(r, 200)
    stm.drop = 2
    s = r.send("SET_POSE", x=1, y=2, theta=3)
    ev = pump(r, 300)
    assert (s, "SET_POSE", "ok", None) in ev and r.retries == 2
    stm.drop = 3
    s = r.send("SET_POSE", x=1, y=2, theta=3)
    ev = pump(r, 300)
    assert (s, "SET_POSE", "timeout", "NOREPLY") in ev


def test_seq_nikad_nula(stm):
    r = Robot(stm)
    seqs = {r.send("STOP") for _ in range(600)}
    assert 0 not in seqs and seqs == set(range(1, 256))


def test_pauza_pinga_se_meri(stm):
    r = Robot(stm)
    pump(r, 1100)
    compat.sleep_ms(400)                       # petlja "zaglavljena" 400 ms
    pump(r, 1100)
    assert r.ping_gap >= 400                   # vidi se u merenju (ekran VEZA, upload STAT)
