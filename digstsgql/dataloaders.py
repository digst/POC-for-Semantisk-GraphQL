from functools import partial
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from strawberry.dataloader import DataLoader

from digstsgql import db

# # https://github.com/graphql/dataloader?tab=readme-ov-file#using-with-graphql


async def load_organisations(
    session: AsyncSession, keys: list[UUID]
) -> list[db.Organisation | None]:
    """Load Organisation from database."""
    statement = select(db.Organisation).where(db.Organisation.id.in_(keys))
    rows = (await session.scalars(statement)).all()
    results = {r.id: r for r in rows}
    return [results.get(id) for id in keys]


async def load_organisational_units(
    session: AsyncSession, keys: list[UUID]
) -> list[db.Organisationenhed | None]:
    """Load Organisationenhed from database."""
    statement = select(db.Organisationenhed).where(db.Organisationenhed.id.in_(keys))
    rows = (await session.scalars(statement)).all()
    results = {r.id: r for r in rows}
    return [results.get(id) for id in keys]


class Dataloaders:
    """Container for all dataloaders.

    Used to get proper typing when accessing dataloaders in the resolvers
    through the Strawberry context.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.organisations = DataLoader(load_fn=partial(load_organisations, session))
        self.organisational_units = DataLoader(
            load_fn=partial(load_organisational_units, session)
        )
