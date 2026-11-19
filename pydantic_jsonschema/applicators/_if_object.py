"""Object keywords on a schema that does not convert to an object model.

JSON Schema object keywords (`properties`, `required`, `minProperties`, ...) assert only on object
instances; every other instance passes them.
See: https://json-schema.org/draft/2020-12/json-schema-core#section-10.3.2
"""

from typing import override

from pydantic import GetJsonSchemaHandler
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema

from pydantic_jsonschema.schema import DataType

from ._base import AnnotationType
from ._if_type import IfType

__all__ = ["IfObject"]


class IfObject(IfType):
    """Validate mapping inputs against an object annotation, and pass every other input through.

    Carried by an untyped schema (`Any`), whose host type cannot express the keywords.
    """

    def __init__(
        self,
        *,
        branch: AnnotationType,
    ) -> None:
        """Initialize with the object annotation every mapping input must validate against.

        :param branch: The object annotation (a model or an annotated `dict[str, ...]`).
        """
        super().__init__(
            data_type=DataType.OBJECT,
            branch=branch,
        )

    @override
    def __get_pydantic_json_schema__(
        self,
        schema: CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        """Dump the host schema unchanged."""
        return handler(schema)
