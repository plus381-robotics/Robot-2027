# Taktike za editor: pomoć za API (iz ESP32/lib/tac.py), provera pre slanja, čitanje i čuvanje.
#
# Pomoć se pravi iz samog tac.py (potpisi i docstring-ovi), pa je uvek u skladu sa kodom na robotu.
# Provera (bez pokretanja): sintaksa (CPython), MicroPython (mpy-cross, ista verzija kao na ESP-u),
# nepoznata imena, pogrešni argumenti tac funkcija, nepoznat aktuator, koordinate van stola, START,
# beskonačna petlja bez čekanja. Provera pokretanjem (simulacija) se dodaje u server.py.
import ast
import builtins
import hashlib
import os
import re
import subprocess
import tempfile

from . import field, paths

NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,40}$")
TEMPLATE = '''# Nova taktika. Piše se za žutu stranu (tac.REF_SIDE); na drugoj se koordinate same ogledaju.
from tac import *

START = (250, 1000, 0)          # startna poza (x, y, ugao); u meču je ESP postavi kad se izvuče činč
TOTAL = 2                       # broj koraka (za ekran "1/2")

if not remaining():             # test bez meča: postavi pozu ručno
    pose(*START)
goto(600, 1000, speed=300, next="okret")
turn_to(90)
'''


# ---------------- API iz tac.py ----------------

def _default(node):
    try:
        return ast.unparse(node)
    except Exception:
        return "..."


