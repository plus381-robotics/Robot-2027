# Lokalni server za simulator: služi web interfejs (simulator/web) i pokreće simulacije.
#
#   python simulator/sim.py serve            # http://localhost:8270, otvara browser
#
# Svaka simulacija radi u posebnom procesu (ESP kod ima globalno stanje; taktika sa beskonačnom petljom
# bez čekanja se ne može prekinuti drugačije). Simulacija ide do kraja što brže može, a browser dobija
# ceo snimak i sam ga pušta (brzina, pauza, korak, premotavanje).
import asyncio
import json
import multiprocessing as mp
import pathlib
import re
import time
import webbrowser

from aiohttp import web

from . import field, paths, profile as profmod
from .record import Recording

WEB = paths.SIM / "web"
RUNS = paths.SIM / "runs"
RUN_TIMEOUT_S = 60
PORT = 8270
STATE = web.AppKey("state", dict)          # {"profile": Profile, "last": poslednji snimak (dict)}


# ---------------- simulacija u posebnom procesu ----------------

def _worker(conn, kw):
    try:
        import contextlib
        import io
        from .sim import Sim
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rec = Sim(**kw).run()
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
        from .sim import Sim

        def control():
            out = []
            while conn.poll():
                out.append(conn.recv())
            return out

        def emit(d):
            conn.send(("data", d))

        with contextlib.redirect_stderr(io.StringIO()):
            rec = Sim(mode="live", control=control, emit=emit, **kw).run()
        conn.send(("end", rec.to_dict()))
    except BaseException as e:            # noqa: BLE001
        import traceback
        try:
            conn.send(("err", "%s\n%s" % (e, traceback.format_exc())))
        except Exception:
            pass
    finally:
        conn.close()


def columns(frames):
    """Frame-ovi (lista dict-ova) -> kolone (dict lista), za grafike i manji JSON."""
    keys = []
    for f in frames:
        for k in f:
            if k not in keys:
                keys.append(k)
    return {k: [f.get(k) for f in frames] for k in keys}


def pack(rec):
    d = dict(rec)
    d["cols"] = columns(d.pop("frames"))
    return d


# ---------------- HTTP ----------------

def _safe_name(s):
    s = re.sub(r"[^A-Za-z0-9_.-]+", "_", s.strip())[:60]
    return s or "run"


async def info(request):
    prof = request.app[STATE]["profile"]
    tactics = sorted(f.stem for f in paths.TACTICS.glob("*.py"))
    return web.json_response({
        "tactics": tactics, "field": field.describe(),
        "profile": {"name": prof.get("name"), "body": prof["body"], "drive": prof["drive"],
                    "odometry": prof["odometry"], "ir": prof.get("ir", {})},
        "sides": ["plava", "zuta"], "runs": _runs(),
    })


async def run(request):
    q = await request.json()
    name = q.get("tactic")
    if name not in {f.stem for f in paths.TACTICS.glob("*.py")}:
        return web.json_response({"error": "nema taktike %r" % name}, status=400)
    kw = dict(name=name, side=q.get("side", "plava"), mode=q.get("mode", "mec"),
              cord_s=float(q.get("cord_s", 1.0)), obstacles=q.get("obstacles") or [],
              prof=request.app[STATE]["profile"])
    if q.get("max_s"):
        kw["max_s"] = float(q["max_s"])
    t0 = time.time()
    kind, res = await asyncio.get_running_loop().run_in_executor(None, run_in_process, kw)
    if kind != "ok":
        return web.json_response({"error": res}, status=500)
    request.app[STATE]["last"] = res
    out = pack(res)
    out["wall_s"] = round(time.time() - t0, 2)
    return web.json_response(out, dumps=lambda o: json.dumps(o, separators=(",", ":")))


def _runs():
    if not RUNS.exists():
        return []
    return sorted((f.name[:-8] for f in RUNS.glob("*.json.gz")), reverse=True)


async def runs_list(request):
    return web.json_response(_runs())


