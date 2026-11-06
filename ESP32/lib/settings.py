# Podešavanja koja se pamte posle restarta (settings.json u korenu fleša).
import json

FILE = "settings.json"
DEFAULTS = {
    "contrast": 200,      # 0..255
    "flip": False,        # ekran okrenut za 180°
    "enc_rev": False,     # obrnut smer enkodera
    "sleep_s": 0,         # gašenje ekrana posle N s bez dodira (0 = nikad)
    "start_pose": True,   # posle povezivanja pošalji SET_POSE iz config.START_POSE
    "demo": False,        # lažna taktika na ekranu (samo prikaz, ništa se ne šalje robotu)
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
