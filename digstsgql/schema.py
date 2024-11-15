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
        # result = await session.scalars(statement)
        # return [Book(title=r.title, author=r.author) for r in result.all()]
        objects = (await session.scalars(statement)).all()
        return [Book(title=o.title, author=o.author) for o in objects]


@strawberry.type
class Mutation:
    @strawberry.mutation
    async def load_books(self, info: strawberry.Info) -> "str":
        session: AsyncSession = info.context["session"]

        author1 = models.Author(first_name="Foo", last_name="Foosen")
        author2 = models.Author(first_name="Bar", last_name="Barsen")

        book1 = models.Book(title="The Great Gatsby", author=author1)
        book2 = models.Book(title="The Bible", author=author2)

        session.add_all([author1, author2, book1, book2])
        await session.commit()
        return "OK"


schema = strawberry.Schema(query=Query, mutation=Mutation)
