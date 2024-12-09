from functools import partial
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from strawberry.dataloader import DataLoader

from digstsgql import db

# DataLoader pairs nicely well with GraphQL. GraphQL fields are designed to be
# stand-alone functions. Without a caching or batching mechanism, it's easy for
# a naive GraphQL server to issue new database requests each time a field is
# resolved.
# https://github.com/graphql/dataloader?tab=readme-ov-file#using-with-graphql


async def load_companies(
    session: AsyncSession, keys: list[UUID]
) -> list[db.Virksomhed | None]:
    """Load Virksomhed from database."""
    query = select(db.Virksomhed).where(db.Virksomhed.id.in_(keys))
    rows = (await session.scalars(query)).all()
    results = {r.id: r for r in rows}
    return [results.get(id) for id in keys]


async def load_organisational_units(
    session: AsyncSession, keys: list[UUID]
) -> list[db.Organisationenhed | None]:
    """Load Organisationenhed from database."""
    query = select(db.Organisationenhed).where(db.Organisationenhed.id.in_(keys))
    rows = (await session.scalars(query)).all()
    results = {r.id: r for r in rows}
    return [results.get(id) for id in keys]


async def load_organisations(
    session: AsyncSession, keys: list[UUID]
) -> list[db.Organisation | None]:
    """Load Organisation from database."""
    query = select(db.Organisation).where(db.Organisation.id.in_(keys))
    rows = (await session.scalars(query)).all()
    results = {r.id: r for r in rows}
    return [results.get(id) for id in keys]


async def load_public_authorities(
    session: AsyncSession, keys: list[UUID]
) -> list[db.Myndighed | None]:
    """Load Myndighed from database."""
    query = select(db.Myndighed).where(db.Myndighed.id.in_(keys))
    rows = (await session.scalars(query)).all()
    results = {r.id: r for r in rows}
    return [results.get(id) for id in keys]


class Dataloaders:
    """Container for all dataloaders.

    Used to get proper typing when accessing dataloaders in the resolvers
    through the Strawberry context.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.companies = DataLoader(load_fn=partial(load_companies, session))
        self.organisational_units = DataLoader(
            load_fn=partial(load_organisational_units, session)
        )
        self.organisations = DataLoader(load_fn=partial(load_organisations, session))
        self.public_authorities = DataLoader(
            load_fn=partial(load_public_authorities, session)
        )
