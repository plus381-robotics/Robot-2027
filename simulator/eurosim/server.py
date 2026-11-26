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
import webbrowser

from aiohttp import web

from . import field, paths, profile as profmod, tactics as tacmod
from .api import profile as profapi, repo as repoapi, runs, scenarios, tactics as tacapi
from .api._util import STATE, _dumps, _elements_arg, _tactic_names, columns, pack
from .api.runs import RUN_TIMEOUT_S, _live_worker, _runs, run_in_process      # noqa: F401  (testovi: server.*)

RUNS = None                    # None = paths.RUNS (testovi ga menjaju; api/runs.py ga čita odavde)
PORT = 8270


# ---------------- HTTP ----------------

def _ir_layout(prof):
    """IR senzori za prikaz: [{name, x, y, d, z}] u mm, koordinate robota (isto kao plant.sensor_layout)."""
    from .plant import Plant
    return [{"name": n, "x": a * 1000, "y": b * 1000, "d": d, "z": z} for n, a, b, d, z in Plant(prof).sensor_layout()]


async def info(request):
    prof = request.app[STATE]["profile"]
    tactics = sorted(_tactic_names())
    return web.json_response({
        "tactics": tactics, "field": field.describe(),
        "profile": {"name": prof.get("name"), "body": prof["body"], "drive": prof["drive"],
                    "odometry": prof["odometry"], "ir": prof.get("ir", {}), "model": prof.get("model", {}),
                    "lidar": prof.get("lidar", {}),
                    "ir_sensors": _ir_layout(prof)},
        "sides": ["zuta", "plava"], "ref_side": tacmod.tac_api()["ref_side"], "runs": _runs(), "where": paths.describe(),
        "opp_tactics": __import__("eurosim.opponents", fromlist=["available"]).available(),
        "lidar_files": __import__("eurosim.lidarsrc", fromlist=["recordings"]).recordings(),
    })


# ---------------- scenariji: izmenjen sto (kamenolomi) i protivnici, plan E3 ----------------


async def live(request):
    """WebSocket /ws/live?tactic=..&side=..: interaktivna simulacija u stvarnom vremenu.
    Klijent šalje JSON liste (komande, vidi Sim.command), server šalje {"type": "data"|"end"|"error", ...}."""
    ws = web.WebSocketResponse(heartbeat=20, max_msg_size=32 * 1024 * 1024)
    await ws.prepare(request)
    q = request.query
    names = _tactic_names()
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
    if q.get("lidar") and q.get("lidar") != "sim":   # hibridna simulacija: lidar sa robota ili iz snimka
        kw["lidar_spec"], kw["lidar_pw"] = q.get("lidar"), q.get("lidar_pw") or None
    ctx = mp.get_context("spawn")
    a, b = ctx.Pipe()
    p = ctx.Process(target=_live_worker, args=(b, kw), daemon=True)
    p.start()
    b.close()
    loop = asyncio.get_running_loop()

    async def outgoing():
        while True:
            try:
                has = await loop.run_in_executor(None, a.poll, 0.2)
                if not has:
                    if not p.is_alive():
                        await ws.send_str(_dumps({"type": "error", "error": "proces simulacije je stao"}))
                        return
                    continue
                kind, d = a.recv()
            except (EOFError, OSError):
                return
            if ws.closed:
                return
            if kind == "data":
                await ws.send_str(_dumps({"type": "data", **d}))
            elif kind == "end":
                request.app[STATE]["last"] = d
                await ws.send_str(_dumps({"type": "end", "run": pack(d)}))
                return
            else:
                await ws.send_str(_dumps({"type": "error", "error": d}))
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


# ---------------- repo kao radni prostor (plan S10) ----------------


# ---------------- pravi robot (F5) ----------------

