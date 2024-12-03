from sqlalchemy.ext.asyncio import async_sessionmaker
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
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
            "schema": self.schema,
            # A single database session ensures a consistent view across the
            # GraphQL operation. The session is started by the Starlette
            # SessionMiddleware.
            "session": session,
            # Dataloaders cache results throughout their lifetime, so even
            # though they should be shared between multiple resolvers, they
            # should NOT be shared across requests.
            # https://strawberry.rocks/docs/guides/dataloaders#usage-with-context
            "dataloaders": Dataloaders(session),
        }


def create_app():
    """Create Starlette ASGI app with a Strawberry GraphQL route.

    https://strawberry.rocks/docs/integrations/starlette.
    """
    # Initialise database. See db.run_upgrade() for more information.
    db.run_upgrade(database_metadata=db.Base.metadata)

    settings = Settings()
    sessionmaker = db.create_async_sessionmaker(settings.database.url)

    # TODO: We are not allowed to add a `@context` entry to the response map as
    # per the GraphQL spec:
    # https://spec.graphql.org/draft/#sec-Response-Format
    # Perhaps we could add it as HTTP header?
    # https://www.w3.org/TR/json-ld11/#interpreting-json-as-json-ld

    app = Starlette(
        middleware=[
            Middleware(RawContextMiddleware),
            Middleware(SessionMiddleware, sessionmaker=sessionmaker),
        ],
        routes=[
            Route("/", RedirectResponse("/graphql")),
            Route("/graphql", CustomGraphQL(schema)),
            # Schema definition in SDL format
            Route("/graphql/schema.graphql", PlainTextResponse(print_schema(schema))),
        ],
    )

    return app
