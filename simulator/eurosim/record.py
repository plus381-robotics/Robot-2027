# Snimak simulacije: meta podaci, frame-ovi (stanje na svakih FRAME_MS) i događaji (poruke, dnevnik,
# koraci taktike). Iz snimka se kasnije crta, premotava, poredi; čuva se kao .json.gz.
import gzip
import json

FRAME_MS = 20
VERSION = 1


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

    @classmethod
    def load(cls, path):
        with gzip.open(path, "rt", encoding="utf-8") as f:
            d = json.load(f)
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
