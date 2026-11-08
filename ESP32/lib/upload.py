# Upload preko WiFi-ja (TCP port 8267) za tools/esp_push.py, tools/flash_stm32.py i tools/tactic.py.
#
# Ne blokira glavnu petlju: jedna veza, automat stanja, najviše BUDGET bajtova po krugu petlje.
# Prijava bez lozinke u čistom tekstu: server pošalje "EURO2 <nonce>", klijent odgovori
# sha256(lozinka + nonce) heksadecimalno. Lozinka je ista kao za WebREPL (webrepl_cfg.PASS).
#
# Komande (posle prijave, jedan red; podaci odmah iza reda):
#   PUT <put> <dužina> [sha256]    upiši fajl odmah (preko .tmp, pa preimenuj)
#   STAGE <put> <dužina> sha256    upiši u /.new/<put>; ništa se ne menja do COMMIT
#   COMMIT [verzija]               sve iz /.new/ na mesto (jedan kratak krug preimenovanja), /version.txt
#   DEL <put>                      obriši fajl
#   LIST                           "put veličina sha256" za sve fajlove
#   RESET                          restartuj ESP
#   RUN <ime> [strana]             pokreni /tactics/<ime>.py odmah (test)
#   STOP                           prekini taktiku i pošalji STOP robotu
#   LOG <od>                       dnevnik taktike od rednog broja <od>; poslednji red "OK <n> <radi>"
#   STAT                           merenja petlje i veze, verzija koda
#   FLASH <dužina>                 STM32 .bin u /stm.bin pa flešovanje (stmflash.py; blokira, STM32 stoji)
# Odgovor: redovi, poslednji "OK ..." ili "ERR ...". Dok taktika radi ili je meč naoružan: samo
# LOG, STOP, STAT. U rescue režimu (app = None): samo upis/brisanje/lista, RESET i LOG.
import socket
import os
from compat import ticks_ms, ticks_diff

PORT = 8267
BUDGET = 2048                           # bajtova po krugu petlje
IDLE_MS = 3000                          # veza bez napretka se zatvara
ROOT = ""                               # prefiks putanja (testovi ga menjaju)
BUSY_OK = ("LOG", "STOP", "STAT")
RESCUE_OK = ("PUT", "STAGE", "COMMIT", "DEL", "LIST", "RESET", "LOG")
DATA_CMDS = ("PUT", "STAGE", "FLASH")
NEW = "/.new"
ALLOWED_ROOT = ("main.py", "config.py", "boot.py", "secrets.py", "webrepl_cfg.py", "version.txt")
ALLOWED_DIRS = ("lib", "tactics")
LIST_MS = 20                            # LIST radi najviše ovoliko po krugu petlje (fajl sistem je spor:
                                        # na WROOM-32 listdir ~380 ms, stat ~55 ms, open ~30 ms)
_sha_cache = {}                         # put -> (veličina, vreme izmene, sha256)


def _password():
    try:
        import webrepl_cfg
        return webrepl_cfg.PASS
    except Exception:
        return None


def _sha():
    import hashlib
    return hashlib.sha256()


def _hex(b):
    import binascii
    return binascii.hexlify(b).decode()


def check_path(p):
    """Dozvoljene putanje: /main.py, /config.py..., /lib/<ime>.py, /tactics/<ime>.py."""
    if not p.startswith("/") or ".." in p or "//" in p:
        return False
    parts = p[1:].split("/")
    if len(parts) == 1:
        return parts[0] in ALLOWED_ROOT
    ext = ".mpy" if parts[-1].endswith(".mpy") and parts[0] == "lib" else ".py"
    if len(parts) == 2 and parts[0] in ALLOWED_DIRS and parts[1].endswith(ext):
        n = parts[1][:-len(ext)]
        return n != "" and all(c.isalpha() or c.isdigit() or c in "_-" for c in n)
    return False


def _mkdirs(path):
    d = ""
    for part in path.split("/")[1:-1]:
        d += "/" + part
        try:
            os.mkdir(ROOT + d)
        except OSError:
            pass


def _is_dir(p):
    try:
        return os.stat(ROOT + p)[0] & 0x4000
    except OSError:
        return False


def _walk(p=""):
    out = []
    for n in sorted(os.listdir(ROOT + (p or "/"))):
        q = p + "/" + n
        if q == NEW or n == "__pycache__":
            continue
        if _is_dir(q):
            out += _walk(q)
        else:
            out.append(q)
    return out


