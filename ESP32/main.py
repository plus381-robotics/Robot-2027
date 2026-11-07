# Ekran sa telemetrijom (enkoder + tasteri), veza sa STM32, WiFi + WebREPL i upload u pozadini,
# i pokretanje taktika iz /tactics (sa ekrana ili preko WiFi-ja: tools/tactic.py).
# Ctrl+C u bilo kom trenutku prekida program (mpremote i Thonny to rade automatski).
# Ako program padne, rescue.py ispiše grešku na ekranu i ostavi WiFi + upload (popravka bez kabla).


def main():
    # Drajveri prvi (WiFi, UART): traže memoriju van MicroPython heap-a, a heap se tokom uvoza
    # koda širi i uzme je ("WiFi Out of Memory", "UART driver malloc error").
    import gc
    gc.collect()
    from machine import UART
    import config as cfg
    from net import Net
    holder = []
    net = Net(lambda: bool(holder) and holder[0].busy())
    net.poll()
    uart_args = dict(baudrate=cfg.UART_BAUD, tx=cfg.UART_TX, rx=cfg.UART_RX, rxbuf=1024)
    uart = UART(cfg.UART_ID, timeout=0, **uart_args)
    from compat import sleep_ms
    from screen import oled
    from robot import Robot
    from settings import Settings
    from inputs import Inputs
    from app import App
    from upload import Upload
    from telem import Telem
    from runner import Loop, run_tactic
    import tac

    st = Settings()
    app = App(Robot(uart), st, oled)           # odmah primenjuje kontrast i okretanje ekrana
    inp = Inputs(cfg, lambda: st["enc_rev"])
    holder.append(app)                         # Net pita app.busy() pre ponovnog povezivanja
    # Memorija: heap ne sme da raste na račun WiFi drajvera (WROOM-32 nema PSRAM). Čisti se
    # pre nego što se napuni, pa ne mora da se širi.
    gc.collect()
    gc.threshold(max(4096, gc.mem_free() // 4))
    gui = app.ui
    upload = Upload(app, uart_args, cfg)      # port 8267: esp_push, flash_stm32, tactic

    def handle_inputs():
        for ev in inp.poll(gui.top.wants_hold):
            if ev[0] == "stop":
                app.stop()                     # i prekida taktiku
            else:
                gui.input(*ev)
        gui.hold(inp.hold_ms)

    telem = Telem(app)                         # UDP 8268: tools/watch.py
    loop = Loop([("net", net.poll), ("upload", upload.poll), ("telem", telem.poll), ("robot", app.update),
                 ("ulaz", handle_inputs), ("ekran", gui.tick)], sleep_ms)
    app.pump = loop.step                       # taktika ga zove dok čeka (tac.py)
    app.loop = loop
    tac.app = app
    while True:
        loop.step()
        if app.request:
            name, app.request = app.request, None
            run_tactic(app, name)


try:
    main()
except KeyboardInterrupt:
    raise                                      # Ctrl+C iz mpremote/Thonny-ja vraća REPL
except BaseException as e:
    try:
        import rescue
    except BaseException as e2:                # ni rescue ne može da se uveze (pokvaren lib/)
        import sys
        sys.print_exception(e)
        sys.print_exception(e2)
        raise
    rescue.run(e)
