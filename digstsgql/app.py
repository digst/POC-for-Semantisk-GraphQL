from strawberry.asgi import GraphQL

from .schema import schema


def create_app():
    app = GraphQL(schema)
    return app