def tac_api():
    """{"funcs": {ime: {sig, params, doc}}, "doc": zaglavlje tac.py, "actuators": [...], "ref_side": ...}"""
    src = (paths.ESP / "lib" / "tac.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    exported, funcs, aliases, consts = [], {}, {}, {}
    for n in tree.body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
            t = n.targets[0].id
            if t == "__all__":
                exported = list(ast.literal_eval(n.value))
            elif isinstance(n.value, ast.Name):
                aliases[t] = n.value.id
            elif isinstance(n.value, ast.Constant):
                consts[t] = n.value.value
        elif isinstance(n, (ast.FunctionDef, ast.ClassDef)):
            funcs[n.name] = n
    out = {}
    for name in exported:
        node = funcs.get(aliases.get(name, name))
        if isinstance(node, ast.FunctionDef):
            a = node.args
            pos = a.posonlyargs + a.args
            defs = [None] * (len(pos) - len(a.defaults)) + list(a.defaults)
            params = [[p.arg, None if d is None else _default(d)] for p, d in zip(pos, defs)]
            sig = "%s(%s)" % (name, ", ".join(p if d is None else "%s=%s" % (p, d) for p, d in params))
            doc = ast.get_docstring(node) or ""
            if name in aliases:
                doc = ("staro ime za %s. " % aliases[name]) + doc
            out[name] = {"sig": sig, "params": params, "doc": doc, "kind": "function",
                         "varargs": bool(a.vararg or a.kwarg)}
        elif isinstance(node, ast.ClassDef):
            out[name] = {"sig": name, "params": [], "doc": ast.get_docstring(node) or "", "kind": "class",
                         "varargs": True}
    header = []
    for line in src.splitlines():
        if not line.startswith("#"):
            break
        header.append(line[1:].strip() if line.startswith("# ") or line == "#" else line[1:])
    from . import apidoc
    for name, f in out.items():
        f["help"] = apidoc.DOC.get(name)
    return {"funcs": out, "doc": "\n".join(header), "actuators": _actuators(), "name": apidoc.NAME,
            "coords": apidoc.COORDS,
            "ref_side": consts.get("REF_SIDE", "zuta"), "field_x": consts.get("FIELD_X", 3000)}


def _actuators():
    try:
        tree = ast.parse((paths.ESP / "config.py").read_text(encoding="utf-8"))
        for n in tree.body:
            if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", None) == "ACTUATORS":
                return sorted(ast.literal_eval(n.value))
    except Exception:
        pass
    return []


# ---------------- provera ----------------

def _diag(node_or_line, msg, sev="error", src="check", col=None):
    if isinstance(node_or_line, int):
        line, c, el, ec = node_or_line, col or 0, None, None
    else:
        n = node_or_line
        line, c = n.lineno, n.col_offset
        el, ec = getattr(n, "end_lineno", None), getattr(n, "end_col_offset", None)
    return {"line": line, "col": c, "end_line": el, "end_col": ec, "severity": sev, "msg": msg, "source": src}


def mpy_check(source):
    """MicroPython kompajler (mpy-cross, kao za lib/ na ESP-u). None = mpy-cross nije instaliran."""
    try:
        import mpy_cross
        exe = [mpy_cross.mpy_cross]
        mpy_cross.fix_perms()
    except ImportError:
        exe = ["mpy-cross"]
    with tempfile.TemporaryDirectory() as d:
        f = os.path.join(d, "taktika.py")
        with open(f, "w", encoding="utf-8") as fh:
            fh.write(source)
        try:
            p = subprocess.run(exe + ["-o", os.path.join(d, "t.mpy"), f], capture_output=True, text=True, timeout=20)
        except (OSError, subprocess.TimeoutExpired):
            return None
    if p.returncode == 0:
        return []
    err = (p.stderr or p.stdout).strip()
    m = re.search(r"line (\d+)", err)
    msg = err.splitlines()[-1] if err else "mpy-cross: greška"
    return [_diag(int(m.group(1)) if m else 1, "MicroPython: " + msg, "error", "mpy")]


class _Names(ast.NodeVisitor):
    def __init__(self):
        self.defined, self.used, self.star = set(), [], []

    def visit_Name(self, n):
        (self.defined.add(n.id) if isinstance(n.ctx, (ast.Store, ast.Del)) else self.used.append(n))

    def visit_arg(self, n):
        self.defined.add(n.arg)

    def visit_FunctionDef(self, n):
        self.defined.add(n.name)
        self.generic_visit(n)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, n):
        self.defined.add(n.name)
        self.generic_visit(n)

    def visit_Import(self, n):
        for a in n.names:
            self.defined.add((a.asname or a.name).split(".")[0])

    def visit_ImportFrom(self, n):
        for a in n.names:
            if a.name == "*":
                self.star.append(n.module)
            else:
                self.defined.add(a.asname or a.name)

    def visit_ExceptHandler(self, n):
        if n.name:
            self.defined.add(n.name)
        self.generic_visit(n)

    def visit_Global(self, n):
        self.defined.update(n.names)

    visit_Nonlocal = visit_Global


def _num(n):
    if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) and not isinstance(n.value, bool):
        return n.value
    if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.USub):
        v = _num(n.operand)
        return -v if v is not None else None
    return None


