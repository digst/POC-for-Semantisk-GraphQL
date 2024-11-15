from functools import partial

from starlette.requests import Request
from starlette.responses import Response
from starlette.websockets import WebSocket
from strawberry.asgi import GraphQL
from strawberry.dataloader import DataLoader

from digstsgql import dataloaders
from digstsgql import db

from .schema import schema


class CustomGraphQL(GraphQL):
    """https://strawberry.rocks/docs/integrations/asgi"""

    async def get_context(
        self, request: Request | WebSocket, response: Response | WebSocket
    ) -> dict:
        async with db.Session() as session:
            return {
                "request": request,
                "response": response,
                "session": session,
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
    db.run_upgrade(database_metadata=db.Base.metadata)

    app = CustomGraphQL(schema)

    return app