async def robot_ws(request):
    """WebSocket /ws/robot?host=..&password=..: telemetrija robota + komande (push, run, stop).
    Isti oblik podataka kao /ws/live; na kraju {"type": "end", "run": snimak}."""
    from . import robotlink
    ws = web.WebSocketResponse(heartbeat=20, max_msg_size=32 * 1024 * 1024)
    await ws.prepare(request)
    q = request.query
    host = q.get("host") or "eurokik.local"
    pw = q.get("password") or robotlink.default_password()

    async def emit(d):
        if not ws.closed:
            await ws.send_str(_dumps({"type": "data", **d}))

    link = robotlink.RobotLink(host, pw, emit, request.app[STATE]["profile"],
                               upload_port=int(q.get("port") or robotlink.UPLOAD_PORT),
                               telem_port=int(q.get("telem") or robotlink.TELEM_PORT))
    try:
        await link.start()
    except OSError as e:
        await ws.send_str(_dumps({"type": "error", "error": "ne mogu da nađem %s: %s (probaj IP adresu sa ekrana "
                                                        "VEZA)" % (host, e)}))
        await ws.close()
        return ws
    pump = asyncio.create_task(link.run())

    async def reply(c, ok, lines):
        if not ws.closed:
            await ws.send_str(_dumps({"type": "reply", "cmd": c, "ok": ok, "lines": lines}))

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
    finally:
        pump.cancel()
        link.close()
        res = link.recording()
        if res["frames"]:
            request.app[STATE]["last"] = res
        if not ws.closed:
            await ws.send_str(_dumps({"type": "end", "run": pack(res) if res["frames"] else None}))
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
    names = _tactic_names()
    kw = dict(name=q.get("tactic") if q.get("tactic") in names else None, side=q.get("side", "zuta"),
              prof=st["profile"], obstacles=q.get("obstacles") or [],
              net={"upload": int(q.get("port", 8267)), "telem": int(q.get("telem", 8268)), "password": "eurosim"})
    p = mp.get_context("spawn").Process(target=_vrobot_worker, args=(kw,), daemon=True)
    p.start()
    st["vrobot"] = p
    await asyncio.sleep(1.0)
    return web.json_response({"running": p.is_alive(), "host": "127.0.0.1", "password": "eurosim"})


# ---------------- profil robota (F4) ----------------


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
    app.router.add_post("/api/run", runs.run)
    app.router.add_get("/api/runs", runs.runs_list)
    app.router.add_post("/api/runs/save", runs.run_save)
    app.router.add_get("/api/runs/{name}", runs.run_load)
    app.router.add_get("/ws/live", live)
    app.router.add_get("/api/tacapi", tacapi.tac_api_h)
    app.router.add_get("/api/tactic/{name}", tacapi.tactic_get)
    app.router.add_post("/api/tactic/save", tacapi.tactic_save)
    app.router.add_post("/api/tactic/rename", tacapi.tactic_rename)
    app.router.add_post("/api/preview", tacapi.preview)
    app.router.add_get("/api/scenarios", scenarios.scenarios_list)
    app.router.add_post("/api/scenarios/save", scenarios.scenario_save)
    app.router.add_get("/api/scenarios/{name}", scenarios.scenario_get)
    app.router.add_get("/api/repo/status", repoapi.repo_status)
    app.router.add_post("/api/repo/open", repoapi.repo_open)
    app.router.add_post("/api/repo/clone", repoapi.repo_clone)
    app.router.add_post("/api/repo/pull", repoapi.repo_pull)
    app.router.add_post("/api/repo/save", repoapi.repo_save)
    app.router.add_post("/api/tactic/delete", tacapi.tactic_delete)
    app.router.add_post("/api/check", tacapi.check)
    app.router.add_post("/api/stage", tacapi.stage)
    app.router.add_get("/ws/robot", robot_ws)
    app.router.add_post("/api/vrobot", vrobot)
    app.router.add_get("/api/profile", profapi.profile_get)
    app.router.add_post("/api/profile", profapi.profile_set)
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
