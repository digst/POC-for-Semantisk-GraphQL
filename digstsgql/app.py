from starlette.requests import Request
from starlette.responses import Response
from starlette.websockets import WebSocket
from strawberry.asgi import GraphQL
from strawberry_sqlalchemy_mapper import StrawberrySQLAlchemyLoader

from digstsgql import database
from digstsgql.models import Base

from .schema import schema


class CustomGraphQL(GraphQL):
    async def get_context(
        self, request: Request | WebSocket, response: Response | WebSocket
    ) -> dict:
        async with database.Session() as session:
            return {
                "request": request,
                "response": response,
                "session": session,
                "sqlalchemy_loader": StrawberrySQLAlchemyLoader(
                    async_bind_factory=database.Session
                ),
            }


def create_app():
    database.run_upgrade(database_metadata=Base.metadata)

    app = CustomGraphQL(schema)

    return app
