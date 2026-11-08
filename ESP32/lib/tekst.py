# Svi natpisi na ekranu na jednom mestu: dosledni, bez dijakritika (font ih nema), do 16 znakova.
import protocol as P

# razlozi FAIL-a sa STM32 i iz ESP-a
REASON = {"INVALID": "odbijeno", "BLOCKED": "prepreka", "TIMEOUT": "isteklo", "PREEMPTED": "prekinuto",
          "MATCH_OVER": "kraj meca", "STOPPED": "stop", "NOREPLY": "nema odgovora",
          "SUPERSEDED": "zamenjeno", "STOP": "STOP", "LINK": "veza", "VEZA": "veza"}

# kratka imena komandi u porukama
SHORT = {"SET_POSE": "POZA", "ROTATE": "OKRET", "MOVE": "PRAVO", "MATCH_START": "START",
         "ACTUATOR": "AKT"}

# bitovi STATUS.state -> etiketa
TAGS = ((P.State.MOVING, "VOZI"), (P.State.BLOCKED, "BLOK"), (P.State.MATCH_RUNNING, "MEC"),
        (P.State.MATCH_OVER, "KRAJ"))

SIDE = {"plava": "P", "zuta": "Z"}       # strana uz ime taktike u naslovu: "x100 P"


def reason(r):
    return REASON.get(r, str(r))


def version_msg(have, want):
    """Šta korisnik treba da uradi kad se verzije protokola ne slažu (want = najnovija koju ESP zna)."""
    if not have:
        return "STM32 nema verz."
    if have > want:
        return "ESP star: STM v%s" % have       # STM32 je noviji: ažurirati ESP (esp_push)
    return "STM32 v%s, flesuj" % have


def secs(ms):
    return "%.1fs" % (ms / 1000) if ms < 100000 else "%ds" % (ms // 1000)
