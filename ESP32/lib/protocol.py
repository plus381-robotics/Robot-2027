# GENERISANO iz protocol/protocol.yaml - ne menjati ručno
# Radi i u MicroPythonu i u CPythonu.
import struct

VERSION = 3

class Reason:
    INVALID = 1
    BLOCKED = 2
    TIMEOUT = 3
    PREEMPTED = 4
    MATCH_OVER = 5
    STOPPED = 6

class GotoFlags:
    REVERSE = 1
    NO_THETA = 2

class State:
    MOVING = 1
    BLOCKED = 2
    MATCH_RUNNING = 4
    MATCH_OVER = 8
    LINK_LOST = 16

class Debug:
    LIDAR = 1
    CONTROL = 2

PING = 0x01
SET_POSE = 0x10
GOTO = 0x11
ROTATE = 0x12
MOVE = 0x13
STOP = 0x1F
ACTUATOR = 0x20
MATCH_START = 0x30
DEBUG_STREAMS = 0x31
ENTER_BOOTLOADER = 0x40
PONG = 0x81
ACK = 0x90
DONE = 0x91
FAIL = 0x92
STATUS = 0xA0
LIDAR_SCAN = 0xB0
CONTROL_DEBUG = 0xB1
LOG = 0xF0
TACTIC_EVENT = 0x70

# min = veličina bez polja koja postoje tek od novije verzije (starija poruka je kraća)
_MSGS = {
    0x01: ('PING', '<', (), None, 0),
    0x10: ('SET_POSE', '<hhh', ('x', 'y', 'theta'), None, 6),
    0x11: ('GOTO', '<hhhBH', ('x', 'y', 'theta', 'flags', 'max_speed'), None, 9),
    0x12: ('ROTATE', '<h', ('theta',), None, 2),
    0x13: ('MOVE', '<hH', ('dist', 'max_speed'), None, 4),
    0x1F: ('STOP', '<', (), None, 0),
    0x20: ('ACTUATOR', '<Bh', ('id', 'value'), None, 3),
    0x30: ('MATCH_START', '<', (), None, 0),
    0x31: ('DEBUG_STREAMS', '<B', ('mask',), None, 1),
    0x40: ('ENTER_BOOTLOADER', '<', (), None, 0),
    0x81: ('PONG', '<B', ('version',), None, 1),
    0x90: ('ACK', '<', (), None, 0),
    0x91: ('DONE', '<', (), None, 0),
    0x92: ('FAIL', '<B', ('reason',), None, 1),
    0xA0: ('STATUS', '<hhhhBIBB', ('x', 'y', 'theta', 'v', 'state', 'match_ms', 'last_seq', 'last_result'), None, 13),
    0xB0: ('LIDAR_SCAN', '<', (), 'points', 0),
    0xB1: ('CONTROL_DEBUG', '<hhhhhh', ('v_ref', 'v_meas', 'w_ref', 'w_meas', 'pwm_l', 'pwm_r'), None, 12),
    0xF0: ('LOG', '<', (), 'text', 0),
    0x70: ('TACTIC_EVENT', '<', (), 'text', 0),
}
NAMES = {v[0]: k for k, v in _MSGS.items()}


def encode(name, **kw):
    """encode('GOTO', x=..., y=...) -> (type, payload bytes)"""
    t = NAMES[name]
    _, fmt, names, tail, _ = _MSGS[t]
    payload = struct.pack(fmt, *[kw[n] for n in names]) if names else b""
    if tail:
        payload += bytes(kw.get(tail, b""))
    return t, payload


def decode(t, payload):
    """(type, payload) -> (ime, dict polja). Nepoznat tip -> (None, {})."""
    m = _MSGS.get(t)
    if m is None:
        return None, {}
    name, fmt, names, tail, mins = m
    size = struct.calcsize(fmt) if names else 0
    n = len(payload)
    if not tail and mins <= n < size:           # starija verzija: bez novijih polja na kraju
        k = len(names)
        while k and struct.calcsize(fmt[:k + 1]) > n:
            k -= 1
        if struct.calcsize(fmt[:k + 1]) != n:
            return None, {}
        d = dict(zip(names, struct.unpack(fmt[:k + 1], payload)))
        for f in names[k:]:
            d[f] = None
        return name, d
    if n < size or (not tail and n != size):
        return None, {}
    vals = struct.unpack(fmt, payload[:size]) if names else ()
    d = dict(zip(names, vals))
    if tail:
        d[tail] = bytes(payload[size:])
    return name, d
