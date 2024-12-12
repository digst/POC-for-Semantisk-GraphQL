import itertools
from typing import Annotated
from typing import Any
from uuid import UUID

import strawberry
from more_itertools import one
from sqlalchemy import false
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette_context import context as starlette_context
from strawberry import UNSET
from strawberry.types import ExecutionContext

from digstsgql import data
from digstsgql import db
from digstsgql.dataloaders import Dataloaders
from digstsgql.jsonld import JSONLD
from digstsgql.jsonld import JSONLDExtension


@strawberry.type(
    description="Language-tagged string value.",
    directives=[JSONLD(id="http://www.w3.org/1999/02/22-rdf-syntax-ns#langString")],
)
class LangString:
    lang: str | None = strawberry.field(description="Language tag.")
    string: str = strawberry.field(description="Literal.")


@strawberry.type(
    description="Organisation type.",
    directives=[
        JSONLD(
            id="https://data.gov.dk/concept/model/formalorganizationtype/FormalOrganizationType",
            type="@id",
        )
    ],
)
class FormalOrganisationType:
    type: str = strawberry.field(
        name="_type",
        default="https://data.gov.dk/model/core/organisation/extension/FormalOrganizationType",
        directives=[JSONLD(id="@type")],
    )
    id: strawberry.ID = strawberry.field(name="_id", directives=[JSONLD(id="@id")])

    definitions: strawberry.Private[list[LangString]]
    preferred_labels: strawberry.Private[list[LangString]]
    broader: "FormalOrganisationType | None" = strawberry.field(
        directives=[JSONLD(id="http://www.w3.org/2004/02/skos/core#broader")],
    )
    narrower: list["FormalOrganisationType"] = strawberry.field(
        default_factory=list,
        directives=[JSONLD(id="http://www.w3.org/2004/02/skos/core#narrower")],
    )

    def __post_init__(self) -> None:
        # Set double-linked relationship
        if self.broader is not None:
            self.broader.narrower.append(self)

    @strawberry.field(
        description="Definition.",
        directives=[
            JSONLD(
                id="http://www.w3.org/2004/02/skos/core#definition", container="@set"
            )
        ],
    )
    @staticmethod
    async def definition(
        root: "FormalOrganisationType",
        languages: list[str | None] | None = UNSET,
    ) -> list[LangString]:
        if not languages:
            return root.definitions
        return [x for x in root.definitions if x.lang in languages]

    @strawberry.field(
        description="Preferred label.",
        directives=[
            JSONLD(
                id="http://www.w3.org/2004/02/skos/core#prefLabel", container="@set"
            ),
        ],
    )
    @staticmethod
    async def preferred_label(
        root: "FormalOrganisationType",
        languages: list[str | None] | None = UNSET,
    ) -> list[LangString]:
        if not languages:
            return root.preferred_labels
        return [x for x in root.preferred_labels if x.lang in languages]