def static_check(source, api=None):
    """Lista dijagnostika (line od 1)."""
    api = api or tac_api()
    funcs = api["funcs"]
    out = []
    try:
        tree = ast.parse(source)
        compile(source, "taktika", "exec")
    except SyntaxError as e:
        return [_diag(e.lineno or 1, "sintaksa: %s" % e.msg, "error", "syntax", col=max(0, (e.offset or 1) - 1))]
    mp = mpy_check(source)
    if mp is None:
        out.append(_diag(1, "mpy-cross nije instaliran: MicroPython provera preskočena "
                            "(pip install -r simulator/requirements.txt)", "info", "mpy"))
    else:
        out += mp
    nv = _Names()
    nv.visit(tree)
    uses_tac = "tac" in nv.star or any(isinstance(n, ast.ImportFrom) and n.module == "tac" for n in ast.walk(tree))
    known = nv.defined | set(dir(builtins)) | {"__name__", "__file__"}
    if "tac" in nv.star:
        known |= set(funcs)
    other_star = [m for m in nv.star if m != "tac"]
    if not other_star:
        seen = set()
        for n in nv.used:
            if n.id not in known and n.id not in seen:
                seen.add(n.id)
                hint = " (fali `from tac import *`?)" if n.id in funcs and not uses_tac else ""
                out.append(_diag(n, "nepoznato ime `%s`%s" % (n.id, hint), "error", "names"))
    # pozivi tac funkcija
    for n in ast.walk(tree):
        if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in funcs):
            continue
        if n.func.id in nv.defined:
            continue                                   # taktika je sama definisala to ime
        f = funcs[n.func.id]
        if f["kind"] != "function" or f["varargs"]:
            continue
        names = [p for p, _ in f["params"]]
        if any(isinstance(a, ast.Starred) for a in n.args) or any(k.arg is None for k in n.keywords):
            continue
        if len(n.args) > len(names):
            out.append(_diag(n, "%s: previše argumenata (%d, najviše %d): %s" % (n.func.id, len(n.args), len(names),
                                                                                f["sig"]), "error", "api"))
            continue
        given = set(names[:len(n.args)])
        for k in n.keywords:
            if k.arg not in names:
                out.append(_diag(k.value, "%s nema argument `%s`: %s" % (n.func.id, k.arg, f["sig"]), "error", "api"))
            elif k.arg in given:
                out.append(_diag(k.value, "%s: `%s` je zadat dvaput" % (n.func.id, k.arg), "error", "api"))
            given.add(k.arg)
        missing = [p for p, d in f["params"] if d is None and p not in given]
        if missing:
            out.append(_diag(n, "%s: fali %s: %s" % (n.func.id, ", ".join("`%s`" % m for m in missing), f["sig"]),
                             "error", "api"))
        args = dict(zip(names, n.args))
        args.update({k.arg: k.value for k in n.keywords if k.arg})
        if n.func.id == "actuator" and "name" in args and isinstance(args["name"], ast.Constant) \
                and isinstance(args["name"].value, str) and api["actuators"] \
                and args["name"].value not in api["actuators"]:
            out.append(_diag(args["name"], "nepoznat aktuator `%s` (config.ACTUATORS: %s)"
                             % (args["name"].value, ", ".join(api["actuators"])), "error", "api"))
        if n.func.id in ("goto", "pose"):
            x, y = _num(args.get("x")), _num(args.get("y"))
            if (x is not None and not 0 <= x <= field.W) or (y is not None and not 0 <= y <= field.H):
                out.append(_diag(n, "%s: tačka (%s, %s) je van stola (x 0..%d, y 0..%d)" %
                                 (n.func.id, x, y, field.W, field.H), "warning", "api"))
        if n.func.id in ("goto", "move") and "speed" in args:
            v = _num(args["speed"])
            if v is not None and v > 1200:
                out.append(_diag(args["speed"], "speed %s mm/s: robot ide najviše ~1200 mm/s" % v, "warning", "api"))
    # beskonačna petlja bez ijednog tac poziva: taktika ne pušta glavnu petlju -> nema PING-a -> STM32 staje
    for n in ast.walk(tree):
        if isinstance(n, ast.While) and isinstance(n.test, ast.Constant) and n.test.value:
            calls = [c for c in ast.walk(n) if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
                     and c.func.id in funcs]
            if not calls:
                out.append(_diag(n, "`while True` bez ijednog tac poziva (wait, goto...): ESP se zaglavi, "
                                    "nema PING-a i STM32 staje posle 500 ms", "error", "loop"))
    # START
    start = [n for n in tree.body if isinstance(n, ast.Assign) and any(getattr(t, "id", None) == "START"
                                                                        for t in n.targets)]
    if not start:
        out.append(_diag(1, "nema START = (x, y, ugao): u meču se startna poza neće postaviti", "warning", "start"))
    else:
        s = start[0]
        vals = None
        if isinstance(s.value, (ast.Tuple, ast.List)):
            vals = [_num(e) for e in s.value.elts]
        if not vals or None in vals or len(s.value.elts) not in (2, 3) or s.end_lineno != s.lineno:
            out.append(_diag(s, "START mora biti brojevi u jednom redu, npr. START = (250, 1000, 0): ESP ga čita "
                                "bez izvršavanja (match.read_meta)", "error", "start"))
    return out


