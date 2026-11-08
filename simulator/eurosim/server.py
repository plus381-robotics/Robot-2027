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
import os
import pathlib
import uuid
import pathlib
import re
import time
import webbrowser

from aiohttp import web

from . import field, paths, profile as profmod, tactics as tacmod
from .record import Recording

RUNS = None                    # None = paths.RUNS (testovi ga menjaju)


def _runs_dir():
    return RUNS or paths.RUNS
RUN_TIMEOUT_S = 60
PORT = 8270
STATE = web.AppKey("state", dict)          # {"profile": Profile, "last": poslednji snimak (dict)}


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
        from .sim import Sim
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
        from .sim import Sim

        def control():
            out = []
            while conn.poll():
                out.append(conn.recv())
            return out

        def emit(d):
            conn.send(("data", d))

        tmp = _staged(kw)
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


def _ir_layout(prof):
    """IR senzori za prikaz: [{name, x, y, d, z}] u mm, koordinate robota (isto kao plant.sensor_layout)."""
    from .plant import Plant
    return [{"name": n, "x": a * 1000, "y": b * 1000, "d": d, "z": z} for n, a, b, d, z in Plant(prof).sensor_layout()]


async def info(request):
    prof = request.app[STATE]["profile"]
    tactics = sorted(f.stem for f in paths.TACTICS.glob("*.py"))
    return web.json_response({
        "tactics": tactics, "field": field.describe(),
        "profile": {"name": prof.get("name"), "body": prof["body"], "drive": prof["drive"],
                    "odometry": prof["odometry"], "ir": prof.get("ir", {}), "model": prof.get("model", {}),
                    "ir_sensors": _ir_layout(prof)},
        "sides": ["zuta", "plava"], "ref_side": tacmod.tac_api()["ref_side"], "runs": _runs(), "where": paths.describe(),
        "opp_tactics": __import__("eurosim.opponents", fromlist=["available"]).available(),
    })


def _elements_arg(v):
    """Kamenolomi iz zahteva: True/False/"1"/"0" (po pravilima ili bez) ili lista (izmenjen sto, JSON)."""
    if isinstance(v, str):
        if v in ("0", "1", ""):
            return v != "0"
        try:
            v = json.loads(v)
        except ValueError:
            return True
    return v if isinstance(v, list) else bool(v)


# ---------------- scenariji: izmenjen sto (kamenolomi) i protivnici, plan E3 ----------------

def _scen_dir():
    d = paths.SCENARIOS
    d.mkdir(parents=True, exist_ok=True)
    return d


async def scenarios_list(request):
    return web.json_response({"scenarios": sorted(p.stem for p in _scen_dir().glob("*.json"))})


async def scenario_get(request):
    n = request.match_info["name"]
    if not tacmod.NAME_RE.match(n):
        return web.json_response({"error": "ime"}, status=400)
    p = _scen_dir() / (n + ".json")
    if not p.exists():
        return web.json_response({"error": "nema scenarija " + n}, status=404)
    return web.json_response(json.loads(p.read_text(encoding="utf-8")))


async def scenario_save(request):
    q = await request.json()
    n = q.get("name", "")
    if not tacmod.NAME_RE.match(n or ""):
        return web.json_response({"error": "ime: slova, cifre i _"}, status=400)
    data = {"elements": q.get("elements"), "opponents": q.get("opponents") or [], "note": q.get("note", "")}
    (_scen_dir() / (n + ".json")).write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    return web.json_response({"saved": n, "scenarios": sorted(p.stem for p in _scen_dir().glob("*.json"))})


async def run(request):
    q = await request.json()
    name = q.get("tactic")
    source = q.get("source")
    if source is not None:
        if not tacmod.NAME_RE.match(name or ""):
            return web.json_response({"error": "neispravno ime taktike %r" % name}, status=400)
    elif name not in {f.stem for f in paths.TACTICS.glob("*.py")}:
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
    return web.json_response(out, dumps=lambda o: json.dumps(o, separators=(",", ":")))


def _runs():
    d = _runs_dir()
    if not d.exists():
        return []
    return sorted((f.name[:-8] for f in d.glob("*.json.gz")), reverse=True)