company_type = FormalOrganisationType(
    id=strawberry.ID(
        "https://data.gov.dk/concept/model/formalorganizationtype/Company"
    ),
    definitions=[
        LangString(
            lang="en",
            string="A business is an organization that produces and sells goods or services.",
        ),
        LangString(
            lang="da",
            string="En virksomhed er en organisation, der producerer og sælger varer eller tjenester.",
        ),
    ],
    preferred_labels=[
        LangString(lang="en", string="Company"),
        LangString(lang="da", string="Virksomhed"),
    ],
    broader=None,
)
public_authority_type = FormalOrganisationType(
    id=strawberry.ID(
        "https://data.gov.dk/concept/model/formalorganizationtype/PublicAuthority"
    ),
    definitions=[
        LangString(
            lang="en",
            string="A public authority is a public administrative unit that has a law enforcement function within the framework of a state, a state, a region or a municipality, and which is not a parliamentary assembly.",
        ),
        LangString(
            lang="da",
            string="En offentlig myndighed er et offentlig forvaltningsenhed, der har en lovudøvende funktion inden for rammerne af en stat, en delstat, en region eller en kommune, og som ikke er en parlamentarisk forsamling.",
        ),
    ],
    preferred_labels=[
        LangString(lang="en", string="Public authority"),
        LangString(lang="da", string="Offentlig myndighed"),
    ],
    broader=None,
)
governmental_authority_type = FormalOrganisationType(
    id=strawberry.ID(
        "https://data.gov.dk/concept/model/formalorganizationtype/GovernmentalAuthority"
    ),
    definitions=[
        LangString(
            lang="en",
            string="Governmental administrative unit that administers legislation or administration of a particular area.",
        ),
        LangString(
            lang="da",
            string="Statslig forvaltningsenhed, som administrerer lovgivning eller forvaltning af et bestemt område.",
        ),
    ],
    preferred_labels=[
        LangString(lang="en", string="Governmental authority"),
        LangString(lang="da", string="Statslig myndighed"),
    ],
    broader=public_authority_type,
)
municipality_type = FormalOrganisationType(
    id=strawberry.ID(
        "https://data.gov.dk/concept/model/formalorganizationtype/Municipality"
    ),
    definitions=[
        LangString(
            lang="en",
            string="A municipality is a local administrative unit within a geographically defined area.",
        ),
        LangString(
            lang="da",
            string="En kommune er en lokal administrativ enhed inden for et geografisk afgrænset område.",
        ),
    ],
    preferred_labels=[
        LangString(lang="en", string="Municipality"),
        LangString(lang="da", string="Kommune"),
    ],
    broader=public_authority_type,
)


