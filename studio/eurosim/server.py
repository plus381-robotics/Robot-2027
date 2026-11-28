# Lokalni server za simulator: služi web interfejs (studio/web) i pokreće simulacije.
#
#   python studio/sim.py serve            # http://localhost:8270, otvara browser
#
# Svaka simulacija radi u posebnom procesu (ESP kod ima globalno stanje; taktika sa beskonačnom petljom
# bez čekanja se ne može prekinuti drugačije). Simulacija ide do kraja što brže može, a browser dobija
# ceo snimak i sam ga pušta (brzina, pauza, korak, premotavanje).
import asyncio
import json
import multiprocessing as mp
import sys
import traceback
import webbrowser

from aiohttp import web

from . import field, paths, profile as profmod, session, tactics as tacmod
from .api import lidar as lidarapi, profile as profapi, repo as repoapi, runs, scenarios, tactics as tacapi
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
        "migrated": request.app[STATE].get("migrated") or {"moved": [], "skipped": []},
    })


# ---------------- scenariji: izmenjen sto (kamenolomi) i protivnici, plan E3 ----------------


# ---------------- sesija: jedan WebSocket za simulaciju, pravog robota i snimak ----------------

STALE_MS, LOST_MS = 1500, 5000       # starost poslednjeg paketa telemetrije: "stale" / "lost" (veza se ne zatvara)
POLL_S = 0.1
POLL_SIM_S = 0.05                    # worker simulacije šalje na 50 ms: Live ostaje na ~20 Hz


def _sim_source(request):
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
    return session.SimSource(kw)


def _robot_host(request):
    return request.query.get("host") or "eurokik.local"


def _robot_source(request):
    from . import robotlink
    q = request.query
    return session.RobotSource(_robot_host(request), q.get("password") or robotlink.default_password(),
                               request.app[STATE]["profile"],
                               upload_port=int(q.get("port") or robotlink.UPLOAD_PORT),
                               telem_port=int(q.get("telem") or robotlink.TELEM_PORT))


def _replay_source(request):
    f = runs._runs_dir() / (runs._safe_name(request.query.get("run") or "") + ".json.gz")
    return session.ReplaySource(f) if f.exists() else None


def _link_state(age):
    return "lost" if age > LOST_MS else "stale" if age > STALE_MS else "ok"


async def session_ws(request, engine=None):
    """WebSocket /ws/session?engine=sim|robot|replay&..: jedan oblik poruka za sva tri izvora.
    Server šalje {"type": "hello"|"data"|"reply"|"state"|"end"|"error", ...}, klijent JSON liste (komande).
    /ws/live i /ws/robot su isti handler sa engine=sim / engine=robot."""
    ws = web.WebSocketResponse(heartbeat=20, max_msg_size=32 * 1024 * 1024)
    await ws.prepare(request)
    engine = engine or request.query.get("engine") or "sim"

    async def send(o):
        if not ws.closed:
            await ws.send_str(_dumps(o))

    async def refuse(text):
        await send({"type": "error", "error": text})
        await ws.close()
        return ws

    try:
        source = {"sim": _sim_source, "robot": _robot_source, "replay": _replay_source}.get(engine, lambda r: None)(request)
    except ValueError as e:
        return await refuse("neispravni parametri: %s" % e)
    if source is None:
        return await refuse("nema snimka %s" % request.query.get("run") if engine == "replay"
                            else "nepoznat izvor: %s" % engine)
    try:
        await source.start()
    except OSError as e:
        await source.close()
        return await refuse("ne mogu da nađem %s: %s (probaj IP adresu sa ekrana VEZA)" % (_robot_host(request), e))
    except Exception as e:
        await source.close()
        return await refuse(str(e))
    await send({"type": "hello", "source": {"engine": source.kind, "parts": source.parts},
                "capabilities": sorted(source.capabilities)})

    async def pump():
        """Skuplja podatke izvora i šalje ih; vraća True ako je izvor javio grešku, False kad je gotov (final)."""
        link = "ok"
        while True:
            d = await source.poll()
            err = d.pop("error", None)
            if source.kind != "replay" or d["frames"] or d["events"] or d["meta"]:
                await send({"type": "data", **d})
            if source.kind == "robot":
                age = source.link_age()
                if _link_state(age) != link:
                    link = _link_state(age)
                    await send({"type": "state", "link": link, "age": age})
            if err:
                await send({"type": "error", "error": err})
                return True
            if d["final"]:
                return False
            await asyncio.sleep(POLL_SIM_S if source.kind == "sim" else POLL_S)

    async def reader():
        async for msg in ws:
            if msg.type != web.WSMsgType.TEXT:
                continue
            try:
                c = json.loads(msg.data)
            except ValueError:
                continue
            if not isinstance(c, list) or not c:
                continue
            if c[0] == "quit":
                return
            try:
                r = await source.command(c)
            except Exception as e:
                r = {"cmd": str(c[0]), "ok": False, "lines": [str(e)]}
            await send({"type": "reply", **r})

    failed = False
    pumping = asyncio.create_task(pump())
    reading = asyncio.create_task(reader())
    try:
        if source.kind == "robot":                    # UI iz STAT odgovora vidi "connected"
            ok, lines = await source.link.cmd("STAT")
            await send({"type": "reply", "cmd": "STAT", "ok": ok, "lines": lines})
        await asyncio.wait({pumping, reading}, return_when=asyncio.FIRST_COMPLETED)
    finally:
        reading.cancel()
        if pumping.done():
            failed = not pumping.cancelled() and pumping.exception() is None and pumping.result()
            if not pumping.cancelled() and pumping.exception() is not None:   # inače bi greška pumpe nestala bez traga
                e = pumping.exception()
                print("sesija (%s): pumpa je pala:" % engine, file=sys.stderr)
                traceback.print_exception(type(e), e, e.__traceback__, file=sys.stderr)
        else:
            pumping.cancel()                           # prvo stop poll-a, tek onda close()
        await asyncio.gather(pumping, reading, return_exceptions=True)
        rec = await source.close()
        if rec.get("frames"):
            request.app[STATE]["last"] = rec
        if not failed:
            await send({"type": "end", "run": pack(rec) if rec.get("frames") else None})
        if not ws.closed:
            await ws.close()
    return ws


async def live(request):
    """WebSocket /ws/live?tactic=..&side=..: stari naziv za /ws/session?engine=sim."""
    return await session_ws(request, "sim")


async def robot_ws(request):
    """WebSocket /ws/robot?host=..&password=..: stari naziv za /ws/session?engine=robot."""
    return await session_ws(request, "robot")


# ---------------- repo kao radni prostor (plan S10) ----------------




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
    app.router.add_get("/ws/session", session_ws)
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
    app.router.add_post("/api/lidar/stages", lidarapi.stages)
    app.router.add_get("/api/lidar/files", lidarapi.files_list)
    app.router.add_get("/api/lidar/files/{name}", lidarapi.file_get)
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
    app = make_app(prof)
    if paths.MODE == "repo":                          # jednom po pokretanju: stari simulator/lidar... -> studio/
        from . import migrate
        app[STATE]["migrated"] = migrate.move_old_local(paths.ROOT)
        m = app[STATE]["migrated"]
        if m["moved"]:
            print("preneto iz starog simulator/ u studio/: %d fajl(ova)" % len(m["moved"]))
        if m["skipped"]:
            print("ostavljeno u simulator/ (isto ime već postoji u studio/): %s" % ", ".join(m["skipped"]))
    web.run_app(app, host=host, port=port, print=None)


if __name__ == "__main__":
    serve()
