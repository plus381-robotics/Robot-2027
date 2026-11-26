# Repo kao radni prostor (plan S10).
import asyncio

from aiohttp import web

from .. import profile as profmod
from ._util import STATE


async def _repo_call(fn, *a):
    from .. import repo
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
    from .. import repo
    return await _repo_call(repo.status, request.query.get("fetch") == "1")


async def repo_open(request):
    from .. import repo
    q = await request.json()
    r = await _repo_call(repo.open_repo, q.get("path", ""))
    if r.status == 200:
        _reload_repo(request.app)
    return r


async def repo_clone(request):
    from .. import repo
    q = await request.json()
    r = await _repo_call(repo.clone, q.get("parent", ""))
    if r.status == 200:
        _reload_repo(request.app)
    return r


async def repo_pull(request):
    from .. import repo
    r = await _repo_call(repo.pull)
    _reload_repo(request.app)
    return r


async def repo_save(request):
    from .. import repo
    q = await request.json()
    return await _repo_call(repo.save, q.get("message", ""))
