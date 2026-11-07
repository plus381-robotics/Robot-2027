# Rescue režim: main.py je pao (ili se lib/ ne može uvesti). Na ekranu je greška, a WiFi i upload
# (samo PUT, RESET, LOG) rade dalje, pa se kod popravlja bez kabla: tools/esp_push.py.
# STM32 sam staje posle 500 ms bez PING-a. Ne uvozi ništa od aplikacije (app, ui, robot).
import sys


def run(e):
    try:
        with open("/err.log", "a") as f:
            f.write("---\n")
            sys.print_exception(e, f)
    except Exception:
        pass
    sys.print_exception(e)
    lines = ["GRESKA", str(type(e).__name__)] + _split(str(e), 16, 3) + ["esp_push za fix"]
    try:
        from screen import oled
        if oled:
            oled.fill(0)
            oled.fill_rect(0, 0, 128, 10, 1)
            for i, l in enumerate(lines[:6]):
                oled.text(l[:16], 0, 1 if i == 0 else 4 + 10 * i, 0 if i == 0 else 1)
            oled.show()
    except Exception:
        pass
    from compat import sleep_ms
    try:
        from net import Net
        net = Net()
    except Exception:
        net = None
    try:
        from upload import Upload
        up = Upload(None, None, None, error=lines)
    except Exception:
        up = None
    while True:
        try:
            if net:
                net.poll()
            if up:
                up.poll()
        except Exception as x:
            sys.print_exception(x)
        sleep_ms(20)


def _split(s, n, k):
    return [s[i:i + n] for i in range(0, min(len(s), n * k), n)] or [""]
