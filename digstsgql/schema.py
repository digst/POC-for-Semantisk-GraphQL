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
from starlette_context import context as starlette_context
from strawberry.extensions import SchemaExtension
from strawberry.schema_directive import Location
from strawberry.utils.await_maybe import AsyncIteratorOrIterator
from strawberry.utils.await_maybe import AwaitableOrValue
from strawberry.utils.await_maybe import await_maybe

from digstsgql import data
from digstsgql import db
from digstsgql.dataloaders import Dataloaders


@strawberry.schema_directive(
    # NOTE: Using the directive in a location not defined here silently omits
    # the directive instead of failing loudly.
    locations=[
        Location.FIELD_DEFINITION,
        Location.OBJECT,
    ],
    # Force lowercase to avoid auto-camelCasing to "jSONLD"
    name="jsonld",
    description="JSON-LD term.",
)
class JSONLD:
    """JSON-LD Expanded term definition.

    https://www.w3.org/TR/json-ld/#expanded-term-definition.
    https://strawberry.rocks/docs/types/schema-directives.
    """

    id: str
    type: str | None = None
    container: str | None = None

    def as_dict(self) -> dict[str, str]:
        """Convert to JSON-LD @context dict."""
        res = {
            "@id": self.id,
        }
        if self.type is not None:
            res["@type"] = self.type
        if self.container is not None:
            res["@container"] = self.container
        return res


class JSONLDExtension(SchemaExtension):
    """Strawberry extension which adds JSON-LD context as a GraphQL extension.

    https://www.w3.org/TR/json-ld/#scoped-contexts
    https://www.w3.org/TR/json-ld/#context-definitions
    https://www.w3.org/TR/json-ld/#keywords
    """

    def on_execute(self) -> AsyncIteratorOrIterator[None]:  # type: ignore
        """Instantiate empty JSON-LD context on every GraphQL execution."""
        # NOTE: We cannot use self.execution_context due to a bug in
        # Strawberry, so we use request-scoped starlette-context instead.
        # https://github.com/strawberry-graphql/strawberry/issues/3571
        starlette_context["jsonld_context"] = {}
        yield

    def _add_to_context(self, info: GraphQLResolveInfo) -> None:
        """Add resolved field to the JSON-LD context."""
        # `info.field_name` and `info.parent_type` is the actual field and type
        # in the *schema*. We use these to fetch the JSONLD directive object.
        field = schema.get_field_for_type(info.field_name, info.parent_type.name)
        if field is None:
            # Introspection queries fetch the `__schema` field which is not
            # part of our schema: ignore.
            return
        for directive in field.directives:
            if isinstance(directive, JSONLD):
                field_context = directive
                break
        else:
            # Set field as an opaque JSON blob if the field does not have a
            # JSONLD directive.
            # https://www.w3.org/TR/json-ld/#json-literals
            field_context = JSONLD(
                id="http://www.w3.org/1999/02/22-rdf-syntax-ns#JSON",
                type="@json",
            )

        # `info.path` `key`s are the fields in the *query*, i.e. potentially an
        # alias. We use these to find where to insert in the JSON-LD @context.
        # For lists, the path key will be an integer index. We ignore these
        # since they do not contribute a level in the JSON-LD context;
        # Collections are typed through @container on the field instead.
        *ancestors, node = info.path.as_list()
        ancestors = [k for k in ancestors if not isinstance(k, int)]
        assert not isinstance(node, int)

        # Walk context to find the parent node. All ancestors are guaranteed to
        # exist in the context because GraphQL is resolved in a breadth-first
        # manner.
        context: dict = starlette_context["jsonld_context"]
        for ancestor in ancestors:
            context = context["@context"][ancestor]

        # Add this node to the parent's context, creating it if this is the
        # first child.
        context = context.setdefault("@context", {})
        context[node] = field_context.as_dict()

    async def resolve(
        self,
        _next: Callable,
        root: Any,
        info: GraphQLResolveInfo,
        *args: str,
        **kwargs: Any,
    ) -> AwaitableOrValue[object]:
        """Called for every resolver."""
        self._add_to_context(info)
        return await await_maybe(_next(root, info, *args, **kwargs))

    def get_results(self) -> dict:
        """Return JSON-LD context as a GraphQL extension under the `@context` key."""
        # A GraphQL response is always nested under the `data` key. The GraphQL
        # Query root is not part of the path in Strawberry, so it was ignored
        # when building the JSON-LD context dict above. Therefore, everything
        # is correct when the built context is nested under `data`.
        return {
            "@context": {
                "data": {
                    "@id": "https://example.org/#TODO",
                    **starlette_context["jsonld_context"],
                },
            },
        }


