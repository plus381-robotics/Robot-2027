# RTTTL (ringtone tekst) -> note. Bez zavisnosti: koristi ga lib/buzzer.py na ESP-u, a simulator (editor
# taktika) isti fajl za proveru play("...").
#
# "ime:d=4,o=6,b=63:nota,nota,..."; d = podrazumevano trajanje, o = oktava, b = četvrtina nota u minuti.
# nota = [trajanje]slovo[#][.][oktava], npr. 8c#7, 4e., p = pauza. Trajanje 1/2/4/8/16/32 (deo cele note),
# tačka = 1,5 puta duže. Ime i podešavanja mogu da se izostave ("c,e,g": d=4, o=6, b=63).

_SEMI = {"c": 0, "d": 2, "e": 4, "f": 5, "g": 7, "a": 9, "b": 11, "h": 11}
_DURS = (1, 2, 4, 8, 16, 32)


def note_hz(semi, octave):
    """Frekvencija note (semi 0..11 od C) u oktavi; A4 = 440 Hz."""
    return round(440 * 2 ** ((12 * (octave + 1) + semi - 69) / 12))


def header(text):
    """Podešavanja i početak nota: (d, o, cela nota u ms, indeks prve note). ValueError ako ne valja."""
    c2 = text.rfind(":")
    if text.count(":") > 2:
        raise ValueError("RTTTL: previse ':'")
    d, o, b = 4, 6, 63
    if c2 >= 0:
        c1 = text.find(":")
        ctl = text[c1 + 1:c2] if c1 != c2 else text[:c2]
        for item in ctl.split(","):
            item = item.strip().lower()
            if not item:
                continue
            k, _, v = item.partition("=")
            try:
                v = int(v)
            except ValueError:
                raise ValueError("RTTTL: los broj u '%s'" % item)
            if k == "d":
                d = v
            elif k == "o":
                o = v
            elif k == "b":
                b = v
            else:
                raise ValueError("RTTTL: nepoznato '%s'" % item)
    if d not in _DURS or not 3 <= o <= 8 or not 10 <= b <= 900:
        raise ValueError("RTTTL: d=%d o=%d b=%d van opsega" % (d, o, b))
    return d, o, 240000 // b, c2 + 1


def note(tok, d, o, whole):
    """Jedna nota ("8c#7.") -> (Hz, ms); Hz 0 = pauza."""
    tok = tok.strip().lower()
    i = 0
    while i < len(tok) and tok[i].isdigit():
        i += 1
    dur = int(tok[:i]) if i else d
    if i >= len(tok) or (tok[i] not in _SEMI and tok[i] != "p"):
        raise ValueError("RTTTL: losa nota '%s'" % tok)
    letter = tok[i]
    semi = _SEMI.get(letter, 0)
    octave, dot = o, False
    for ch in tok[i + 1:]:
        if ch == "#" or ch == "_":
            semi += 1
        elif ch == ".":
            dot = True
        elif ch.isdigit():
            octave = int(ch)
        else:
            raise ValueError("RTTTL: losa nota '%s'" % tok)
    if dur not in _DURS or not 3 <= octave <= 8:
        raise ValueError("RTTTL: losa nota '%s'" % tok)
    ms = whole // dur
    if dot:
        ms = ms * 3 // 2
    return (0 if letter == "p" else note_hz(semi, octave)), ms


def stream(text):
    """Note jednu po jednu (generator), bez liste: za duge melodije na ESP-u (brz početak, malo RAM-a).
    Podešavanja se proveravaju odmah (pre prve note), loša nota baca ValueError kad na nju dođe red."""
    d, o, whole, i = header(text)

    def gen(i):
        n = len(text)
        while i < n:
            j = text.find(",", i)
            if j < 0:
                j = n
            if text[i:j].strip():
                yield note(text[i:j], d, o, whole)
            i = j + 1
    return gen(i)


def parse(text):
    """RTTTL -> [(Hz, ms), ...] (Hz 0 = pauza). Ime i podešavanja mogu da se izostave ("c,e,g").
    Loš tekst: ValueError sa opisom."""
    out = list(stream(text))
    if not out:
        raise ValueError("RTTTL: nema nota")
    return out


def check(sound, names):
    """Ime zvuka iz names ili ispravan RTTTL tekst; inače ValueError (tac.play i editor taktika)."""
    if sound in names:
        return
    if ":" not in sound and "," not in sound:
        raise ValueError("nema zvuka '%s' (config.SOUNDS), a nije ni RTTTL" % sound)
    parse(sound)
