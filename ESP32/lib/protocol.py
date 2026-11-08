# GENERISANO iz protocol/protocol.yaml - ne menjati ručno
# Radi i u MicroPythonu i u CPythonu.
import struct

VERSION = 4

class Reason:
    INVALID = 1
    BLOCKED = 2
    TIMEOUT = 3
    PREEMPTED = 4
    MATCH_OVER = 5
    STOPPED = 6
    LINK = 7

class GotoFlags:
    REVERSE = 1
    NO_THETA = 2

class State:
    MOVING = 1
    BLOCKED = 2
    MATCH_RUNNING = 4
    MATCH_OVER = 8

class ResetCause:
    PIN = 1
    POWER = 2
    SOFT = 4
    IWDG = 8
    WWDG = 16
    LOW_POWER = 32

PING = 0x01
SET_POSE = 0x10
GOTO = 0x11
ROTATE = 0x12
MOVE = 0x13
STOP = 0x1F
ACTUATOR = 0x20
MATCH_START = 0x30
RESUME = 0x32
ENTER_BOOTLOADER = 0x40
RESET = 0x41
PONG = 0x81
ACK = 0x90
DONE = 0x91
FAIL = 0x92
STATUS = 0xA0
LOG = 0xF0

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
    0x32: ('RESUME', '<hhhI', ('x', 'y', 'theta', 'elapsed_ms'), None, 10),
    0x40: ('ENTER_BOOTLOADER', '<', (), None, 0),
    0x41: ('RESET', '<', (), None, 0),
    0x81: ('PONG', '<BB', ('version', 'reset_cause'), None, 1),
    0x90: ('ACK', '<', (), None, 0),
    0x91: ('DONE', '<', (), None, 0),
    0x92: ('FAIL', '<B', ('reason',), None, 1),
    0xA0: ('STATUS', '<hhhhBIBBIh', ('x', 'y', 'theta', 'v', 'state', 'match_ms', 'last_seq', 'last_result', 'uptime_ms', 'w'), None, 13),
    0xF0: ('LOG', '<', (), 'text', 0),
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
