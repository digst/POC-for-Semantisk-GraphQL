from functools import partial

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response
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
        async with request.app.state.Session() as session:
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
                        load_fn=partial(dataloaders.load_authors, session)
                    ),
                    "books": DataLoader(
                        load_fn=partial(dataloaders.load_books, session)
                    ),
                },
            }


def create_app():
    """Create Starlette ASGI app.

    https://strawberry.rocks/docs/integrations/starlette.
    """
    db.run_upgrade(database_metadata=db.Base.metadata)

    app = Starlette()

    # https://www.starlette.io/applications/#storing-state-on-the-app-instance
    settings = Settings()
    app.state.settings = settings
    app.state.Session = db.create_async_sessionmaker(settings.database.url)

    graphql_app = CustomGraphQL(schema)
    app.add_route("/graphql", graphql_app)

    return app
