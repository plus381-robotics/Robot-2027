# Okviri: COBS + CRC16. Isti kod radi na ESP32 (MicroPython) i na laptopu (CPython).
# Okvir na žici:  COBS(type | seq | payload | crc16_le) 0x00


def crc16(data, crc=0xFFFF):
    """CRC16-CCITT (poly 0x1021, init 0xFFFF). Mora se poklapati sa link.c."""
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else (crc << 1)
            crc &= 0xFFFF
    return crc


def cobs_encode(data):
    out = bytearray([0])
    code_i, code = 0, 1
    for b in data:
        if b == 0:
            out[code_i] = code
            code_i, code = len(out), 1
            out.append(0)
        else:
            out.append(b)
            code += 1
            if code == 0xFF:
                out[code_i] = code
                code_i, code = len(out), 1
                out.append(0)
    out[code_i] = code
    return bytes(out)


def cobs_decode(data):
    out = bytearray()
    i, n = 0, len(data)
    while i < n:
        code = data[i]
        if code == 0:
            return None
        i += 1
        end = i + code - 1
        if end > n:
            return None
        out += data[i:end]
        i = end
        if code < 0xFF and i < n:
            out.append(0)
    return bytes(out)


def build_frame(t, seq, payload=b""):
    body = bytes([t, seq]) + bytes(payload)
    c = crc16(body)
    return cobs_encode(body + bytes([c & 0xFF, c >> 8])) + b"\x00"


def parse_frame(raw):
    """raw = bajtovi između dve nule (bez nule). -> (type, seq, payload) ili None."""
    body = cobs_decode(raw)
    if body is None or len(body) < 4:
        return None
    c = body[-2] | (body[-1] << 8)
    if crc16(body[:-2]) != c:
        return None
    return body[0], body[1], body[2:-2]


class FrameParser:
    """Hrani se bajtovima kako stižu, vraća listu kompletnih okvira."""

    MAX = 512

    def __init__(self):
        self.buf = bytearray()
        self.errors = 0

    def feed(self, data):
        frames = []
        for b in data:
            if b == 0:
                if self.buf:
                    f = parse_frame(bytes(self.buf))
                    if f is None:
                        self.errors += 1
                    else:
                        frames.append(f)
                    self.buf = bytearray()
            elif len(self.buf) < self.MAX:
                self.buf.append(b)
            else:  # predugačko smeće, odbaci do sledeće nule
                self.buf = bytearray()
                self.errors += 1
        return frames
