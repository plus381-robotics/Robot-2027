# Taktike: API, čitanje, čuvanje, preimenovanje, brisanje, provera, nacrt putanje, stage za Live.
import asyncio
import uuid

from aiohttp import web

from .. import tactics as tacmod
from ._util import STATE


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


async def preview(request):
    """Nacrt putanje iz teksta taktike, bez simulacije (plan S7): lažni tac beleži komande."""
    from .. import preview as pv
    q = await request.json()
    api = request.app[STATE].setdefault("api", tacmod.tac_api())
    r = await asyncio.get_running_loop().run_in_executor(
        None, lambda: pv.preview(q.get("source", ""), q.get("side", "zuta"), api["ref_side"], api["field_x"],
                                 q.get("mode", "mec")))
    return web.json_response(r)


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