@strawberry.type(
    description="Organisation.",
    directives=[JSONLD(id="http://www.w3.org/ns/org#FormalOrganization", type="@id")],
)
class FormalOrganisation:
    type: str = strawberry.field(
        name="_type",
        default="http://www.w3.org/ns/org#FormalOrganization",
        directives=[JSONLD(id="@type")],
    )

    local_identifier: UUID = strawberry.field(
        graphql_type=strawberry.ID,
        directives=[
            JSONLD(
                id="https://data.gov.dk/model/core/organisation/extension/localIdentifier"
            )
        ],
    )
    user_friendly_key: str | None = strawberry.field(
        directives=[
            JSONLD(
                id="https://data.gov.dk/model/core/organisation/extension/userFriendlyKey"
            )
        ],
    )
    preferred_label: str | None = strawberry.field(
        directives=[JSONLD(id="http://www.w3.org/2004/02/skos/core#prefLabel")],
    )

    company_id: strawberry.Private[UUID | None]
    public_authority_id: strawberry.Private[UUID | None]
    # topenhed_id: strawberry.Private[UUID | None]

    @strawberry.field(
        name="_id", description="Object's ID.", directives=[JSONLD(id="@id")]
    )
    async def id(root: "FormalOrganisation") -> strawberry.ID:
        return strawberry.ID(f"https://data.gov.dk/TODO/{root.local_identifier}")

    @strawberry.field(
        description="Organisation's public authority's code.",
        directives=[
            JSONLD(
                id="https://data.gov.dk/model/core/organisation/extension/authorityCode"
            )
        ],
    )
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

    @strawberry.field(
        description="Organisation's CVR-number.",
        directives=[
            JSONLD(
                id="https://data.gov.dk/model/core/organisation/extension/registeredBusinessCode"
            )
        ],
    )
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

    @strawberry.field(
        description="Organisation's classifications.",
        directives=[
            JSONLD(
                id="http://www.w3.org/ns/org#classification",
                type="@id",
                container="@set",
            )
        ],
    )
    @staticmethod
    async def classification(
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

    @strawberry.field(
        name="hasUnit",  # 🤷
        description=(
            "Organisation's organisational units.\n\n"
            "NOTE: The list will be empty if the organisation does not have any organisational units."
        ),
        directives=[
            JSONLD(
                id="https://data.gov.dk/model/core/organisation/extension/hasUpperUnit",
                type="@id",
                container="@set",
            )
        ],
    )
    @staticmethod
    async def organisational_units(
        root: "FormalOrganisation",
        info: strawberry.Info,
    ) -> list["OrganisationalUnit"]:
        session: AsyncSession = info.context["session"]
        query = select(db.Organisationenhed.id).where(
            db.Organisationenhed.organisation_id == root.local_identifier
        )
        uuids = list((await session.scalars(query)).all())
        return await get_organisational_units(info=info, local_identifiers=uuids)


@strawberry.type(
    description="Organisational unit.",
    directives=[JSONLD(id="http://www.w3.org/ns/org#OrganizationalUnit", type="@id")],
)
class OrganisationalUnit:
    type: str = strawberry.field(
        name="_type",
        default="http://www.w3.org/ns/org#OrganizationalUnit",
        directives=[JSONLD(id="@type")],
    )

    local_identifier: UUID = strawberry.field(
        graphql_type=strawberry.ID,
        directives=[
            JSONLD(
                id="https://data.gov.dk/model/core/organisation/extension/localIdentifier"
            )
        ],
    )
    user_friendly_key: str | None = strawberry.field(
        directives=[
            JSONLD(
                id="https://data.gov.dk/model/core/organisation/extension/userFriendlyKey"
            )
        ],
    )
    preferred_label: str | None = strawberry.field(
        directives=[JSONLD(id="http://www.w3.org/2004/02/skos/core#prefLabel")],
    )

    organisation_id: strawberry.Private[UUID | None]
    parent_id: strawberry.Private[UUID | None]

    @strawberry.field(
        name="_id", description="Object's ID.", directives=[JSONLD(id="@id")]
    )
    async def id(root: "OrganisationalUnit") -> strawberry.ID:
        return strawberry.ID(f"https://data.gov.dk/TODO/{root.local_identifier}")

    @strawberry.field(
        name="hasSubUnit",  # 🤷
        description=(
            "Unit's subunits.\n\n"
            "NOTE: The list will be empty if the unit does not have any subunits."
        ),
        directives=[
            JSONLD(id="http://www.w3.org/ns/org#hasUnit", type="@id", container="@set")
        ],
    )
    @staticmethod
    async def children(
        root: "OrganisationalUnit",
        info: strawberry.Info,
    ) -> list["OrganisationalUnit"]:
        session: AsyncSession = info.context["session"]
        query = select(db.Organisationenhed.id).where(
            db.Organisationenhed.overordnetenhed_id == root.local_identifier
        )
        uuids = list((await session.scalars(query)).all())
        return await get_organisational_units(info=info, local_identifiers=uuids)

    @strawberry.field(
        name="unitOf",  # 🤷
        description="Unit's formal organisation.",
        directives=[JSONLD(id="http://www.w3.org/ns/org#unitOf", type="@id")],
    )
    @staticmethod
    async def organisation(
        root: "OrganisationalUnit",
        info: strawberry.Info,
    ) -> FormalOrganisation | None:
        if root.organisation_id is None:
            return None
        return one(
            await get_organisations(
                info=info,
                local_identifiers=[root.organisation_id],
            )
        )

    @strawberry.field(
        name="subUnitOf",  # 🤷
        description="Unit's parent unit.",
        directives=[JSONLD(id="http://www.w3.org/ns/org#unitOf", type="@id")],
    )
    @staticmethod
    async def parent(
        root: "OrganisationalUnit",
        info: strawberry.Info,
    ) -> "OrganisationalUnit | None":
        if root.parent_id is None:
            return None
        return one(
            await get_organisational_units(
                info=info,
                local_identifiers=[root.parent_id],
            )
        )


async def get_organisations(
    info: strawberry.Info,
    local_identifiers: Annotated[
        list[UUID] | None,
        strawberry.argument(
            description="Limit returned organisations to those with the given `localIdentifier`."
        ),
    ] = UNSET,
    preferred_labels: Annotated[
        list[str] | None,
        strawberry.argument(
            description="Limit returned organisations to those with the given `preferredLabel`."
        ),
    ] = UNSET,
    registered_business_codes: Annotated[
        list[str | None] | None,
        strawberry.argument(
            description="Limit returned organisations to those with the given `registeredBusinessCode`."
        ),
    ] = UNSET,
    authority_codes: Annotated[
        list[str | None] | None,
        strawberry.argument(
            description="Limit returned organisations to those with the given `authorityCode`."
        ),
    ] = UNSET,
) -> list[FormalOrganisation]:
    """Organisation resolver."""
    # Filter
    query = select(db.Organisation.id)
    if local_identifiers is not None and local_identifiers is not UNSET:
        query = query.where(db.Organisation.id.in_(local_identifiers))
    if preferred_labels is not None and preferred_labels is not UNSET:
        query = query.where(db.Organisation.organisationsnavn.in_(preferred_labels))
    if registered_business_codes is not None and registered_business_codes is not UNSET:
        query = query.where(
            or_(
                db.Organisation.virksomhed_id.in_(
                    select(db.Virksomhed.id).where(
                        db.Virksomhed.cvr_nummer.in_(registered_business_codes)
                    )
                ),
                # NULL cannot be filtered using a WHERE IN clause
                db.Organisation.virksomhed_id.is_(None)
                if None in registered_business_codes
                else false(),
            )
        )
    if authority_codes is not None and authority_codes is not UNSET:
        query = query.where(
            or_(
                db.Organisation.myndighed_id.in_(
                    select(db.Myndighed.id).where(
                        db.Myndighed.myndighedskode.in_(authority_codes)
                    )
                ),
                # NULL cannot be filtered using a WHERE IN clause
                db.Organisation.virksomhed_id.is_(None)
                if None in authority_codes
                else false(),
            )
        )
    session: AsyncSession = info.context["session"]
    uuids = list((await session.scalars(query)).all())

    # Fetch selected IDs from database (through dataloader)
    dataloaders: Dataloaders = info.context["dataloaders"]
    results = await dataloaders.organisations.load_many(uuids)
    # Convert database objects to GraphQL types
    return [
        FormalOrganisation(
            local_identifier=r.id,
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
    local_identifiers: Annotated[
        list[UUID] | None,
        strawberry.argument(
            description="Limit returned organisational units to those with the given `localIdentifier`."
        ),
    ] = UNSET,
    preferred_labels: Annotated[
        list[str] | None,
        strawberry.argument(
            description="Limit returned organisational units to those with the given `preferredLabel`."
        ),
    ] = UNSET,
) -> list[OrganisationalUnit]:
    """Organisational Unit resolver."""
    # Filter
    query = select(db.Organisationenhed.id)
    if local_identifiers is not None and local_identifiers is not UNSET:
        query = query.where(db.Organisationenhed.id.in_(local_identifiers))
    if preferred_labels is not None and preferred_labels is not UNSET:
        query = query.where(db.Organisationenhed.enhedsnavn.in_(preferred_labels))
    session: AsyncSession = info.context["session"]
    uuids = list((await session.scalars(query)).all())

    # Fetch selected IDs from database (through dataloader)
    dataloaders: Dataloaders = info.context["dataloaders"]
    results = await dataloaders.organisational_units.load_many(uuids)
    # Convert database objects to GraphQL types
    return [
        OrganisationalUnit(
            local_identifier=r.id,
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
    """The entrypoint for read operations."""

    organisational_units: list[OrganisationalUnit] = strawberry.field(
        resolver=get_organisational_units,
        description="Get organisational units.",
        directives=[
            JSONLD(
                id="http://www.w3.org/ns/org#OrganizationalUnit",
                container="@set",
            )
        ],
    )
    organisations: list[FormalOrganisation] = strawberry.field(
        resolver=get_organisations,
        description="Get organisations.",
        directives=[
            JSONLD(
                id="http://www.w3.org/ns/org#FormalOrganization",
                container="@set",
            )
        ],
    )


@strawberry.type
class Mutation:
    """The entrypoint for write operations."""

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


class CustomSchema(strawberry.Schema):
    def _create_execution_context(self, *args: Any, **kwargs: Any) -> ExecutionContext:
        # HACK: We cannot use self.execution_context in the extensions due to a
        # bug in Strawberry. This private method is called internally in
        # Strawberry whenever the execution context is built, so we can use it
        # to inject the created context into the request-scoped
        # starlette-context, which can be properly accessed from the extension
        # around the Strawberry framework.
        # https://github.com/strawberry-graphql/strawberry/issues/3571
        execution_context = super()._create_execution_context(*args, **kwargs)
        starlette_context["execution_context"] = execution_context
        return execution_context


schema = CustomSchema(
    query=Query,
    mutation=Mutation,
    extensions=[JSONLDExtension],
)
