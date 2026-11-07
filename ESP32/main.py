# Ekran sa telemetrijom (enkoder + tasteri), veza sa STM32, WiFi + WebREPL i upload u pozadini,
# i pokretanje taktika iz /tactics (sa ekrana ili preko WiFi-ja: tools/tactic.py).
# Ctrl+C u bilo kom trenutku prekida program (mpremote i Thonny to rade automatski).
# Ako program padne, rescue.py ispiše grešku na ekranu i ostavi WiFi + upload (popravka bez kabla).


def main():
    from machine import UART
    import config as cfg
    from compat import sleep_ms
    from screen import oled
    from net import Net
    from robot import Robot
    from settings import Settings
    from inputs import Inputs
    from app import App
    from upload import Upload
    from runner import Loop, run_tactic
    import tac

    st = Settings()
    uart_args = dict(baudrate=cfg.UART_BAUD, tx=cfg.UART_TX, rx=cfg.UART_RX, rxbuf=1024)
    uart = UART(cfg.UART_ID, timeout=0, **uart_args)
    app = App(Robot(uart), st, oled)           # odmah primenjuje kontrast i okretanje ekrana
    inp = Inputs(cfg, lambda: st["enc_rev"])
    net = Net()                                # ne blokira: ikonica WiFi trepće dok se povezuje
    gui = app.ui
    upload = Upload(app, uart_args, cfg)      # port 8267: esp_push, flash_stm32, tactic

    def handle_inputs():
        for ev in inp.poll(gui.top.wants_hold):
            if ev[0] == "stop":
                app.stop()                     # i prekida taktiku
            else:
                gui.input(*ev)
        gui.hold(inp.hold_ms)

    loop = Loop([("net", net.poll), ("upload", upload.poll), ("robot", app.update),
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
    import rescue
    rescue.run(e)