async def runs_list(request):
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
    name = _safe_name(request.match_info["name"])
    f = _runs_dir() / (name + ".json.gz")
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
    staged = request.app[STATE].get("staged", {}).pop(q.get("stage"), None)
    try:
        obstacles = json.loads(q.get("obstacles") or "[]")
    except ValueError:
        obstacles = []
    kw = dict(name=tactic, side=q.get("side", "zuta"), obstacles=obstacles, prof=request.app[STATE]["profile"],
              elements=_elements_arg(q.get("elements", "1")))
    if staged:
        kw["name"], kw["source"] = staged
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


async def tac_api_h(request):
    api = tacmod.tac_api()                      # svaki put iz tac.py (prati izmene)
    request.app[STATE]["api"] = api
    return web.json_response(dict(api, template=tacmod.TEMPLATE))


async def tactic_get(request):
    try:
        return web.json_response(tacmod.read(request.match_info["name"]))
    except (ValueError, OSError) as e:
        return web.json_response({"error": str(e)}, status=404)


async def tactic_save(request):
    q = await request.json()
    try:
        r = tacmod.save(q.get("name"), q.get("source", ""), q.get("sha"))
    except ValueError as e:
        return web.json_response({"error": str(e)}, status=400)
    if r.get("conflict"):
        return web.json_response({"error": "fajl je u međuvremenu promenjen na disku (git, drugi editor); "
                                           "osveži ili sačuvaj pod drugim imenom", **r}, status=409)
    return web.json_response(r)


async def preview(request):
    """Nacrt putanje iz teksta taktike, bez simulacije (plan S7): lažni tac beleži komande."""
    from . import preview as pv
    q = await request.json()
    api = request.app[STATE].setdefault("api", tacmod.tac_api())
    r = await asyncio.get_running_loop().run_in_executor(
        None, lambda: pv.preview(q.get("source", ""), q.get("side", "zuta"), api["ref_side"], api["field_x"],
                                 q.get("mode", "mec")))
    return web.json_response(r)


# ---------------- repo kao radni prostor (plan S10) ----------------

async def _repo_call(fn, *a):
    from . import repo
    try:
        return web.json_response(await asyncio.get_running_loop().run_in_executor(None, fn, *a))
    except repo.GitError as e:
        return web.json_response({"error": str(e)}, status=502)
    except (ValueError, OSError) as e:
        return web.json_response({"error": str(e)}, status=400)


def _reload_repo(app):
    """Posle prelaska na drugi repo: profil i API taktika iz novog repoa."""
    app[STATE]["profile"] = profmod.load()
    app[STATE].pop("api", None)


async def repo_status(request):
    from . import repo
    return await _repo_call(repo.status, request.query.get("fetch") == "1")


async def repo_open(request):
    from . import repo
    q = await request.json()
    r = await _repo_call(repo.open_repo, q.get("path", ""))
    if r.status == 200:
        _reload_repo(request.app)
    return r


async def repo_clone(request):
    from . import repo
    q = await request.json()
    r = await _repo_call(repo.clone, q.get("parent", ""))
    if r.status == 200:
        _reload_repo(request.app)
    return r


async def repo_pull(request):
    from . import repo
    r = await _repo_call(repo.pull)
    _reload_repo(request.app)
    return r


async def repo_save(request):
    from . import repo
    q = await request.json()
    return await _repo_call(repo.save, q.get("message", ""))


async def tactic_rename(request):
    q = await request.json()
    try:
        return web.json_response(tacmod.rename(q.get("name"), q.get("new")))
    except FileExistsError as e:
        return web.json_response({"error": str(e)}, status=409)
    except (ValueError, OSError) as e:
        return web.json_response({"error": str(e)}, status=400)


async def tactic_delete(request):
    q = await request.json()
    try:
        return web.json_response(tacmod.delete(q.get("name")))
    except (ValueError, OSError) as e:
        return web.json_response({"error": str(e)}, status=400)


async def check(request):
    q = await request.json()
    api = request.app[STATE].setdefault("api", tacmod.tac_api())
    diags = await asyncio.get_running_loop().run_in_executor(None, tacmod.static_check, q.get("source", ""), api)
    return web.json_response({"diagnostics": diags})


async def stage(request):
    """Tekst iz editora za Live (ne staje u URL): vraća oznaku za /ws/live?stage=..."""
    q = await request.json()
    if not tacmod.NAME_RE.match(q.get("name") or ""):
        return web.json_response({"error": "neispravno ime"}, status=400)
    st = request.app[STATE].setdefault("staged", {})
    if len(st) > 20:
        st.clear()
    key = uuid.uuid4().hex
    st[key] = (q["name"], q.get("source", ""))
    return web.json_response({"stage": key})


