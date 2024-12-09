import base64
import bz2
import datetime
import json
from contextlib import suppress
from decimal import Decimal
from typing import Any
from typing import Callable
from uuid import UUID

import strawberry
from graphql import GraphQLResolveInfo
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.responses import Response
from starlette_context import context as starlette_context
from strawberry.extensions import SchemaExtension
from strawberry.schema_directive import Location
from strawberry.types import ExecutionContext
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
        """Convert to JSON-LD @context dict.

        # https://www.w3.org/TR/json-ld/#context-definitions
        # https://www.w3.org/TR/json-ld/#keywords
        """
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
    strawberry.ID: JSONLD(
        id="http://www.w3.org/2001/XMLSchema#ID"  # TODO: this is wrong
    ),
}


class JSONLDExtension(SchemaExtension):
    """Strawberry extension which adds JSON-LD context as a GraphQL extension
    and HTTP header.

    JSON-LD contexts can either be directly embedded into the document (an
    embedded context) or be referenced using a URL[1]. As per the GraphQL
    spec[2], the only keys allowed in the response are `data`, `errors` and
    `extensions`. We are therefore not allowed to add an embedded context using
    a JSON-LD `@context` key.

    Ordinary JSON documents can be interpreted as JSON-LD by providing an
    explicit JSON-LD context document, for example by referencing a JSON-LD
    context document in an HTTP Link Header[3]. In this way, we avoid breaking
    the GraphQL spec, while still providing JSON-LD processors with JSON-LD
    context data.

    [1] https://www.w3.org/TR/json-ld11/#the-context
    [2] https://spec.graphql.org/draft/#sec-Response-Format
    [3] https://www.w3.org/TR/json-ld11/#interpreting-json-as-json-ld
    """

    @property
    def real_execution_context(self) -> ExecutionContext:
        # HACK: see _create_execution_context() in schema.py
        return starlette_context["execution_context"]

    def on_execute(self) -> AsyncIteratorOrIterator[None]:  # type: ignore
        """Called for the execution step of the GraphQL query."""
        # Instantiate empty JSON-LD context on every GraphQL execution. A
        # GraphQL response is always nested under the `data` key.
        context = {
            "@context": {
                "data": {
                    "@id": "https://example.org/#TODO",
                },
            },
        }
        self.real_execution_context.context["jsonld_context"] = context

        yield  # Execute! This will build a JSON-LD context through the resolve() hook

        # Add HTTP 'Link' header to JSON-LD context document. The generated
        # JSON-LD context is encoded as part of the URL to make it stateless.
        request: Request = self.real_execution_context.context["request"]
        response: Response = self.real_execution_context.context["response"]
        url = request.url_for("jsonld-context", context=encode_context(context))
        response.headers["Link"] = (
            f"<{url}>"
            ';rel="http://www.w3.org/ns/json-ld#context"'
            ';type="application/ld+json"'
        )

    def _add_to_context(self, info: GraphQLResolveInfo) -> None:
        """Add resolved field to the JSON-LD context."""
        # `info.field_name` and `info.parent_type` is the actual field and type
        # in the *schema*. We use these to fetch the JSONLD directive object.
        field = self.real_execution_context.schema.get_field_for_type(
            field_name=info.field_name,
            type_name=info.parent_type.name,
        )
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
        # manner. Add the "data" ancestor since it's not part of the schema.
        context: dict = self.real_execution_context.context["jsonld_context"]
        for ancestor in ["data"] + ancestors:
            context = context["@context"][ancestor]

        # Add this node to the parent's context, creating it if this is the
        # first child.
        # https://www.w3.org/TR/json-ld/#scoped-contexts
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
        with suppress(KeyError):
            return self.real_execution_context.context["jsonld_context"]
        # The jsonld_context may not have been set if the GraphQL query was
        # never executed, e.g. due to syntax errors.
        return {}


async def context_endpoint(request: Request) -> JSONResponse:
    """JSON-LD Context document endpoint."""
    context = request.path_params["context"]
    return JSONResponse(decode_context(context), media_type="application/ld+json")


def encode_context(context: dict) -> str:
    """Encode and compress context."""
    # TODO: This can probably be done without encoding/decoding twice
    json_string = json.dumps(context)
    json_bytes = json_string.encode()
    compressed_bytes = bz2.compress(json_bytes)
    b64_bytes = base64.urlsafe_b64encode(compressed_bytes)
    b64_string = b64_bytes.decode()
    return b64_string


def decode_context(b64_string: str) -> dict:
    """Decode and decompress context."""
    # TODO: This can probably be done without encoding/decoding twice
    b64_bytes = b64_string.encode()
    compressed_bytes = base64.urlsafe_b64decode(b64_bytes)
    json_bytes = bz2.decompress(compressed_bytes)
    json_string = json_bytes.decode()
    context = json.loads(json_string)
    return context
