from functools import partial

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
from strawberry.dataloader import DataLoader

from digstsgql import dataloaders
from digstsgql import db
from digstsgql.config import Settings

from .schema import schema


class CustomGraphQL(GraphQL):
    async def get_context(
        self, request: Request | WebSocket, response: Response | WebSocket
    ) -> dict:
        """Extend Strawberry context with objects required from resolvers.

        In particular:
          - SQLAlchemy database session.
          - Strawberry dataloaders.
        """
        session = request.scope["session"]
        return {
            "request": request,
            "response": response,
            # A single database session ensures a consistent view across
            # the GraphQL operation.
            "session": session,
            # Dataloaders cache results throughout their lifetime, so even
            # though they should be shared between multiple resolvers, they
            # need to be instantiated per request.
            # https://strawberry.rocks/docs/guides/dataloaders#usage-with-context
            "dataloaders": {
                "authors": DataLoader(
                    load_fn=partial(dataloaders.load_authors, session),
                ),
                "books": DataLoader(
                    load_fn=partial(dataloaders.load_books, session),
                ),
            },
        }


class SessionMiddleware:
    """
    A single database session ensures a consistent view across the GraphQL operation.

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
            scope["session"] = session
            await self.app(scope, receive, send)


def create_app():
    """Create Starlette ASGI app.

    https://strawberry.rocks/docs/integrations/starlette.
    """
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
