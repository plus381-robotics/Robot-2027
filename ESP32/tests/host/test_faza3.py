# Faza 3: upload server (pravi TCP na laptopu), esp_push, telemetrija (pravi UDP), WiFi.
import hashlib
import json
import os
import socket
import sys
import threading
import time

import pytest

from conftest import ESP

sys.path.append(str(ESP.parent / "tools"))     # na kraj: tools/tactic.py ne sme da zakloni lib/tactic.py


@pytest.fixture
def server(tmp_path, monkeypatch, app):
    """Upload server sa korenom u tmp_path, na slobodnom portu, poll u pozadinskoj niti."""
    import state
    import upload
    import espnet
    monkeypatch.setattr(state, "MODE", "STA")
    monkeypatch.setattr(upload, "ROOT", str(tmp_path / "esp"))
    monkeypatch.setattr(upload, "_password", lambda: "tajna")
    (tmp_path / "esp").mkdir()
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    up = upload.Upload(app, {}, None, port=port)
    monkeypatch.setattr(espnet, "PORT", port)
    stop = threading.Event()
    slow = [0.0]

    def loop():
        while not stop.is_set():
            t = time.perf_counter()
            up.poll()
            slow[0] = max(slow[0], time.perf_counter() - t)
            time.sleep(0.001)
    th = threading.Thread(target=loop, daemon=True)
    th.start()
    for _ in range(200):                       # sačekaj da server zaista sluša
        if up.s is not None:
            break
        time.sleep(0.005)
    yield up, tmp_path / "esp", slow
    stop.set()
    th.join(1)


def q(cmd, data=b"", pw="tajna"):
    import espnet
    return espnet.query("127.0.0.1", pw, cmd, data, tries=1)


def test_prijava_bez_lozinke_u_cistom_tekstu(server):
    assert q("LIST", pw="pogresna")[-1].startswith("ERR pogresna")
    assert q("LIST")[-1] == "OK"


def test_put_list_del_i_putanje(server):
    up, root, _ = server
    data = b"print('hi')\n"
    sha = hashlib.sha256(data).hexdigest()
    assert q("PUT /tactics/a.py %d %s" % (len(data), sha), data)[-1].startswith("OK")
    assert (root / "tactics" / "a.py").read_bytes() == data
    assert "/tactics/a.py %d %s" % (len(data), sha) in q("LIST")
    for bad in ("/lib/../x.py", "/etc/passwd", "/lib/a.txt", "/tactics/a%b.py"):
        assert "nedozvoljena" in q("PUT %s 1" % bad, b"x")[-1]
    assert q("DEL /tactics/a.py")[-1].startswith("OK") and not (root / "tactics" / "a.py").exists()


def test_pogresan_sha_ne_menja_fajl(server):
    up, root, _ = server
    (root / "lib").mkdir()
    (root / "lib" / "x.py").write_bytes(b"staro")
    assert "sha256" in q("PUT /lib/x.py 4 %s" % ("0" * 64), b"novo")[-1]
    assert (root / "lib" / "x.py").read_bytes() == b"staro"


def test_stage_commit_atomicno(server):
    up, root, _ = server
    a, b = b"A" * 10, b"B" * 20
    q("STAGE /lib/a.py %d %s" % (len(a), hashlib.sha256(a).hexdigest()), a)
    q("STAGE /main.py %d %s" % (len(b), hashlib.sha256(b).hexdigest()), b)
    assert not (root / "lib" / "a.py").exists()            # ništa se ne menja do COMMIT
    assert q("COMMIT v1.2-test")[-1] == "OK 2 fajlova"
    assert (root / "lib" / "a.py").read_bytes() == a and (root / "main.py").read_bytes() == b
    assert (root / "version.txt").read_text() == "v1.2-test"


def test_veliki_fajl_ne_blokira_petlju(server):
    """T-1: 60 KB stiže u delovima; nijedan poll() ne traje dugo."""
    up, root, slow = server
    data = os.urandom(60000)
    assert q("PUT /tactics/big.py %d %s" % (len(data), hashlib.sha256(data).hexdigest()), data)[-1].startswith("OK")
    assert (root / "tactics" / "big.py").read_bytes() == data
    assert slow[0] < 0.05


def test_dok_radi_taktika_samo_log_stop_stat(server, app):
    app.running = "t"
    for cmd in ("PUT /x.py 1", "RESET", "FLASH 4", "RUN t", "LIST"):
        assert q(cmd, b"x")[-1].startswith("ERR taktika radi")
    assert q("LOG 0")[-1].endswith("1")
    app.running = None


def test_esp_push_salje_samo_izmenjeno(server, monkeypatch, capsys):
    up, root, _ = server
    import esp_push
    monkeypatch.setattr(sys, "argv", ["esp_push", "--host", "127.0.0.1", "--password", "tajna", "--no-reset"])
    esp_push.main()
    assert (root / "lib" / "upload.mpy").exists() and not (root / "lib" / "upload.py").exists()   # lib kao .mpy
    assert (root / "version.txt").exists()
    capsys.readouterr()
    esp_push.main()
    assert "ništa za slanje" in capsys.readouterr().out


def test_telemetrija_udp(app, monkeypatch):
    import state
    import telem
    monkeypatch.setattr(state, "MODE", "STA")
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    t = telem.Telem(app, port=port)
    t.poll()
    c = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    c.settimeout(1)
    c.sendto(b"WATCH", ("127.0.0.1", port))
    app.tlog("probni red")
    from conftest import run
    for _ in range(50):
        run(app, 20)
        t.poll()
    d = json.loads(c.recv(4096))
    assert d["ok"] and "x" in d and "probni red" in d.get("log", [])


def test_wifi_se_ponovo_povezuje(monkeypatch):
    import network
    import state
    import compat
    from net import Net
    monkeypatch.setattr(state, "MODE", None)
    n = Net()
    network.connected[0] = False
    n.poll()                                              # prva mreža
    network.connected[0] = True
    n.poll()
    assert state.MODE == "STA" and n.sta.cfg.get("pm") == 0
    network.connected[0] = False
    for _ in range(8):
        compat.sleep_ms(1000)
        n.poll()
    assert state.MODE is None                             # ikonica opet trepće
    network.connected[0] = True
    for _ in range(3):
        n.poll()
    assert state.MODE == "STA"


def test_rescue_rezim(server):
    """R-1: kad main.py padne, upload radi bez app-a: popravka bez kabla, ali ništa ne pokreće."""
    up, root, _ = server
    app, up.app, up.error = up.app, None, ["GRESKA", "ImportError"]
    try:
        assert "ImportError" in q("LOG 0")
        assert q("RUN t")[-1].startswith("ERR rescue")
        assert q("LIST")[-1] == "OK"
    finally:
        up.app, up.error = app, None


def test_wifi_ne_povezuje_ponovo_dok_taktika_radi(monkeypatch):
    import network
    import state
    import compat
    from net import Net
    monkeypatch.setattr(state, "MODE", None)
    busy = [False]
    n = Net(lambda: busy[0])
    network.connected[0] = True
    n.poll()
    n.poll()
    assert state.MODE == "STA"
    busy[0] = True
    network.connected[0] = False
    for _ in range(8):
        compat.sleep_ms(1000)
        n.poll()
    assert state.MODE == "STA"                            # čeka kraj taktike
    busy[0] = False
    compat.sleep_ms(1000)
    n.poll()
    assert state.MODE is None
