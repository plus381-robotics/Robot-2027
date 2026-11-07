from upload import Upload


class Conn:
    """Lažni socket: zadati ulaz, beleži izlaz."""
    def __init__(self, data):
        self.data, self.out = data, b""

    def read(self, n):
        d, self.data = self.data[:n], self.data[n:]
        return d

    def write(self, b):
        self.out += b

    def settimeout(self, t):
        pass


def serve(up, text, monkeypatch):
    import upload
    monkeypatch.setattr(upload, "_password", lambda: "pw")
    c = Conn(text.encode())
    up._serve(c)
    return c.out.decode()


def test_dok_taktika_radi_dozvoljeni_samo_log_stop_stat(app, monkeypatch):
    """A-2: upis fajlova, restart i flešovanje usred taktike se odbijaju."""
    up = Upload(app, {}, None)
    app.running = "t"
    for cmd in ("PUT /x.py 1", "RESET", "FLASH 4", "RUN t"):
        assert serve(up, "pw\n%s\n" % cmd, monkeypatch).startswith("ERR taktika radi")
    assert serve(up, "pw\nLOG 0\n", monkeypatch).strip().endswith("1")


def test_rescue_rezim(monkeypatch):
    up = Upload(None, None, None, error=["GRESKA", "ImportError"])
    assert "ImportError" in serve(up, "pw\nLOG 0\n", monkeypatch)
    assert serve(up, "pw\nRUN x\n", monkeypatch).startswith("ERR rescue")


def test_pogresna_lozinka(app, monkeypatch):
    assert serve(Upload(app, {}, None), "xx\nRESET\n", monkeypatch).startswith("ERR pogresna")
