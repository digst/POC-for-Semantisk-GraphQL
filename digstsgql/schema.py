import strawberry
from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession

from digstsgql import models


@strawberry.type
class Book:
    title: str
    author: str


@strawberry.type
class Query:
    @strawberry.field
    async def books(self, info: strawberry.Info) -> list[Book]:
        session: AsyncSession = info.context["session"]
        statement = Select(models.Book)
        objects = (await session.scalars(statement)).all()
        return [Book(title=o.title, author=o.author) for o in objects]


@strawberry.type
class Mutation:
    @strawberry.mutation
    async def add_books(self, info: strawberry.Info) -> "str":
        session: AsyncSession = info.context["session"]
        session.add_all(
            [
                models.Book(title="The Great Gatsby", author="F. Scott Fitzgerald"),
            ]
        )
        await session.commit()
        return "OK"


schema = strawberry.Schema(query=Query, mutation=Mutation)
