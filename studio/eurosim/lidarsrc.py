# Izvori lidara za simulaciju (hibridna simulacija): pogon, odometrija, IR i protivnici su simulirani, a krugovi
# lidara dolaze spolja i idu simuliranom ESP-u kroz lažni RPLIDAR (ESP32/sim/fakelidar.py push_scan), pa ih
# ESP kod čita istim drajverom (lib/lidar.py) kao na robotu.
#
#   RobotLidar  pravi lidar na robotu: upload komanda "LIDAR ON" (lozinka), pa krugovi iz telemetrije (UDP 8268,
#               binarni paket ESP32/lib/lidarpkt.py). Svaki krug se snima u studio/lidar/<vreme>.jsonl.gz.
#   FileLidar   snimak (.jsonl.gz): krugovi po vremenu simulacije, u krug (ponavlja se); radi i u brzoj simulaciji.
#
# poll(t_ms) -> lista krugova (dict: bins, hz, near) koji su stigli do trenutka t (ms simulacije).
import gzip
import importlib.util
import json
import pathlib
import socket
import threading
import time

from . import paths

LIDAR_DIR_NAME = "lidar"


def lidar_dir():
    """Gde se čuvaju snimci lidara: studio/lidar/ (u repou) ili ~/Eurosim/lidar/."""
    d = paths.RUNS.parent / LIDAR_DIR_NAME if hasattr(paths, "RUNS") else pathlib.Path.home() / "Eurosim" / LIDAR_DIR_NAME
    return d


def recordings():
    d = lidar_dir()
    return sorted(p.name for p in d.glob("*.jsonl.gz")) if d.exists() else []


_PKT = None


def pkt():
    """ESP32/lib/lidarpkt.py (format paketa), učitan po putanji: server ne stavlja ESP kod u sys.path."""
    global _PKT
    if _PKT is None:
        spec = importlib.util.spec_from_file_location("_eurosim_lidarpkt", paths.ESP / "lib" / "lidarpkt.py")
        _PKT = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_PKT)
    return _PKT


class RobotLidar:
    """Krugovi sa pravog robota preko WiFi-ja. Nit prima UDP; poll() predaje sve primljeno od prošlog poziva."""
    kind = "robot"

    def __init__(self, host, password, upload_port=8267, telem_port=8268, record=True, command=None):
        self.host, self.password = host, password
        self.upload_port, self.telem_port = upload_port, telem_port
        self._command = command                   # (host, pw, cmd, port) -> (ok, redovi); testovi ga menjaju
        self.received = 0
        self.error = None
        self.state = None                         # odgovor na LIDAR ON (stanje lidara na robotu)
        self._q = []
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._t0 = time.monotonic()
        self.file = None
        self._rec = None
        if record:
            d = lidar_dir()
            d.mkdir(parents=True, exist_ok=True)
            self.file = d / time.strftime("%Y%m%d-%H%M%S.jsonl.gz")
            self._rec = gzip.open(self.file, "wt", encoding="utf-8")
            self._rec.write(json.dumps({"meta": {"source": "robot", "host": host, "start": time.time()}}) + "\n")
        addr = socket.getaddrinfo(host, telem_port, socket.AF_INET, socket.SOCK_DGRAM)[0][4]
        self.addr = addr
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("0.0.0.0", 0))
        self.sock.settimeout(0.2)
        self._cmd("LIDAR ON")
        self._th = threading.Thread(target=self._run, daemon=True)
        self._th.start()

    def describe(self):
        return "robot %s" % self.host

    def _cmd(self, c):
        if self._command:
            ok, lines = self._command(self.host, self.password, c, self.upload_port)
        else:
            from .robotlink import command
            ok, lines = command(self.host, self.password, c, port=self.upload_port, timeout=5)
        if not ok:
            self.error = (lines or ["bez odgovora"])[-1]
        elif c == "LIDAR ON":
            self.state = lines[-1][3:]
        return ok

    def _run(self):
        P = pkt()
        t_watch = 0
        while not self._stop.is_set():
            if time.monotonic() - t_watch > 2:
                t_watch = time.monotonic()
                try:
                    self.sock.sendto(b"WATCH", self.addr)
                except OSError:
                    pass
            try:
                data = self.sock.recv(2048)
            except (socket.timeout, OSError):
                continue
            s = P.parse_lidar(data)
            if s is None:
                continue                          # JSON stanje robota: ovde ne treba
            self.received += 1
            s["rx"] = int((time.monotonic() - self._t0) * 1000)
            with self._lock:
                self._q.append(s)
            if self._rec:
                self._rec.write(json.dumps({"t": s["rx"], "bins": s["bins"], "hz": s["hz"], "near": s["near"]}) + "\n")

    def poll(self, t_ms):
        with self._lock:
            out, self._q = self._q, []
        return out

    def close(self):
        self._stop.set()
        self._th.join(1)
        try:
            self._cmd("LIDAR OFF")
        except Exception:                          # noqa: BLE001  (robot nestao: sam se gasi posle par sekundi)
            pass
        self.sock.close()
        if self._rec:
            self._rec.close()
            self._rec = None


class FileLidar:
    """Snimak krugova (.jsonl.gz od RobotLidar): krug ide kad vreme simulacije stigne do njegovog vremena;
    posle poslednjeg ispočetka (loop=True)."""
    kind = "file"

    def __init__(self, path, loop=True):
        p = pathlib.Path(path)
        if not p.is_absolute() and not p.exists():
            p = lidar_dir() / p
        self.path = p
        self.scans = []
        with gzip.open(p, "rt", encoding="utf-8") as f:
            for line in f:
                d = json.loads(line)
                if "bins" in d:
                    self.scans.append(d)
        if not self.scans:
            raise ValueError("snimak lidara bez krugova: %s" % p.name)
        t0 = self.scans[0]["t"]
        for s in self.scans:
            s["t"] -= t0
        self.period = self.scans[-1]["t"] + 100    # trajanje jednog prolaza (ms)
        self.loop = loop
        self.error = None
        self._start = None
        self._i = 0
        self._round = 0
        self.received = 0

    def describe(self):
        return "snimak %s" % self.path.name

    def poll(self, t_ms):
        if self._start is None:
            self._start = t_ms
        el = t_ms - self._start
        out = []
        while True:
            if self._i >= len(self.scans):
                if not self.loop:
                    return out
                self._i, self._round = 0, self._round + 1
            s = self.scans[self._i]
            if s["t"] + self._round * self.period > el:
                return out
            out.append(s)
            self._i += 1
            self.received += 1

    def close(self):
        pass


def open_source(spec, password=None):
    """"sim"/None -> None; "robot:<host>" -> RobotLidar; "file:<ime ili putanja>" -> FileLidar."""
    if not spec or spec == "sim":
        return None
    kind, _, arg = spec.partition(":")
    if kind == "robot":                           # robot:<host>[:<upload port>[:<telem port>]]
        if password is None:
            from .robotlink import default_password
            password = default_password()
        host, *ports = (arg or "eurokik.local").split(":")
        return RobotLidar(host, password, *(int(p) for p in ports[:2]))
    if kind == "file":
        return FileLidar(arg)
    raise ValueError("izvor lidara: sim, robot:<host> ili file:<snimak>")
