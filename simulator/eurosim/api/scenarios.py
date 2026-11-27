# Scenariji: izmenjen sto (kamenolomi) i protivnici, plan E3.
import json

from aiohttp import web

from .. import paths, tactics as tacmod


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
