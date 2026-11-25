# NRST pin STM32-a sa ESP-a (config.STM_NRST). Dva načina povezivanja:
#  - direktno na NRST (WROOM test, BlackPill): open-drain, 0 = reset, pušten = 1 (pull-up na STM32)
#  - preko N-MOSFET-a (ESP32_Main, Q1): config.STM_NRST_INV = True, push-pull, 1 = reset
#    (u mirovanju 0; i dok ESP startuje, pin je ulaz i pull-down na gejtu drži STM32 da radi)


class Nrst:
    def __init__(self, cfg):
        from machine import Pin
        self.inv = bool(getattr(cfg, "STM_NRST_INV", False))
        if self.inv:
            self.pin = Pin(cfg.STM_NRST, Pin.OUT, value=0)
        else:
            self.pin = Pin(cfg.STM_NRST, Pin.OPEN_DRAIN, value=1)

    def hold(self, on=True):
        """on = True: STM32 u resetu; False: pušten (radi)."""
        self.pin.value((1 if on else 0) if self.inv else (0 if on else 1))