# ---------------- pravi robot (F5) ----------------

async def robot_ws(request):
    """WebSocket /ws/robot?host=..&password=..: telemetrija robota + komande (push, run, stop, stat).
    Isti oblik podataka kao /ws/live; na kraju {"type": "end", "run": snimak}."""
    from . import robotlink
    ws = web.WebSocketResponse(heartbeat=20, max_msg_size=32 * 1024 * 1024)
    await ws.prepare(request)
    q = request.query
    host = q.get("host") or "eurokik.local"
    pw = q.get("password") or robotlink.default_password()
    dumps = lambda o: json.dumps(o, separators=(",", ":"))   # noqa: E731

    async def emit(d):
        if not ws.closed:
            await ws.send_str(dumps({"type": "data", **d}))

    link = robotlink.RobotLink(host, pw, emit, request.app[STATE]["profile"],
                               upload_port=int(q.get("port") or robotlink.UPLOAD_PORT),
                               telem_port=int(q.get("telem") or robotlink.TELEM_PORT))
    try:
        await link.start()
    except OSError as e:
        await ws.send_str(dumps({"type": "error", "error": "ne mogu da nađem %s: %s (probaj IP adresu sa ekrana "
                                                        "VEZA)" % (host, e)}))
        await ws.close()
        return ws
    pump = asyncio.create_task(link.run())

    async def reply(c, ok, lines):
        if not ws.closed:
            await ws.send_str(dumps({"type": "reply", "cmd": c, "ok": ok, "lines": lines}))

    try:
        ok, lines = await link.cmd("STAT")
        await reply("STAT", ok, lines)
        async for msg in ws:
            if msg.type != web.WSMsgType.TEXT:
                continue
            try:
                c = json.loads(msg.data)
            except ValueError:
                continue
            k = c[0]
            if k == "quit":
                break
            if k == "push":                       # ["push", ime, tekst ili null = fajl iz ESP32/tactics]
                name, src = c[1], c[2] if len(c) > 2 else None
                if not tacmod.NAME_RE.match(name or ""):
                    await reply(k, False, ["neispravno ime"])
                    continue
                if src is None:
                    src = (paths.TACTICS / (name + ".py")).read_text(encoding="utf-8")
                data = src.encode("utf-8")
                ok, lines = await link.cmd("PUT", "/tactics/%s.py" % name, len(data), data=data)
                await reply(k, ok, lines)
            elif k == "run":
                ok, lines = await link.cmd("RUN", c[1], c[2] if len(c) > 2 else "")
                await reply(k, ok, lines)
            elif k == "stop":
                ok, lines = await link.cmd("STOP")
                await reply(k, ok, lines)
            elif k == "stat":
                ok, lines = await link.cmd("STAT")
                await reply(k, ok, lines)
    finally:
        pump.cancel()
        link.close()
        res = link.recording()
        if res["frames"]:
            request.app[STATE]["last"] = res
        if not ws.closed:
            await ws.send_str(dumps({"type": "end", "run": pack(res) if res["frames"] else None}))
            await ws.close()
    return ws


def _vrobot_worker(kw):
    import contextlib
    import io
    from .sim import Sim
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        Sim(mode="live", **kw).run()


async def vrobot(request):
    """POST /api/vrobot {"action": "start"|"stop"}: virtuelni robot na 127.0.0.1 (kao sim.py robot)."""
    q = await request.json()
    st = request.app[STATE]
    p = st.get("vrobot")
    if q.get("action") == "stop" or (p is not None and q.get("action") == "start"):
        if p is not None and p.is_alive():
            p.kill()
            p.join(2)
        st["vrobot"] = None
        if q.get("action") == "stop":
            return web.json_response({"running": False})
    names = {f.stem for f in paths.TACTICS.glob("*.py")}
    kw = dict(name=q.get("tactic") if q.get("tactic") in names else None, side=q.get("side", "zuta"),
              prof=st["profile"], obstacles=q.get("obstacles") or [],
              net={"upload": int(q.get("port", 8267)), "telem": int(q.get("telem", 8268)), "password": "eurosim"})
    p = mp.get_context("spawn").Process(target=_vrobot_worker, args=(kw,), daemon=True)
    p.start()
    st["vrobot"] = p
    await asyncio.sleep(1.0)
    return web.json_response({"running": p.is_alive(), "host": "127.0.0.1", "password": "eurosim"})