def _stat_key(p):
    st = os.stat(ROOT + p)
    return st[6], st[8]


def remember(p, sha):
    """Upamti sha upravo upisanog fajla (LIST ga posle ne računa ponovo)."""
    try:
        _sha_cache[p] = _stat_key(p) + (sha,)
    except OSError:
        pass


def file_sha(p):
    h = _sha()
    buf = bytearray(512)
    with open(ROOT + p, "rb") as f:
        while True:
            n = f.readinto(buf)
            if not n:
                break
            h.update(memoryview(buf)[:n])
    return _hex(h.digest())


class Upload:
    def __init__(self, app, uart_args, cfg, error=None, port=PORT):
        self.app, self.uart_args, self.cfg = app, uart_args, cfg
        self.error = error              # rescue režim: redovi greške za LOG
        self.port = port
        self.s = None
        self._t_try = None
        self.c = None                   # trenutna veza
        self.f = None
        self.rbuf = bytearray(BUDGET)   # prijem podataka bez novih alokacija (malo RAM-a na WROOM-32)
        self.rmv = memoryview(self.rbuf)

    # ---------------- osluškivanje ----------------

    def _open(self):
        import state
        if not state.MODE:              # čeka WiFi
            return
        if self._t_try is not None and ticks_diff(ticks_ms(), self._t_try) < 1000:
            return
        self._t_try = ticks_ms()
        try:
            s = socket.socket()
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("0.0.0.0", self.port))
            s.listen(1)
            s.setblocking(False)
            self.s = s
            print("upload: port", self.port)
        except OSError as e:            # npr. port još drži stari socket (rescue): probaj ponovo
            print("upload:", e)

    def busy(self):
        return self.app is not None and self.app.busy()

    def poll(self):
        if self.s is None:
            self._open()
            if self.s is None:
                return
        if self.c is None:
            try:
                c, _ = self.s.accept()
            except OSError:
                return
            c.setblocking(False)
            self._start(c)
        self._step()

    # ---------------- jedna veza: automat stanja ----------------

    def _start(self, c):
        self.c = c
        self.buf = b""
        self.out = b""
        self.state = "AUTH"
        self.closing = False
        self.t = ticks_ms()
        self.nonce = _hex(os.urandom(8))
        self._say("EURO2 %s" % self.nonce)

    def _say(self, line):
        self.out += (line + "\n").encode()

    def _close(self):
        try:
            self.c.close()
        except Exception:
            pass
        if self.f:
            self.f.close()
            self.f = None
        self.c = None

    def _step(self):
        c = self.c
        if self.out:                    # prvo pošalji odgovor
            try:
                n = c.send(self.out[:BUDGET])
                if n:
                    self.out = self.out[n:]
                    self.t = ticks_ms()
            except OSError as e:
                if not _again(e):
                    return self._close()
        if self.closing:
            if not self.out or ticks_diff(ticks_ms(), self.t) > IDLE_MS:
                self._close()
            return
        if ticks_diff(ticks_ms(), self.t) > IDLE_MS:
            return self._close()
        if self.state == "LIST":
            return self._list_step()
        if self.state == "DATA":
            try:
                n = _recv_into(c, self.rmv[:min(BUDGET, self.left)])
            except OSError as e:
                if not _again(e):
                    self._close()
                return
            if n is None:
                return
            if n == 0:                  # klijent zatvorio vezu
                return self._close()
            self.t = ticks_ms()
            return self._data(self.rmv[:n])
        try:
            d = c.recv(BUDGET)
        except OSError as e:
            if not _again(e):
                self._close()
            return
        if not d:                       # klijent zatvorio vezu
            return self._close()
        self.t = ticks_ms()
        self.buf += d
        while self.state in ("AUTH", "CMD") and b"\n" in self.buf and not self.closing:
            line, self.buf = self.buf.split(b"\n", 1)
            self._line(line.decode().strip())
        if self.state == "DATA" and self.buf:
            d, self.buf = self.buf, b""
            self._data(d)
        elif len(self.buf) > 200:
            self._fail("predugacak red")

    def _fail(self, msg):
        self._say("ERR " + msg)
        self.closing = True

    def _ok(self, msg=""):
        self._say(("OK " + msg).strip())
        self.closing = True

    def _line(self, line):
        if self.state == "AUTH":
            pw = _password()
            h = _sha()
            h.update(((pw or "") + self.nonce).encode())
            if pw is None or line != _hex(h.digest()):
                return self._fail("pogresna lozinka")
            self.state = "CMD"
            return
        args = line.split()
        if not args:
            return self._fail("prazna komanda")
        cmd = args[0]
        if self.app is None and cmd not in RESCUE_OK:
            return self._fail("rescue: samo %s" % ", ".join(RESCUE_OK))
        if self.busy() and cmd not in BUSY_OK:
            return self._fail("taktika radi (dozvoljeno: LOG, STOP, STAT)")
        fn = getattr(self, "c_" + cmd.lower(), None)
        if cmd not in DATA_CMDS and fn is None:
            return self._fail("nepoznata komanda")
        try:
            if cmd in DATA_CMDS:
                self._begin_data(cmd, args)
            else:
                fn(args)
        except (OSError, ValueError, IndexError) as e:
            self._fail("%s: %s" % (cmd, e))

    # ---------------- komande sa podacima ----------------

    def _begin_data(self, cmd, args):
        if cmd == "FLASH":
            path, n, sha = "/stm.bin", int(args[1]), None
        else:
            path, n = args[1], int(args[2])
            sha = args[3] if len(args) > 3 else None
            if not check_path(path):
                return self._fail("nedozvoljena putanja: %s" % path)
            if cmd == "STAGE":
                if not sha:
                    return self._fail("STAGE trazi sha256")
                path = NEW + path
        self.cmd, self.path, self.left, self.size, self.want_sha = cmd, path, n, n, sha
        _mkdirs(path)
        self.tmp = path + ".tmp"
        self.f = open(ROOT + self.tmp, "wb")
        self.h = _sha()
        self.state = "DATA"
        if self.app and cmd == "FLASH":
            self.app.ui.toast("STM32: prijem", 60000)
        if n == 0:
            self._data(b"")

    def _data(self, d):
        if len(d) > self.left:
            self.buf, d = d[self.left:], d[:self.left]
        if d:
            self.f.write(d)
            self.h.update(d)
            self.left -= len(d)
        if self.left:
            return
        self.f.close()
        self.f = None
        got = _hex(self.h.digest())
        self.state = "CMD"
        if self.want_sha and got != self.want_sha:
            os.remove(ROOT + self.tmp)
            return self._fail("sha256 se ne poklapa")
        try:
            os.remove(ROOT + self.path)
        except OSError:
            pass
        os.rename(ROOT + self.tmp, ROOT + self.path)
        remember(self.path, got)
        if self.cmd == "FLASH":
            return self._flash()
        self._ok("%s %d B" % (self.path, self.size))

    def _flash(self):
        import stmflash
        a, ui, c = self.app, self.app.ui, self.c
        c.setblocking(True)             # flešovanje blokira ionako (STM32 je u bootloader-u)
        c.settimeout(2)

        def log(msg):
            print("[flash]", msg)
            try:
                c.send((msg + "\n").encode())
            except OSError:
                pass
            ui.toast(msg[:16], 60000)
            ui.draw()
        r = a.robot
        try:
            stmflash.flash_file(r.uart, ROOT + "/stm.bin", self.uart_args, r, self.cfg, log)
        except Exception as e:
            ui.toast("FLASH: greska", 5000, alert=True)
            c.setblocking(False)
            return self._fail("FLASH: %s" % e)
        r.parser.buf = bytearray()
        r.version = None
        ui.toast("STM32 flesovan", 3000)
        c.setblocking(False)
        self._ok("upisano %d B" % self.size)

    # ---------------- ostale komande ----------------

    def c_commit(self, args):
        staged = _walk(NEW) if _is_dir(NEW) else []
        staged = [p for p in staged if not p.endswith(".tmp")]
        for p in staged:
            dst = p[len(NEW):]
            _mkdirs(dst)
            try:
                os.remove(ROOT + dst)
            except OSError:
                pass
            os.rename(ROOT + p, ROOT + dst)
            c = _sha_cache.pop(p, None)
            if c:
                remember(dst, c[2])
        if len(args) > 1:
            with open(ROOT + "/version.txt", "w") as f:
                f.write(args[1])
        self._ok("%d fajlova" % len(staged))

    def c_del(self, args):
        if not check_path(args[1]):
            return self._fail("nedozvoljena putanja")
        os.remove(ROOT + args[1])
        self._ok(args[1])

    def c_list(self, args):
        self.gen = self._list_gen()
        self.state = "LIST"

    def _list_gen(self):
        """Po jedan spori korak (listdir, stat, sha) po next(); yield red za slanje ili None."""
        dirs, files = [""], []
        while dirs:
            d = dirs.pop(0)
            for n in sorted(os.listdir(ROOT + (d or "/"))):
                q = d + "/" + n
                if q != NEW and n != "__pycache__":
                    files.append(q)
            yield None
        for p in files:
            if _is_dir(p):
                for n in sorted(os.listdir(ROOT + p)):
                    if n != "__pycache__":
                        files.append(p + "/" + n)
                yield None
                continue
            key = _stat_key(p)
            yield None
            c = _sha_cache.get(p)
            if not c or c[:2] != key:
                c = key + (file_sha(p),)
                _sha_cache[p] = c
                yield None
            yield "%s %d %s" % (p, key[0], c[2])

    def _list_step(self):
        t0 = ticks_ms()
        try:
            while ticks_diff(ticks_ms(), t0) < LIST_MS:
                line = next(self.gen)
                if line:
                    self._say(line)
        except StopIteration:
            self.state = "CMD"
            self._ok()
        except OSError as e:
            self.state = "CMD"
            self._fail("LIST: %s" % e)
        self.t = ticks_ms()

    def c_reset(self, args):
        self._ok("restart")
        c = self.c
        c.setblocking(True)
        try:
            c.send(self.out)
        except OSError:
            pass
        self._close()
        import machine
        machine.reset()

    def c_run(self, args):                  # RUN <ime> [strana]: odmah, kao test (bez činča)
        import tac
        side = args[2] if len(args) > 2 else None
        if args[1] not in self.app.tactics():
            return self._fail("nema /tactics/%s.py" % args[1])
        if side and side not in tac.SIDES:
            return self._fail("strana: %s" % ", ".join(tac.SIDES))
        self.app.start_tactic(args[1], side)
        self._ok()

    def c_stop(self, args):
        self.app.stop("WiFi")
        self._ok()

    def c_log(self, args):
        if self.app is None:
            for l in self.error or []:
                self._say(l)
            return self._ok("0 0")
        a = self.app
        first = a.log_n - len(a.log)             # redni broj najstarijeg sačuvanog reda
        for i, line in enumerate(a.log):
            if first + i >= int(args[1]):
                self._say(line)
        self._ok("%d %d" % (a.log_n, 1 if (a.running or a.request) else 0))

    def c_stat(self, args):
        a, r = self.app, self.app.robot
        if a.loop:
            for k, v in sorted(a.loop.max.items()):
                self._say("%s %d ms" % (k, v))
        self._say("krug %d ms, PING max %d ms, okvira/s %d, CRC %d, ponovljeno %d, bez odg %d" % (
            a.loop.step_max if a.loop else 0, r.ping_gap, r.fps, r.parser.errors, r.retries, r.noreply))
        self._say("verzija %s" % version())
        self._say(mem())
        self._ok()


def mem():
    """Memorija: MicroPython heap (slobodno/zauzeto) i slobodna memorija drajvera (WiFi, UART)."""
    import gc
    out = "heap slob %dk zauz %dk" % (gc.mem_free() // 1024, gc.mem_alloc() // 1024)
    try:
        import esp32
        h = esp32.idf_heap_info(esp32.HEAP_DATA)
        out += ", IDF slob %dk (najveci %dk)" % (sum(x[1] for x in h) // 1024, max(x[2] for x in h) // 1024)
    except Exception:
        pass
    return out


def version():
    try:
        with open(ROOT + "/version.txt") as f:
            return f.read().strip()
    except OSError:
        return "?"


def _recv_into(c, mv):
    """Prijem u postojeći bafer: MicroPython ima readinto (None = nema podataka), CPython recv_into."""
    if hasattr(c, "recv_into"):
        return c.recv_into(mv)
    return c.readinto(mv)


def _again(e):
    """Neblokirajući socket: nema podataka ili se još šalje (EAGAIN / EINPROGRESS)."""
    return getattr(e, "errno", None) in (11, 35, 115, 119) or e.args[:1] in ((11,), (115,), (119,))