async def run_save(request):
    q = await request.json()
    last = request.app[STATE]["last"]
    if not last:
        return web.json_response({"error": "nema simulacije za čuvanje"}, status=400)
    m = last["meta"]
    name = _safe_name(q.get("name") or "%s_%s_%s" % (time.strftime("%Y%m%d-%H%M%S"), m["tactic"], m["side"]))
    RUNS.mkdir(exist_ok=True)
    r = Recording(m)
    r.frames, r.events, r.result = last["frames"], last["events"], last["result"]
    r.save(RUNS / (name + ".json.gz"))
    return web.json_response({"saved": name, "runs": _runs()})


async def run_load(request):
    name = _safe_name(request.match_info["name"])
    f = RUNS / (name + ".json.gz")
    if not f.exists():
        return web.json_response({"error": "nema snimka %s" % name}, status=404)
    r = Recording.load(f)
    request.app[STATE]["last"] = r.to_dict()
    return web.json_response(pack(r.to_dict()), dumps=lambda o: json.dumps(o, separators=(",", ":")))


async def live(request):
    """WebSocket /ws/live?tactic=..&side=..: interaktivna simulacija u stvarnom vremenu.
    Klijent šalje JSON liste (komande, vidi Sim.command), server šalje {"type": "data"|"end"|"error", ...}."""
    ws = web.WebSocketResponse(heartbeat=20, max_msg_size=32 * 1024 * 1024)
    await ws.prepare(request)
    q = request.query
    names = {f.stem for f in paths.TACTICS.glob("*.py")}
    tactic = q.get("tactic") if q.get("tactic") in names else None
    try:
        obstacles = json.loads(q.get("obstacles") or "[]")
    except ValueError:
        obstacles = []
    kw = dict(name=tactic, side=q.get("side", "plava"), obstacles=obstacles, prof=request.app[STATE]["profile"])
    ctx = mp.get_context("spawn")
    a, b = ctx.Pipe()
    p = ctx.Process(target=_live_worker, args=(b, kw), daemon=True)
    p.start()
    b.close()
    loop = asyncio.get_running_loop()
    dumps = lambda o: json.dumps(o, separators=(",", ":"))   # noqa: E731

    async def outgoing():
        while True:
            try:
                has = await loop.run_in_executor(None, a.poll, 0.2)
                if not has:
                    if not p.is_alive():
                        await ws.send_str(dumps({"type": "error", "error": "proces simulacije je stao"}))
                        return
                    continue
                kind, d = a.recv()
            except (EOFError, OSError):
                return
            if ws.closed:
                return
            if kind == "data":
                await ws.send_str(dumps({"type": "data", **d}))
            elif kind == "end":
                request.app[STATE]["last"] = d
                await ws.send_str(dumps({"type": "end", "run": pack(d)}))
                return
            else:
                await ws.send_str(dumps({"type": "error", "error": d}))
                return

    task = asyncio.create_task(outgoing())
    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                try:
                    a.send(tuple(json.loads(msg.data)))
                except (ValueError, OSError, BrokenPipeError):
                    pass
            if task.done():
                break
    finally:
        if p.is_alive():
            try:
                a.send(("quit",))
            except (OSError, BrokenPipeError):
                pass
        try:
            await asyncio.wait_for(task, 5)
        except (asyncio.TimeoutError, Exception):
            task.cancel()
        p.join(1)
        if p.is_alive():
            p.kill()
        if not ws.closed:
            await ws.close()
    return ws


async def index(request):
    return web.FileResponse(WEB / "index.html")


def make_app(prof=None):
    app = web.Application(client_max_size=8 * 1024 * 1024)
    app[STATE] = {"profile": prof or profmod.load(), "last": None}
    app.router.add_get("/", index)
    app.router.add_get("/api/info", info)
    app.router.add_post("/api/run", run)
    app.router.add_get("/api/runs", runs_list)
    app.router.add_post("/api/runs/save", run_save)
    app.router.add_get("/api/runs/{name}", run_load)
    app.router.add_get("/ws/live", live)
    app.router.add_static("/", WEB, show_index=False)
    return app


def serve(port=PORT, host="127.0.0.1", open_browser=True, prof=None):
    url = "http://%s:%d/" % ("localhost" if host in ("127.0.0.1", "0.0.0.0") else host, port)
    print("simulator: %s  (Ctrl+C za kraj)" % url)
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    web.run_app(make_app(prof), host=host, port=port, print=None)


if __name__ == "__main__":
    serve()
