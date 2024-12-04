import datetime
from decimal import Decimal
from typing import Any
from typing import Callable
from uuid import UUID

import strawberry
from graphql import GraphQLResolveInfo
from starlette_context import context as starlette_context
from strawberry import Schema
from strawberry.extensions import SchemaExtension
from strawberry.schema_directive import Location
from strawberry.types.base import StrawberryOptional
from strawberry.utils.await_maybe import AsyncIteratorOrIterator
from strawberry.utils.await_maybe import AwaitableOrValue
from strawberry.utils.await_maybe import await_maybe


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
    """JSON-LD Expanded term definition. Used to tag types and fields in GraphQL.

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


FALLBACK_TYPES: dict = {
    # List of types inspired by
    # strawberry.schema.types.scalar.DEFAULT_SCALAR_REGISTRY
    bool: JSONLD(id="http://www.w3.org/2001/XMLSchema#boolean"),
    float: JSONLD(id="http://www.w3.org/2001/XMLSchema#float"),
    int: JSONLD(id="http://www.w3.org/2001/XMLSchema#integer"),
    str: JSONLD(id="http://www.w3.org/2001/XMLSchema#string"),
    datetime.date: JSONLD(id="http://www.w3.org/2001/XMLSchema#date"),
    datetime.datetime: JSONLD(id="http://www.w3.org/2001/XMLSchema#dateTime"),
    datetime.time: JSONLD(id="http://www.w3.org/2001/XMLSchema#time"),
    Decimal: JSONLD(id="http://www.w3.org/2001/XMLSchema#decimal"),
    UUID: JSONLD(id="http://www.w3.org/TR/sparql11-query/#func-struuid"),
    strawberry.ID: JSONLD(id="http://www.w3.org/2001/XMLSchema#ID"),
}


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
        schema: Schema = info.context["schema"]
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
            # Fallback to simple literal types for scalar fields which do not
            # have a JSONLD directive.
            field_type = field.type
            # Optional types are wrapped in StrawberryOptional
            if isinstance(field_type, StrawberryOptional):
                field_type = field_type.of_type
            try:
                field_context = FALLBACK_TYPES[field_type]
            except KeyError:
                # Set non-scalar fields as an opaque JSON blob
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
        try:
            context = starlette_context["jsonld_context"]
        except KeyError:
            return {}
        return {
            "@context": {
                "data": {
                    "@id": "https://example.org/#TODO",
                    **context,
                },
            },
        }
