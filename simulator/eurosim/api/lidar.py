# Test dela → Lidar (HTTP): međukoraci jednog kruga (eurosim/lidarview.py, računa laptop) i snimci krugova iz
# simulator/lidar/ (lidarsrc.lidar_dir(), format koji čita lidarsrc.FileLidar) za puštanje u pregledaču.
#   POST /api/lidar/stages {scan, pose}        -> lidarview.stages(scan, pose, profil)
#   GET  /api/lidar/files                      -> {"files": [{name, size, mtime}]}
#   GET  /api/lidar/files/{name}?every=N       -> {"name", "meta", "total", "every", "truncated",
#                                                  "scans": [{t, pts, hz, near, pose, o}]}  (t od prvog kruga, ms)
# Ime snimka: samo obično ime fajla direktno u lidar_dir() (bez putanje, bez „..“), sa ili bez .jsonl.gz.
import asyncio
import gzip
import json
import re
import zlib

from aiohttp import web

from .. import lidarsrc, lidarview
from ._util import STATE, _dumps

EXT = ".jsonl.gz"
NAME_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,80}$")
MAX_SCANS = 3000             # najviše krugova u jednom odgovoru (~5 min na 10 Hz); više: ?every=N
MAX_EVERY = 1000


def _bad(text, status=400):
    return web.json_response({"error": text}, status=status)


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v == v and abs(v) < 1e7


async def stages(request):
    try:
        q = await request.json()
    except ValueError:
        return _bad("neispravan JSON")
    scan, pose = (q or {}).get("scan"), (q or {}).get("pose")
    if not isinstance(scan, dict) or not isinstance(scan.get("pts", []), list) \
            or len(scan.get("pts", [])) > 2 * lidarview.MAX_PTS or not all(_num(v) for v in scan.get("pts", [])):
        return _bad("scan: {pts: [ugao, mm, ...], o, near, hz}")
    o = scan.get("o")
    if o is not None and (not isinstance(o, list) or not all(_num(v) for v in o)):
        return _bad("scan.o: [x, y, z]")
    if pose is not None and (not isinstance(pose, list) or len(pose) != 3 or not all(_num(v) for v in pose)):
        return _bad("pose: [x, y, ugao] ili null")
    near = scan.get("near")
    if near is not None and (not isinstance(near, list) or len(near) != 2 or not all(_num(v) for v in near)):
        scan = {**scan, "near": None}
    return web.json_response(lidarview.stages(scan, pose, request.app[STATE]["profile"]), dumps=_dumps)


def _file(name):
    """Putanja snimka iz imena; None ako ime nije obično ime fajla."""
    if name.endswith(EXT):
        name = name[:-len(EXT)]
    if not NAME_RE.match(name or "") or ".." in name:
        return None
    d = lidarsrc.lidar_dir()
    p = d / (name + EXT)
    return p if p.parent == d else None


async def files_list(request):
    d = lidarsrc.lidar_dir()
    out = []
    for n in lidarsrc.recordings():
        try:
            st = (d / n).stat()
        except OSError:
            continue
        out.append({"name": n, "size": st.st_size, "mtime": int(st.st_mtime)})
    return web.json_response({"files": out})


def _read(path, every, offset):
    meta, scans, total, t0 = None, [], 0, None
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            d = json.loads(line)
            if "meta" in d and meta is None:
                meta = d["meta"]
            if "bins" not in d:
                continue
            if t0 is None:
                t0 = d.get("t", 0)
            total += 1
            if (total - 1) % every or len(scans) >= MAX_SCANS:
                continue
            pts = []
            for a, mm in enumerate(d["bins"][:360]):
                if mm:
                    pts += (a, mm)
            pose = d.get("pose")
            scans.append({"t": d.get("t", 0) - t0, "pts": pts, "hz": d.get("hz"),
                          "near": list(d["near"]) if d.get("near") else None,
                          "pose": list(pose) if isinstance(pose, list) and len(pose) == 3 else None,
                          "o": list(offset)})
    return meta, scans, total


async def file_get(request):
    p = _file(request.match_info["name"])
    if p is None:
        return _bad("neispravno ime snimka lidara")
    if not p.is_file():
        return _bad("nema snimka lidara %s" % p.name, 404)
    try:
        every = max(1, min(MAX_EVERY, int(request.query.get("every") or 1)))
    except ValueError:
        return _bad("every: ceo broj")
    lp = request.app[STATE]["profile"].get("lidar", {}) or {}
    offset = (lp.get("x", 0), lp.get("y", 0), lp.get("z", 300))
    try:
        meta, scans, total = await asyncio.get_running_loop().run_in_executor(None, _read, p, every, offset)
    except (OSError, ValueError, KeyError, EOFError, TypeError, zlib.error) as e:
        return _bad("snimak lidara %s se ne čita: %s" % (p.name, e), 422)
    return web.json_response({"name": p.name, "meta": meta, "total": total, "every": every,
                              "truncated": total > len(scans) * every, "scans": scans}, dumps=_dumps)
