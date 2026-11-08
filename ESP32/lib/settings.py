# Podešavanja koja se pamte posle restarta (settings.json u korenu fleša).
import json

FILE = "settings.json"
DEFAULTS = {
    "contrast": 200,      # 0..255
    "flip": False,        # ekran okrenut za 180°
    "enc_rev": False,     # obrnut smer enkodera
    "sleep_s": 0,         # gašenje ekrana posle N s bez dodira (0 = nikad)
    "start_pose": True,   # posle povezivanja pošalji SET_POSE iz config.START_POSE
    "demo": False,
    "wdt_match": True,    # machine.WDT od NAORUZAN do restarta (ESP se sam restartuje ako se zaglavi)
    "wifi_off_match": False,  # ugasi WiFi kad meč krene (u pravom meču)
    "sel_tactic": None,   # izabrana taktika i strana (pamte se posle restarta i zamene baterije)
    "sel_side": None,
    "test_start": True,   # test (bez meča) kreće od START poze taktike, kao meč
    "screen_match": "miran",  # ekran u meču: miran (krupno, retko crta), ugasen, detaljan        # lažna taktika na ekranu (samo prikaz, ništa se ne šalje robotu)
}


class Settings(dict):
    def __init__(self, path=FILE):
        super().__init__(DEFAULTS)
        self.path = path
        try:
            with open(path) as f:
                self.update(json.load(f))
        except (OSError, ValueError):
            pass

    def set(self, key, value):
        if self.get(key) != value:
            self[key] = value
            try:
                with open(self.path, "w") as f:
                    json.dump(dict(self), f)
            except OSError as e:
                print("settings:", e)
