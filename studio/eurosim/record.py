# Snimak simulacije: meta podaci, frame-ovi (stanje na svakih FRAME_MS) i događaji (poruke, dnevnik,
# koraci taktike). Iz snimka se kasnije crta, premotava, poredi; čuva se kao .json.gz.
import gzip
import json

FRAME_MS = 20
VERSION = 2


def upgrade(d):
    """Snimak v1 -> v2: meta.origin (ko je izvor podataka). meta.source (tekst taktike) se ne dira."""
    if d.get("version", 1) >= 2 and "origin" in d.get("meta", {}):
        return d
    meta = d.setdefault("meta", {})
    if "origin" not in meta:
        robot = bool((d.get("result") or {}).get("robot"))
        meta["origin"] = {"engine": "robot" if robot else "sim", "parts": {}}
        meta.setdefault("tactic_sha", None)
        meta.setdefault("scenario", None)
    d["version"] = VERSION
    return d


_WS = " \t\r\n"


def _head(dec, s, eof):
    """Ključevi najvišeg nivoa sa početka JSON objekta, do prvog "frames"/"events" (ili kraja).
    None = treba još teksta. Vrednost se prihvata tek kad posle nje stigne i sledeći znak (broj na kraju bafera
    može biti nepotpun)."""
    out, i, n = {}, 0, len(s)

    def skip(i):
        while i < n and s[i] in _WS:
            i += 1
        return i

    i = skip(i)
    if i >= n:
        return None
    if s[i] != "{":
        raise ValueError("snimak nije JSON objekat")
    i += 1
    while True:
        i = skip(i)
        if i >= n:
            return None
        if s[i] == "}":
            return out
        if s[i] == ",":
            i = skip(i + 1)
        try:
            key, i = dec.raw_decode(s, i)
        except json.JSONDecodeError:
            if eof:
                raise
            return None
        if key in ("frames", "events"):
            return out
        i = skip(i)
        if i >= n:
            return None
        if s[i] != ":":
            raise ValueError("snimak: očekivano ':'")
        i = skip(i + 1)
        try:
            val, j = dec.raw_decode(s, i)
        except json.JSONDecodeError:
            if eof:
                raise
            return None
        if skip(j) >= n and not eof:
            return None
        out[key] = val
        i = j


def _round(v):
    if isinstance(v, float):
        return round(v, 4)
    return v


class Recording:
    def __init__(self, meta=None):
        self.meta = meta or {}
        self.frames = []          # dict-ovi; t = ms od početka simulacije
        self.events = []          # [t, vrsta, podaci]
        self.result = {}

    def frame(self, d):
        self.frames.append({k: _round(v) for k, v in d.items()})

    def event(self, t, kind, data):
        self.events.append([t, kind, data])

    def to_dict(self):
        return {"version": VERSION, "meta": self.meta, "result": self.result,
                "frames": self.frames, "events": self.events}

    def save(self, path):
        with gzip.open(path, "wt", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, separators=(",", ":"))

    @staticmethod
    def peek(path, chunk=1 << 16):
        """Samo version, meta i result (posle upgrade, pa i v1), bez frame-ova i događaja: to_dict ih piše prve, pa
        se čita (raspakuje) samo početak fajla. Ako fajl nije u tom redu, čita se ceo."""
        dec = json.JSONDecoder()
        with gzip.open(path, "rt", encoding="utf-8") as f:
            buf = ""
            while True:
                more = f.read(chunk)
                buf += more
                head = _head(dec, buf, eof=not more)
                if head is not None:
                    break
                if not more:
                    raise ValueError("nepotpun snimak")
            if "meta" not in head:                      # neobičan redosled ključeva: ceo fajl
                f.seek(0)
                d = json.load(f)
                head = {k: d[k] for k in ("version", "meta", "result") if k in d}
        head.setdefault("result", {})
        return upgrade(head)

    @classmethod
    def load(cls, path):
        with gzip.open(path, "rt", encoding="utf-8") as f:
            d = upgrade(json.load(f))
        r = cls(d["meta"])
        r.frames, r.events, r.result = d["frames"], d["events"], d.get("result", {})
        return r

    # ---------------- pomoć za prikaz i testove ----------------

    def of(self, kind):
        return [e for e in self.events if e[1] == kind]

    def steps(self):
        """Završeni koraci: [(idx, ime, ok, razlog, trajanje_ms)]."""
        return [tuple(e[2]) for e in self.of("step_end")]

    def logs(self):
        return [e[2] for e in self.of("log")]
