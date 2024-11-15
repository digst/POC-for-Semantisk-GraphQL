from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from digstsgql import db
from digstsgql import schema


async def load_authors(session: AsyncSession, keys: list[int]) -> list[schema.Author]:
    """Load authors from database and convert to Strawberry GraphQL models."""
    statement = select(db.Author).where(db.Author.id.in_(keys))
    rows = (await session.scalars(statement)).all()
    results = {
        r.id: schema.Author(
            id=r.id,
            first_name=r.first_name,
            last_name=r.last_name,
        )
        for r in rows
    }
    return [results[id] for id in keys]


async def load_books(session: AsyncSession, keys: list[int]) -> list[schema.Book]:
    """Load books from database and convert to Strawberry GraphQL models."""
    statement = select(db.Book).where(db.Book.id.in_(keys))
    rows = (await session.scalars(statement)).all()
    results = {
        r.id: schema.Book(
            id=r.id,
            title=r.title,
            author_id=r.author_id,
        )
        for r in rows
    }
    return [results[id] for id in keys]
