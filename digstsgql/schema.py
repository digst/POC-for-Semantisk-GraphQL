from typing import Self

import strawberry
from sqlalchemy.ext.asyncio import AsyncSession

from digstsgql import db


@strawberry.type
class Author:
    id: int
    first_name: str
    last_name: str


@strawberry.type
class Book:
    id: int
    title: str

    author_id: strawberry.Private[int]

    @strawberry.field
    async def author(self, root: Self, info: strawberry.Info) -> Author:
        return await info.context["dataloaders"]["authors"].load(root.author_id)


@strawberry.type
class Query:
    @strawberry.field
    async def books(
        self,
        info: strawberry.Info,
        ids: list[int],
    ) -> list[Book]:
        return await info.context["dataloaders"]["books"].load_many(ids)


@strawberry.type
class Mutation:
    @strawberry.mutation
    async def load_books(self, info: strawberry.Info) -> "str":
        session: AsyncSession = info.context["session"]

        author1 = db.Author(first_name="Foo", last_name="Foosen")
        author2 = db.Author(first_name="Bar", last_name="Barsen")

        book1 = db.Book(title="The Great Gatsby", author=author1)
        book2 = db.Book(title="The Bible", author=author2)
        book3 = db.Book(title="CLRS", author=author2)

        session.add_all([author1, author2, book1, book2, book3])
        await session.commit()
        return "OK"


schema = strawberry.Schema(query=Query, mutation=Mutation)
