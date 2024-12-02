import itertools
from typing import Any
from typing import Callable
from uuid import UUID

import strawberry
from graphql import GraphQLResolveInfo
from more_itertools import one
from sqlalchemy import select
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from strawberry.extensions import SchemaExtension
from strawberry.schema_directive import Location
from strawberry.utils.await_maybe import AwaitableOrValue
from strawberry.utils.await_maybe import await_maybe

from digstsgql import data
from digstsgql import db
from digstsgql.dataloaders import Dataloaders

# TODO: define if collections are lists or sets


@strawberry.schema_directive(
    # NOTE: Using the directive in a location not defined here silently omits
    # the directive instead of failing loudly.
    locations=[
        Location.FIELD_DEFINITION,
        Location.OBJECT,
    ],
    description="TODO.",
)
class JSONLD:
    """TODO

    https://strawberry.rocks/docs/types/schema-directives.
    """

    type: str  # TODO: URL?


class JSONLDExtension(SchemaExtension):
    async def resolve(
        self,
        _next: Callable,
        root: Any,
        info: GraphQLResolveInfo,
        *args: str,
        **kwargs: Any,
    ) -> AwaitableOrValue[object]:
        value = await await_maybe(_next(root, info, *args, **kwargs))
        # print("===")
        # print("root", root)
        # print("info", info)
        # print("value", value)
        # print(info.field_nodes[0].to_dict())
        # for directive in info.field_nodes[0].directives:
        #     print("DIRECTIVE!!!!!!")
        #     print("directive", directive)
        #
        return value

    def get_results(self) -> dict:
        document = self.execution_context.graphql_document
        if document is None:
            return {}
        # self.execution_context.context["db"] = 2
        return {}


@strawberry.type(description="Language string.")
class LangString:
    lang: str
    value: str


@strawberry.type(
    description="Organisation type.",
    directives=[JSONLD(type="http://www.w3.org/ns/org#classification")],
)
class FormalOrganisationType:
    definition: list[LangString]
    preferred_label: list[LangString]


company_type = FormalOrganisationType(
    definition=[
        LangString(
            lang="en",
            value="A business is an organization that produces and sells goods or services.",
        ),
        LangString(
            lang="da",
            value="En virksomhed er en organisation, der producerer og sælger varer eller tjenester.",
        ),
    ],
    preferred_label=[
        LangString(lang="en", value="Company"),
        LangString(lang="da", value="Virksomhed"),
    ],
)
municipality_type = FormalOrganisationType(
    definition=[
        LangString(
            lang="en",
            value="A municipality is a local administrative unit within a geographically defined area.",
        ),
        LangString(
            lang="da",
            value="En kommune er en lokal administrativ enhed inden for et geografisk afgrænset område.",
        ),
    ],
    preferred_label=[
        LangString(lang="en", value="Municipality"),
        LangString(lang="da", value="Kommune"),
    ],
)
public_authority_type = FormalOrganisationType(
    definition=[
        LangString(
            lang="en",
            value="A public authority is a public administrative unit that has a law enforcement function within the framework of a state, a state, a region or a municipality, and which is not a parliamentary assembly.",
        ),
        LangString(
            lang="da",
            value="En offentlig myndighed er et offentlig forvaltningsenhed, der har en lovudøvende funktion inden for rammerne af en stat, en delstat, en region eller en kommune, og som ikke er en parlamentarisk forsamling.",
        ),
    ],
    preferred_label=[
        LangString(lang="en", value="Public authority"),
        LangString(lang="da", value="Offentlig myndighed"),
    ],
)


@strawberry.type(description="Organisation.")
class FormalOrganisation:
    id: UUID
    user_friendly_key: str | None
    preferred_label: str | None

    company_id: strawberry.Private[UUID | None]
    public_authority_id: strawberry.Private[UUID | None]
    # topenhed_id: strawberry.Private[UUID | None]

    @strawberry.field(description="Organisation's public authority's code.")
    @staticmethod
    async def authority_code(
        root: "FormalOrganisation",
        info: strawberry.Info,
    ) -> str | None:
        if root.public_authority_id is None:
            return None
        dataloaders: Dataloaders = info.context["dataloaders"]
        result = await dataloaders.public_authorities.load(root.public_authority_id)
        if result is None:
            return None
        return result.myndighedskode

    @strawberry.field(description="Organisation's CVR-number.")
    @staticmethod
    async def registered_business_code(
        root: "FormalOrganisation",
        info: strawberry.Info,
    ) -> str | None:
        if root.company_id is None:
            return None
        dataloaders: Dataloaders = info.context["dataloaders"]
        result = await dataloaders.companies.load(root.company_id)
        if result is None:
            return None
        return result.cvr_nummer

    @strawberry.field(description="Organisation's organisational units.")
    @staticmethod
    async def classifications(
        root: "FormalOrganisation",
        info: strawberry.Info,
    ) -> list[FormalOrganisationType]:
        classifications = []

        # The company classification not only requires an associated company,
        # but also that it has a non-null CVR-number.
        if await root.registered_business_code(root=root, info=info):
            classifications.append(company_type)

        # The public authority classification not only requires an associated
        # public authority, but also that it has a non-null authority code.
        if authority_code := await root.authority_code(root=root, info=info):
            classifications.append(public_authority_type)
            if 101 <= int(authority_code) <= 860:
                classifications.append(municipality_type)

        return classifications

    @strawberry.field(description="Organisation's organisational units.")
    @staticmethod
    async def organisational_units(
        root: "FormalOrganisation",
        info: strawberry.Info,
    ) -> list["OrganisationalUnit"]:
        session: AsyncSession = info.context["session"]
        query = select(db.Organisationenhed.id).where(
            db.Organisationenhed.organisation_id == root.id
        )
        ids = list((await session.scalars(query)).all())
        return await get_organisational_units(info=info, ids=ids)