@strawberry.type(
    description="Language-tagged string value.",
)
class LangString:
    lang: str = strawberry.field(description="Language tag.")
    value: str = strawberry.field(description="Literal.")


@strawberry.type(
    description="Organisation type.",
    directives=[
        JSONLD(
            id="https://data.gov.dk/model/core/organisation/extension/FormalOrganizationType",
            type="@id",
        )
    ],
)
class FormalOrganisationType:
    definitions: strawberry.Private[list[LangString]]
    preferred_labels: strawberry.Private[list[LangString]]

    @strawberry.field(
        description="Definition.",
        directives=[JSONLD(id="http://www.w3.org/2004/02/skos/core#definition")],
    )
    @staticmethod
    async def definition(
        root: "FormalOrganisationType",
        languages: list[str] | None = None,
    ) -> list[LangString]:
        if languages is None:
            return root.definitions
        return [x for x in root.definitions if x.lang in languages]

    @strawberry.field(
        description="Preferred label.",
        directives=[JSONLD(id="http://www.w3.org/2004/02/skos/core#prefLabel")],
    )
    @staticmethod
    async def preferred_label(
        root: "FormalOrganisationType",
        languages: list[str] | None = None,
    ) -> list[LangString]:
        if languages is None:
            return root.preferred_labels
        return [x for x in root.preferred_labels if x.lang in languages]


company_type = FormalOrganisationType(
    definitions=[
        LangString(
            lang="en",
            value="A business is an organization that produces and sells goods or services.",
        ),
        LangString(
            lang="da",
            value="En virksomhed er en organisation, der producerer og sælger varer eller tjenester.",
        ),
    ],
    preferred_labels=[
        LangString(lang="en", value="Company"),
        LangString(lang="da", value="Virksomhed"),
    ],
)
municipality_type = FormalOrganisationType(
    definitions=[
        LangString(
            lang="en",
            value="A municipality is a local administrative unit within a geographically defined area.",
        ),
        LangString(
            lang="da",
            value="En kommune er en lokal administrativ enhed inden for et geografisk afgrænset område.",
        ),
    ],
    preferred_labels=[
        LangString(lang="en", value="Municipality"),
        LangString(lang="da", value="Kommune"),
    ],
)
public_authority_type = FormalOrganisationType(
    definitions=[
        LangString(
            lang="en",
            value="A public authority is a public administrative unit that has a law enforcement function within the framework of a state, a state, a region or a municipality, and which is not a parliamentary assembly.",
        ),
        LangString(
            lang="da",
            value="En offentlig myndighed er et offentlig forvaltningsenhed, der har en lovudøvende funktion inden for rammerne af en stat, en delstat, en region eller en kommune, og som ikke er en parlamentarisk forsamling.",
        ),
    ],
    preferred_labels=[
        LangString(lang="en", value="Public authority"),
        LangString(lang="da", value="Offentlig myndighed"),
    ],
)


@strawberry.type(
    description="Organisation.",
    directives=[JSONLD(id="http://www.w3.org/ns/org#FormalOrganization", type="@id")],
)
class FormalOrganisation:
    id: UUID
    user_friendly_key: str | None = strawberry.field(
        directives=[
            JSONLD(
                id="https://data.gov.dk/model/core/organisation/extension/userFriendlyKey"
            )
        ],
    )
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
    """Organisation resolver."""
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
    """Organisational Unit resolver."""
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
    """The entrypoint for read operations."""

    organisational_units: list[OrganisationalUnit] = strawberry.field(
        resolver=get_organisational_units,
        description="Get organisational units.",
    )
    organisations: list[FormalOrganisation] = strawberry.field(
        resolver=get_organisations,
        description="Get organisations.",
        directives=[
            JSONLD(id="http://www.w3.org/ns/org#FormalOrganization", container="@set")
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


schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    extensions=[JSONLDExtension],
)
