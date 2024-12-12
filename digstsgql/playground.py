import httpx
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Mount
from starlette.routing import Route
from starlette.staticfiles import StaticFiles

# TODO: The JSON-LD playground does not currently support contexts through the
# HTTP Link header. The fix has yet to be merged. Serve fixed version locally.
# https://github.com/json-ld/json-ld.org/pull/851


async def proxy(request: Request) -> Response:
    """Reimplementation of the playground's proxy.php to avoid php."""
    url = request.query_params["url"]
    async with httpx.AsyncClient() as client:
        r = await client.get(url)
    return Response(content=r.content, status_code=r.status_code, headers=r.headers)


routes = [
    # Serve entire JSON-LD repo (cloned in the Dockerfile)
    Mount("/json-ld.org", app=StaticFiles(directory="/json-ld.org", html=True)),
    Route("/playground/proxy.php", proxy),
]