@strawberry.type(description="Organisational unit.")
class OrganisationalUnit:
    id: UUID
    user_friendly_key: str | None
    preferred_label: str | None

    organisation_id: strawberry.Private[UUID | None]
    parent_id: strawberry.Private[UUID | None]

    @strawberry.field(description="Unit's children units.")
    @staticmethod
    async def children(
        root: "OrganisationalUnit",
        info: strawberry.Info,
    ) -> list["OrganisationalUnit"]:
        session: AsyncSession = info.context["session"]
        query = select(db.Organisationenhed.id).where(
            db.Organisationenhed.overordnetenhed_id == root.id
        )
        ids = list((await session.scalars(query)).all())
        return await get_organisational_units(info=info, ids=ids)

    @strawberry.field(description="Unit's formal organisation.")
    @staticmethod
    async def organisation(
        root: "OrganisationalUnit",
        info: strawberry.Info,
    ) -> FormalOrganisation | None:
        if root.organisation_id is None:
            return None
        return one(await get_organisations(info=info, ids=[root.organisation_id]))

    @strawberry.field(description="Unit's parent unit.")
    @staticmethod
    async def parent(
        root: "OrganisationalUnit",
        info: strawberry.Info,
    ) -> "OrganisationalUnit | None":
        if root.parent_id is None:
            return None
        return one(await get_organisational_units(info=info, ids=[root.parent_id]))


async def get_organisations(
    info: strawberry.Info,
    ids: list[UUID] | None = None,
    preferred_labels: list[str] | None = None,
    registered_business_codes: list[str] | None = None,
    public_authority_codes: list[str] | None = None,
) -> list[FormalOrganisation]:
    # Filter
    query = select(db.Organisation.id)
    if ids is not None:
        query = query.where(db.Organisation.id.in_(ids))
    if preferred_labels is not None:
        query = query.where(db.Organisation.organisationsnavn.in_(preferred_labels))
    if registered_business_codes is not None:
        query = query.where(
            db.Organisation.virksomhed_id.in_(
                select(db.Virksomhed.id).where(
                    db.Virksomhed.cvr_nummer.in_(registered_business_codes)
                )
            )
        )
    if public_authority_codes is not None:
        query = query.where(
            db.Organisation.myndighed_id.in_(
                select(db.Myndighed.id).where(
                    db.Myndighed.myndighedskode.in_(public_authority_codes)
                )
            )
        )
    session: AsyncSession = info.context["session"]
    ids = list((await session.scalars(query)).all())

    # Fetch selected IDs from database (through dataloader)
    dataloaders: Dataloaders = info.context["dataloaders"]
    results = await dataloaders.organisations.load_many(ids)
    # Convert database objects to GraphQL types
    return [
        FormalOrganisation(
            id=r.id,
            user_friendly_key=r.brugervendtnoegle,
            preferred_label=r.organisationsnavn,
            company_id=r.virksomhed_id,
            public_authority_id=r.myndighed_id,
        )
        for r in results
        if r is not None
    ]


async def get_organisational_units(
    info: strawberry.Info,
    ids: list[UUID] | None = None,
    preferred_labels: list[str] | None = None,
) -> list[OrganisationalUnit]:
    # Filter
    query = select(db.Organisationenhed.id)
    if ids is not None:
        query = query.where(db.Organisationenhed.id.in_(ids))
    if preferred_labels is not None:
        query = query.where(db.Organisationenhed.enhedsnavn.in_(preferred_labels))
    session: AsyncSession = info.context["session"]
    ids = list((await session.scalars(query)).all())

    # Fetch selected IDs from database (through dataloader)
    dataloaders: Dataloaders = info.context["dataloaders"]
    results = await dataloaders.organisational_units.load_many(ids)
    # Convert database objects to GraphQL types
    return [
        OrganisationalUnit(
            id=r.id,
            user_friendly_key=r.brugervendtnoegle,
            preferred_label=r.enhedsnavn,
            organisation_id=r.organisation_id,
            parent_id=r.overordnetenhed_id,
        )
        for r in results
        if r is not None
    ]


@strawberry.type
class Query:
    organisational_units: list[OrganisationalUnit] = strawberry.field(
        resolver=get_organisational_units,
        description="Get organisational units.",
    )
    organisations: list[FormalOrganisation] = strawberry.field(
        resolver=get_organisations,
        description="Get organisations.",
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
                data.myndighed(),
                data.organisation(),
                data.organisationenhed(),
                data.virksomhed(),
            )
        )
        await session.commit()
        return "OK"


schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    extensions=[JSONLDExtension],
)
