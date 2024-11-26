import itertools
from uuid import UUID

import strawberry
from more_itertools import only
from sqlalchemy import select
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from digstsgql import data
from digstsgql import db
from digstsgql.dataloaders import Dataloaders


@strawberry.type(description="Organisation.")
class Organisation:
    id: UUID
    user_key: str | None
    name: str | None

    @strawberry.field(description="Organisation's organisational units.")
    @staticmethod
    async def organisational_units(
        root: "OrganisationalUnit",
        info: strawberry.Info,
    ) -> list["OrganisationalUnit"]:
        # Select organisational units with this organisation
        session: AsyncSession = info.context["session"]
        statement = select(db.Organisationenhed.id).where(
            db.Organisationenhed.organisation_id == root.id
        )
        ids = list((await session.scalars(statement)).all())
        return await get_organisational_units(info=info, ids=ids)


@strawberry.type(description="Organisational unit.")
class OrganisationalUnit:
    id: UUID
    user_key: str | None
    name: str | None

    organisation_id: strawberry.Private[UUID | None]
    parent_id: strawberry.Private[UUID | None]

    @strawberry.field(description="Unit's organisation.")
    @staticmethod
    async def organisation(
        root: "OrganisationalUnit",
        info: strawberry.Info,
    ) -> Organisation | None:
        if root.organisation_id is None:
            return None
        return only(await get_organisations(info=info, ids=[root.organisation_id]))

    @strawberry.field(description="Unit's parent unit.")
    @staticmethod
    async def parent(
        root: "OrganisationalUnit",
        info: strawberry.Info,
    ) -> "OrganisationalUnit | None":
        if root.parent_id is None:
            return None
        return only(await get_organisational_units(info=info, ids=[root.parent_id]))

    @strawberry.field(description="Unit's children units.")
    @staticmethod
    async def children(
        root: "OrganisationalUnit",
        info: strawberry.Info,
    ) -> list["OrganisationalUnit"]:
        # Select organisational units which have this unit as parent
        session: AsyncSession = info.context["session"]
        statement = select(db.Organisationenhed.id).where(
            db.Organisationenhed.overordnetenhed_id == root.id
        )
        ids = list((await session.scalars(statement)).all())
        return await get_organisational_units(info=info, ids=ids)


async def get_organisations(
    info: strawberry.Info,
    ids: list[UUID] | None = None,
) -> list[Organisation]:
    # Select all organisations if no filter is applied
    if ids is None:
        session: AsyncSession = info.context["session"]
        statement = select(db.Organisation.id)
        ids = list((await session.scalars(statement)).all())

    # Fetch selected IDs from database (through dataloader)
    dataloaders: Dataloaders = info.context["dataloaders"]
    results = await dataloaders.organisations.load_many(ids)
    # Convert database objects to GraphQL types
    return [
        Organisation(
            id=r.id,
            user_key=r.brugervendtnoegle,
            name=r.organisationsnavn,
        )
        for r in results
        if r is not None
    ]


async def get_organisational_units(
    info: strawberry.Info,
    ids: list[UUID] | None = None,
) -> list[OrganisationalUnit]:
    # Select all organisational units if no filter is applied
    if ids is None:
        session: AsyncSession = info.context["session"]
        statement = select(db.Organisationenhed.id)
        ids = list((await session.scalars(statement)).all())

    # Fetch selected IDs from database (through dataloader)
    dataloaders: Dataloaders = info.context["dataloaders"]
    results = await dataloaders.organisational_units.load_many(ids)
    # Convert database objects to GraphQL types
    return [
        OrganisationalUnit(
            id=r.id,
            user_key=r.brugervendtnoegle,
            name=r.enhedsnavn,
            organisation_id=r.organisation_id,
            parent_id=r.overordnetenhed_id,
        )
        for r in results
        if r is not None
    ]


@strawberry.type
class Query:
    organisations: list[Organisation] = strawberry.field(
        resolver=get_organisations,
        description="Get organisations.",
    )
    organisational_units: list[OrganisationalUnit] = strawberry.field(
        resolver=get_organisational_units,
        description="Get organisational units.",
    )


@strawberry.type
class Mutation:
    @strawberry.mutation(
        description="Load fixture-data into database.",
    )
    async def load_data(self, info: strawberry.Info) -> "str":
        session: AsyncSession = info.context["session"]
        # Truncate existing data
        await session.execute(
            text("TRUNCATE {};".format(",".join(db.Base.metadata.tables)))
        )
        # Load data anew
        session.add_all(
            itertools.chain(
                data.organisation(),
                data.organisationenhed(),
            )
        )
        await session.commit()
        return "OK"


schema = strawberry.Schema(query=Query, mutation=Mutation)
