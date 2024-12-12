from sqlalchemy.ext.asyncio import async_sessionmaker
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse
from starlette.responses import PlainTextResponse
from starlette.responses import RedirectResponse
from starlette.responses import Response
from starlette.routing import Route
from starlette.types import ASGIApp
from starlette.types import Receive
from starlette.types import Scope
from starlette.types import Send
from starlette.websockets import WebSocket
from starlette_context.middleware import RawContextMiddleware
from strawberry.asgi import GraphQL
from strawberry.printer import print_schema

from digstsgql import db
from digstsgql.config import Settings
from digstsgql.dataloaders import Dataloaders
from digstsgql.jsonld import context_endpoint
from digstsgql.playground import routes as playground_routes

from .schema import schema


class SessionMiddleware:
    """Start a database session for each HTTP request.

    https://www.starlette.io/middleware/#pure-asgi-middleware.
    """

    def __init__(self, app: ASGIApp, sessionmaker: async_sessionmaker) -> None:
        self.app = app
        self.sessionmaker = sessionmaker

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # Start the single database session for this request, and pass it to
        # Strawberry through the scope dict.
        # https://www.starlette.io/middleware/#passing-information-to-endpoints
        async with self.sessionmaker() as session:
            scope["database_session"] = session
            await self.app(scope, receive, send)


class CustomGraphQL(GraphQL):
    async def get_context(
        self, request: Request | WebSocket, response: Response | WebSocket
    ) -> dict:
        """The Strawberry context is available from resolvers and extensions."""
        session = request.scope["database_session"]
        return {
            "request": request,
            "response": response,
            # A single database session ensures a consistent view across the
            # GraphQL operation. The session is started by the Starlette
            # SessionMiddleware.
            "session": session,
            # Dataloaders cache results throughout their lifetime, so even
            # though they should be shared between multiple resolvers, they
            # should NOT be shared across requests.
            # https://strawberry.rocks/docs/guides/dataloaders#usage-with-context
            # https://github.com/graphql/dataloader?tab=readme-ov-file#creating-a-new-dataloader-per-request
            "dataloaders": Dataloaders(session),
        }

    async def render_graphql_ide(self, request: Request) -> HTMLResponse:
        """Inject JSON-LD Playground button into the GraphiQL IDE."""
        playground_button = """
        <script>
            // setTimeout allows the React components to load
            setTimeout(() => {
                const playgroundButton = `
                    <button type="button" id="playground-button" class="graphiql-un-styled graphiql-toolbar-button" aria-label="Open in JSON-LD Playground" data-state="closed" onclick="playground();">
                        <div class="graphiql-toolbar-icon" style="color: transparent; text-shadow: 0 0 0 hsla(var(--color-neutral), var(--alpha-tertiary)); font-size: 1.5em;">🛝</div>
                    </button>
                `;
                const toolbar = document.querySelector(".graphiql-toolbar");
                toolbar.insertAdjacentHTML("beforeend", playgroundButton);
            });

            function playground() {
                // Get GraphQL query from editor
                const queryEditor = document.querySelector(".CodeMirror").CodeMirror;
                const query = queryEditor.getValue();
                // Minify query
                const minifiedQuery = GraphiQL.GraphQL.stripIgnoredCharacters(query);
                // Construct HTTP GET request URL for the query
                const queryUrl = new URL(window.location.pathname, window.location.origin);
                queryUrl.searchParams.append("query", minifiedQuery);
                // Construct JSON-LD playground with seeded query URL
                // const playgroundUrl = new URL("https://json-ld.org/playground/");
                // See playground.py
                const playgroundUrl = new URL("/json-ld.org/playground/", window.location.origin);
                playgroundUrl.searchParams.append("json-ld", queryUrl.href);
                // Open playground in new tab
                window.open(playgroundUrl.href, "_blank");
            }
        </script>
        """
        html = self.graphql_ide_html
        html = html.replace("</body>", f"{playground_button}</body>")
        return HTMLResponse(html)


def create_app():
    """Create Starlette ASGI app with a Strawberry GraphQL route.

    https://strawberry.rocks/docs/integrations/starlette.
    """
    # Initialise database. See db.run_upgrade() for more information.
    db.run_upgrade(database_metadata=db.Base.metadata)

    settings = Settings()
    sessionmaker = db.create_async_sessionmaker(settings.database.url)

    app = Starlette(
        middleware=[
            Middleware(RawContextMiddleware),
            Middleware(SessionMiddleware, sessionmaker=sessionmaker),
            Middleware(
                # CORS headers describe which origins are permitted to contact the server, and
                # specify which authentication credentials (e.g. cookies or headers) should be
                # sent. CORS is NOT a server-side security mechanism, but relies on the browser
                # itself to enforce it.
                # https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS
                # https://www.starlette.io/middleware/#corsmiddleware
                CORSMiddleware,
                # Allow any website to contact the API
                allow_origins=["*"],
                # Allow the HTTP methods needed by GraphQL
                allow_methods=["HEAD", "GET", "POST"],
                # Allow JavaScript to access the following HTTP headers from requests
                expose_headers=["Link", "Location"],
                # Don't allow the browser to send cookies with the request. Allowing
                # credentials is incompatible with the settings above, as the browser blocks
                # credentialed requests if the server allows wildcard origin, methods, or
                # headers.
                allow_credentials=False,
            ),
        ],
        routes=[
            Route("/", RedirectResponse("/graphql")),
            Route("/graphql", CustomGraphQL(schema)),
            # Schema definition in SDL format
            Route("/graphql/schema.graphql", PlainTextResponse(print_schema(schema))),
            # JSON-LD Context document
            Route(
                "/graphql/contexts/{context:str}.jsonld",
                context_endpoint,
                name="jsonld-context",
            ),
            # Self-hosted JSON-LD playground. See playground.py.
            *playground_routes,
        ],
    )

    return app
