# Simulacija u posebnom procesu, /api/run i snimci (/api/runs).
import asyncio
import datetime
import multiprocessing as mp
import os
import re
import time
import zlib

from aiohttp import web

from .. import paths, tactics as tacmod
from ..record import Recording
from ._util import STATE, _dumps, _elements_arg, _tactic_names, pack

RUN_TIMEOUT_S = 60


def _runs_dir():
    from .. import server                  # server.RUNS menjaju testovi
    return server.RUNS or paths.RUNS


# ---------------- simulacija u posebnom procesu ----------------

def _staged(kw):
    """kw["source"] (tekst iz editora, ne mora biti sačuvan): sve taktike + ova u privremeni folder."""
    src = kw.pop("source", None)
    if src is None:
        return None
    import shutil
    import tempfile
    d = tempfile.TemporaryDirectory(prefix="eurosim-tac-")
    for f in paths.TACTICS.glob("*.py"):
        shutil.copy(f, d.name)
    with open(os.path.join(d.name, kw["name"] + ".py"), "w", encoding="utf-8") as fh:
        fh.write(src)
    kw["tactics_dir"] = d.name
    return d


def _worker(conn, kw):
    try:
        import contextlib
        import io
        from ..sim import Sim
        err = io.StringIO()
        tmp = _staged(kw)
        with contextlib.redirect_stderr(err):
            rec = Sim(**kw).run()
        if tmp:
            tmp.cleanup()
        conn.send(("ok", rec.to_dict()))
    except BaseException as e:            # noqa: BLE001  (sve greške idu nazad u UI)
        import traceback
        conn.send(("err", "%s\n%s" % (e, traceback.format_exc())))
    finally:
        conn.close()


def run_in_process(kw, timeout=RUN_TIMEOUT_S):
    ctx = mp.get_context("spawn")
    a, b = ctx.Pipe(duplex=False)
    p = ctx.Process(target=_worker, args=(b, kw), daemon=True)
    p.start()
    b.close()
    try:
        if not a.poll(timeout):
            p.kill()
            return "err", "simulacija nije završila za %d s (beskonačna petlja bez wait()?)" % timeout
        return a.recv()
    except EOFError:
        return "err", "proces simulacije je pao"
    finally:
        p.join(1)
        if p.is_alive():
            p.kill()


def _live_worker(conn, kw):
    """Live simulacija: komande stižu kroz conn, podaci idu nazad ("data", d), na kraju ("end", snimak)."""
    try:
        import contextlib
        import io
        from ..sim import Sim

        def control():
            out = []
            while conn.poll():
                out.append(conn.recv())
            return out

        def emit(d):
            conn.send(("data", d))

        tmp = _staged(kw)
        from .. import lidarsrc                       # izvor lidara se pravi ovde (nit i soket ne prelaze u proces)
        kw["lidar"] = lidarsrc.open_source(kw.pop("lidar_spec", None), kw.pop("lidar_pw", None))
        with contextlib.redirect_stderr(io.StringIO()):
            rec = Sim(mode="live", control=control, emit=emit, **kw).run()
        if tmp:
            tmp.cleanup()
        conn.send(("end", rec.to_dict()))
    except BaseException as e:            # noqa: BLE001
        import traceback
        try:
            conn.send(("err", "%s\n%s" % (e, traceback.format_exc())))
        except Exception:
            pass
    finally:
        conn.close()


def _safe_name(s):
    s = re.sub(r"[^A-Za-z0-9_.-]+", "_", s.strip())[:60]
    return s or "run"


async def run(request):
    q = await request.json()
    name = q.get("tactic")
    source = q.get("source")
    if source is not None:
        if not tacmod.NAME_RE.match(name or ""):
            return web.json_response({"error": "neispravno ime taktike %r" % name}, status=400)
    elif name not in _tactic_names():
        return web.json_response({"error": "nema taktike %r" % name}, status=400)
    else:
        source = (paths.TACTICS / (name + ".py")).read_text(encoding="utf-8")
    loop = asyncio.get_running_loop()
    api = request.app[STATE].setdefault("api", tacmod.tac_api())
    diags = await loop.run_in_executor(None, tacmod.static_check, source, api)
    if any(d["source"] == "syntax" for d in diags):
        return web.json_response({"error": "taktika ima sintaksnu grešku", "diagnostics": diags}, status=422)
    kw = dict(source=source, name=name, side=q.get("side", "zuta"), mode=q.get("mode", "mec"),
              cord_s=float(q.get("cord_s", 1.0)), obstacles=q.get("obstacles") or [],
              elements=_elements_arg(q.get("elements", True)),
              prof=request.app[STATE]["profile"])
    if q.get("max_s"):
        kw["max_s"] = float(q["max_s"])
    t0 = time.time()
    kind, res = await loop.run_in_executor(None, run_in_process, kw)
    if kind != "ok":
        return web.json_response({"error": res, "diagnostics": diags}, status=500)
    request.app[STATE]["last"] = res
    out = pack(res)
    out["diagnostics"] = diags + tacmod.runtime_diags(res)
    out["wall_s"] = round(time.time() - t0, 2)
    return web.json_response(out, dumps=_dumps)