# ---------------- profil robota (F4) ----------------

async def profile_get(request):
    f = request.app[STATE].get("profile_path") or paths.DEFAULT_PROFILE
    return web.json_response({"file": str(f), "files": sorted(x.name for x in paths.PROFILES.glob("*.toml")),
                              "sections": profmod.describe(f)})


async def profile_set(request):
    q = await request.json()
    st = request.app[STATE]
    f = pathlib.Path(st.get("profile_path") or paths.DEFAULT_PROFILE)
    if q.get("file"):
        f2 = paths.PROFILES / pathlib.Path(q["file"]).name
        if not f2.exists():
            return web.json_response({"error": "nema profila %s" % q["file"]}, status=404)
        f = f2
    try:
        if q.get("changes"):
            profmod.update_file(f, q["changes"])
        prof = profmod.load(f)
    except (ValueError, KeyError) as e:
        return web.json_response({"error": str(e)}, status=400)
    st["profile"], st["profile_path"] = prof, f
    return web.json_response({"file": str(f), "sections": profmod.describe(f), "name": prof.get("name")})


async def index(request):
    return web.FileResponse(paths.WEB / "index.html")


@web.middleware
async def no_stale_ui(request, handler):
    """Interfejs se ne kešira bez provere: posle git pull / nove verzije pregledač mora da dobije nove
    index.html i *.js (inače ostaje stari UI). Lokalno je provera jeftina (304 Not Modified)."""
    resp = await handler(request)
    if not request.path.startswith(("/api/", "/ws/")):
        resp.headers["Cache-Control"] = "no-cache"
    return resp


def make_app(prof=None):
    app = web.Application(client_max_size=8 * 1024 * 1024, middlewares=[no_stale_ui])
    app[STATE] = {"profile": prof or profmod.load(), "last": None}
    app.router.add_get("/", index)
    app.router.add_get("/api/info", info)
    app.router.add_post("/api/run", run)
    app.router.add_get("/api/runs", runs_list)
    app.router.add_post("/api/runs/save", run_save)
    app.router.add_get("/api/runs/{name}", run_load)
    app.router.add_get("/ws/live", live)
    app.router.add_get("/api/tacapi", tac_api_h)
    app.router.add_get("/api/tactic/{name}", tactic_get)
    app.router.add_post("/api/tactic/save", tactic_save)
    app.router.add_post("/api/tactic/rename", tactic_rename)
    app.router.add_post("/api/preview", preview)
    app.router.add_get("/api/scenarios", scenarios_list)
    app.router.add_post("/api/scenarios/save", scenario_save)
    app.router.add_get("/api/scenarios/{name}", scenario_get)
    app.router.add_get("/api/repo/status", repo_status)
    app.router.add_post("/api/repo/open", repo_open)
    app.router.add_post("/api/repo/clone", repo_clone)
    app.router.add_post("/api/repo/pull", repo_pull)
    app.router.add_post("/api/repo/save", repo_save)
    app.router.add_post("/api/tactic/delete", tactic_delete)
    app.router.add_post("/api/check", check)
    app.router.add_post("/api/stage", stage)
    app.router.add_get("/ws/robot", robot_ws)
    app.router.add_post("/api/vrobot", vrobot)
    app.router.add_get("/api/profile", profile_get)
    app.router.add_post("/api/profile", profile_set)
    app.router.add_static("/", paths.WEB, show_index=False)
    return app


def serve(port=PORT, host="127.0.0.1", open_browser=True, prof=None):
    url = "http://%s:%d/" % ("localhost" if host in ("127.0.0.1", "0.0.0.0") else host, port)
    import socket
    with socket.socket() as so:                       # port zauzet: verovatno već radi (stari) Eurosim
        try:
            so.bind((host, port))
        except OSError:
            raise SystemExit("port %d je zauzet: verovatno već radi Eurosim (možda stara verzija).\n"
                             "Zatvori ga (Ctrl+C u njegovom prozoru) pa pokreni ponovo, ili: serve --port %d"
                             % (port, port + 1))
    print("simulator: %s  (Ctrl+C za kraj)" % url)
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    web.run_app(make_app(prof), host=host, port=port, print=None)


if __name__ == "__main__":
    serve()
