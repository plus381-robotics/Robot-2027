# Profil robota (F4).
import pathlib

from aiohttp import web

from .. import paths, profile as profmod
from ._util import STATE


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