def _runs():
    d = _runs_dir()
    if not d.exists():
        return []
    return sorted((f.name[:-8] for f in d.glob("*.json.gz")), reverse=True)


# Detalji snimka za listu u Snimcima; keš po putanji, važi dok se mtime i veličina fajla ne promene.
_DETAIL_CACHE = {}


def _lidar_of(meta):
    """Odakle je lidar u snimku: parts.lidar (v2) ili, za v1, iz meta.lidar_source; None = nepoznato."""
    parts = (meta.get("origin") or {}).get("parts") or {}
    if parts.get("lidar"):
        return parts["lidar"]
    src = meta.get("lidar_source")
    if isinstance(src, str):
        return "pravi" if src.startswith("robot") else "snimak" if src.startswith("snimak") else "sim"
    return None


def run_detail(f):
    """Jedan red liste: ime, datum (mtime, lokalno ISO), izvor (engine + lidar), taktika, strana, režim, ishod, trajanje."""
    st = f.stat()
    key = str(f)
    hit = _DETAIL_CACHE.get(key)
    if hit and hit[0] == (st.st_mtime_ns, st.st_size):
        return hit[1]
    name = f.name[:-8]
    date = datetime.datetime.fromtimestamp(st.st_mtime).astimezone().isoformat(timespec="seconds")
    try:
        d = Recording.peek(f)
        meta, res = d.get("meta") or {}, d.get("result") or {}
        ok = res.get("ok")
        dur = res.get("sim_ms")
        out = {"name": name, "date": date, "engine": (meta.get("origin") or {}).get("engine"),
               "lidar": _lidar_of(meta), "tactic": meta.get("tactic"), "side": meta.get("side"),
               "mode": meta.get("mode"), "ok": ok if ok is None else bool(ok),
               "duration_ms": dur if isinstance(dur, (int, float)) else None}
    except Exception as e:                    # noqa: BLE001  (oštećen fajl: red ostaje, sa greškom)
        out = {"name": name, "date": date, "engine": None, "lidar": None, "tactic": None, "side": None,
               "mode": None, "ok": None, "duration_ms": None, "error": str(e)[:200]}
    _DETAIL_CACHE[key] = ((st.st_mtime_ns, st.st_size), out)
    return out


def _runs_detail():
    d = _runs_dir()
    if not d.exists():
        return []
    out, seen = [], set()
    for f in d.glob("*.json.gz"):
        try:
            out.append(run_detail(f))
            seen.add(str(f))
        except OSError:                       # fajl obrisan u međuvremenu
            continue
    for k in [k for k in list(_DETAIL_CACHE) if k not in seen and os.path.dirname(k) == str(d)]:
        _DETAIL_CACHE.pop(k, None)            # obrisani fajlovi (dva paralelna zahteva: niti iz executor-a)
    return sorted(out, key=lambda r: (datetime.datetime.fromisoformat(r["date"]), r["name"]), reverse=True)


async def runs_list(request):
    """GET /api/runs -> imena (kao ranije);  GET /api/runs?detail=1 -> redovi za listu u Snimcima (najnoviji prvi)."""
    if request.query.get("detail") in ("1", "true"):
        loop = asyncio.get_running_loop()
        return web.json_response(await loop.run_in_executor(None, _runs_detail))
    return web.json_response(_runs())


async def run_save(request):
    q = await request.json()
    last = request.app[STATE]["last"]
    if not last:
        return web.json_response({"error": "nema simulacije za čuvanje"}, status=400)
    m = last["meta"]
    name = _safe_name(q.get("name") or "%s_%s_%s" % (time.strftime("%Y%m%d-%H%M%S"), m["tactic"], m["side"]))
    _runs_dir().mkdir(parents=True, exist_ok=True)
    r = Recording(m)
    r.frames, r.events, r.result = last["frames"], last["events"], last["result"]
    r.save(_runs_dir() / (name + ".json.gz"))
    return web.json_response({"saved": name, "runs": _runs()})


async def run_load(request):
    """GET /api/runs/{name}: snimak za puštanje; postaje „poslednji“ (to čuva /api/runs/save).
    ?ref=1: samo za poređenje (referenca), „poslednji“ ostaje ono što se gleda."""
    name = _safe_name(request.match_info["name"])
    f = _runs_dir() / (name + ".json.gz")
    if not f.exists():
        return web.json_response({"error": "nema snimka %s" % name}, status=404)
    try:
        r = Recording.load(f)
    except (OSError, ValueError, KeyError, EOFError, TypeError, zlib.error) as e:   # oštećen fajl: 422 umesto HTML 500
        return web.json_response({"error": "snimak %s se ne čita: %s" % (name, e)}, status=422)
    d = r.to_dict()
    if request.query.get("ref") not in ("1", "true"):
        request.app[STATE]["last"] = d
    return web.json_response(pack(d), dumps=_dumps)
