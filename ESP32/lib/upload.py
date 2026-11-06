# Upload preko WiFi-ja (port 8267), za tools/esp_push.py i tools/flash_stm32.py.
#
# Klijent šalje:  lozinka\n  KOMANDA args\n  [bajtovi]
#   PUT <putanja> <dužina>   upiši fajl na ESP (preko privremenog fajla, pa preimenuj)
#   FLASH <dužina>           primi STM32 .bin u /stm.bin i flešuj ga (stmflash.py)
#   RESET                    restartuj ESP
# Odgovor: redovi napretka, na kraju "OK ..." ili "ERR ...". Lozinka je ista kao za WebREPL.
import socket
import os

PORT = 8267


def _password():
    try:
        import webrepl_cfg
        return webrepl_cfg.PASS
    except Exception:
        return None


class Upload:
    def __init__(self, app, uart_args, cfg):
        self.app, self.uart_args, self.cfg = app, uart_args, cfg
        self.s = None

    def poll(self):
        if self.s is None:
            import state
            if not state.MODE:              # čeka WiFi
                return
            self.s = socket.socket()
            self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.s.bind(("0.0.0.0", PORT))
            self.s.listen(1)
            self.s.setblocking(False)
            print("upload: port", PORT)
        try:
            c, addr = self.s.accept()
        except OSError:
            return
        c.setblocking(True)
        c.settimeout(10)
        try:
            self._serve(c)
        except Exception as e:
            try:
                c.write(("ERR %s\n" % e).encode())
            except Exception:
                pass
        finally:
            c.close()

    def _line(self, c):
        b = b""
        while not b.endswith(b"\n"):
            ch = c.read(1)
            if not ch:
                raise OSError("veza prekinuta")
            b += ch
            if len(b) > 200:
                raise OSError("predugačak red")
        return b.decode().strip()

    def _recv_file(self, c, path, n):
        tmp = path + ".tmp"
        buf = bytearray(1024)
        left = n
        with open(tmp, "wb") as f:
            while left:
                k = c.readinto(memoryview(buf)[:min(left, len(buf))])
                if not k:
                    raise OSError("prekinuto posle %d/%d" % (n - left, n))
                f.write(memoryview(buf)[:k])
                left -= k
        try:
            os.remove(path)
        except OSError:
            pass
        os.rename(tmp, path)

    def _serve(self, c):
        pw = _password()
        if pw is None or self._line(c) != pw:
            c.write(b"ERR pogresna lozinka\n")
            return
        args = self._line(c).split()
        ui = self.app.ui
        if args[0] == "PUT":
            path, n = args[1], int(args[2])
            self._recv_file(c, path, n)
            c.write(("OK %s %d B\n" % (path, n)).encode())
        elif args[0] == "FLASH":
            n = int(args[1])
            ui.toast("STM32: prijem", 60000)
            ui.draw()
            self._recv_file(c, "/stm.bin", n)
            import stmflash

            def log(msg):
                print("[flash]", msg)
                c.write((msg + "\n").encode())
                ui.toast(msg[:16], 60000)
                ui.draw()
            r = self.app.robot
            try:
                stmflash.flash_file(r.uart, "/stm.bin", self.uart_args, r, self.cfg, log)
            except Exception as e:
                ui.toast("FLASH: greska", 5000, alert=True)
                raise
            r.parser.buf = bytearray()
            r.version = None
            ui.toast("STM32 flesovan", 3000)
            c.write(("OK upisano %d B\n" % n).encode())
        elif args[0] == "RESET":
            c.write(b"OK restart\n")
            c.close()
            import machine
            machine.reset()
        else:
            c.write(b"ERR nepoznata komanda\n")