def runtime_diags(rec):
    """Dijagnostike iz simulacije: izuzeci sa linijom, neuspeli koraci, TOTAL."""
    out = []
    line_of = {}
    for _, kind, x in rec["events"]:
        if kind == "line":
            line_of[x[0]] = x[1]
        elif kind == "exception" and x.get("line"):
            out.append(_diag(x["line"], "u simulaciji: %s: %s" % (x["type"], x["msg"]), "error", "sim"))
        elif kind == "step_end" and not x[2] and x[0] in line_of:
            out.append(_diag(line_of[x[0]], "u simulaciji: korak %d \"%s\" nije uspeo: %s" % (x[0], x[1], x[3]),
                             "warning", "sim"))
    r = rec.get("result", {})
    total = rec.get("meta", {}).get("total")
    if total and r.get("steps") is not None and r.get("ok") and r["steps"] != total:
        out.append(_diag(1, "TOTAL = %d, a taktika je imala %d koraka (ekran pokazuje \"%d/%d\")"
                         % (total, r["steps"], r["steps"], total), "info", "sim"))
    if r.get("start_in_zone") is False:
        out.append(_diag(1, "robot na START pozi nije u svojoj startnoj zoni (pravila 2027; vidi ESP32/PROBLEMI.md, 1)",
                         "info", "sim"))
    return out


# ---------------- fajlovi ----------------

def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


PROTECTED = ("primer", "provera")      # primeri: ne brišu se i ne preimenuju iz editora


def path_of(name):
    import keyword
    if not NAME_RE.match(name or "") or keyword.iskeyword(name or ""):
        raise ValueError("ime taktike: slova, cifre i _, ne počinje cifrom, do 40 znakova (npr. zuta_1)")
    return paths.TACTICS / (name + ".py")


def rename(name, new):
    """Preimenuj taktiku (i <ime>_obnova.py ako postoji). Ne prepisuje postojeću."""
    src, dst = path_of(name), path_of(new)
    if name in PROTECTED:
        raise ValueError("%s je primer: koristi Save as" % name)
    if not src.exists():
        raise ValueError("nema taktike %s" % name)
    if dst.exists():
        raise FileExistsError("taktika %s već postoji" % new)
    src.rename(dst)
    ob, ob_new = paths.TACTICS / (name + "_obnova.py"), paths.TACTICS / (new + "_obnova.py")
    if ob.exists() and not ob_new.exists():
        ob.rename(ob_new)
    return {"renamed": name, "name": new}


def delete(name):
    p = path_of(name)
    if name in PROTECTED:
        raise ValueError("%s je primer i ne briše se" % name)
    if not p.exists():
        raise ValueError("nema taktike %s" % name)
    p.unlink()
    return {"deleted": name}


def read(name):
    p = path_of(name)
    text = p.read_text(encoding="utf-8")
    return {"name": name, "source": text, "sha": sha(text)}


def save(name, source, base_sha=None):
    """Upiši ESP32/tactics/<name>.py. base_sha: sha verzije koja je otvorena u editoru (None = nov fajl).
    Ako se fajl na disku u međuvremenu promenio, ne upisuje (vraća conflict)."""
    p = path_of(name)
    if p.exists():
        cur = sha(p.read_text(encoding="utf-8"))
        if base_sha != cur:
            return {"conflict": True, "sha": cur}
    elif base_sha:
        return {"conflict": True, "sha": None}
    if not source.endswith("\n"):
        source += "\n"
    p.write_text(source, encoding="utf-8", newline="\n")
    return {"saved": name, "sha": sha(source)}
