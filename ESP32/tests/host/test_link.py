from link import build_frame, FrameParser, crc16


def test_okvir_tam_i_nazad():
    p = FrameParser()
    data = bytes(range(0, 60))                 # i nule u sadržaju
    out = p.feed(build_frame(0x11, 7, data) + build_frame(0x01, 0))
    assert out == [(0x11, 7, data), (0x01, 0, b"")]


def test_ostecen_okvir_se_odbacuje():
    p = FrameParser()
    f = bytearray(build_frame(0x11, 7, b"abc"))
    f[2] ^= 0xFF
    assert p.feed(bytes(f)) == [] and p.errors == 1


def test_crc_ccitt():
    assert crc16(b"123456789") == 0x29B1        # poznata vrednost za CRC16-CCITT (0xFFFF)
