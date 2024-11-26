from sqlalchemy.ext.asyncio import async_sessionmaker
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp
from starlette.types import Receive
from starlette.types import Scope
from starlette.types import Send
from starlette.websockets import WebSocket
from strawberry.asgi import GraphQL

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
        """The Strawberry context is available from the resolvers."""
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

    app = Starlette(
        middleware=[
            Middleware(SessionMiddleware, sessionmaker=sessionmaker),
        ],
    )

    graphql_app = CustomGraphQL(schema)
    app.add_route("/graphql", graphql_app)

    return app
