import strawberry
from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession
from strawberry_sqlalchemy_mapper import StrawberrySQLAlchemyMapper

from digstsgql import models

strawberry_sqlalchemy_mapper = StrawberrySQLAlchemyMapper()


@strawberry_sqlalchemy_mapper.type(models.Book)
class Book:
    pass


@strawberry.type
class Query:
    @strawberry.field
    async def books(self, info: strawberry.Info) -> list[Book]:
        session: AsyncSession = info.context["session"]
        result = await session.scalars(Select(models.Book))
        return result.all()


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


strawberry_sqlalchemy_mapper.finalize()
schema = strawberry.Schema(query=Query, mutation=Mutation)
