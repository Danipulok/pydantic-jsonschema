"""JSON Schema models (draft 2020-12).

Core: https://json-schema.org/draft/2020-12/json-schema-core
Validation: https://json-schema.org/draft/2020-12/json-schema-validation
"""

# NOTE: `pydantic.experimental.missing_sentinel.MISSING` is a `Sentinel` instance,
# not a type — mypy rejects `field: X | MISSING` as invalid. Pydantic itself
# handles the union correctly at runtime via `from __future__ import annotations`.
# mypy: disable-error-code="valid-type"

from __future__ import annotations as _annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from pydantic.experimental.missing_sentinel import MISSING

__all__ = [
    "DataType",
    "Reference",
    "Schema",
    "SchemaOrRefType",
]

type SchemaOrRefType = Reference | Schema


class DataType(StrEnum):
    """JSON Schema primitive types.

    See: https://json-schema.org/draft/2020-12/json-schema-core#section-4.2.1
    """

    NULL = "null"
    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


class Reference(BaseModel):
    """JSON Schema `$ref` reference.

    See: https://json-schema.org/draft/2020-12/json-schema-core#section-8.2.3.1
    """

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )

    ref: str = Field(alias="$ref")


class Schema(BaseModel):
    """JSON Schema object.

    Only fields consumed by the converter are declared explicitly.
    Unknown keywords are preserved via ``extra="allow"`` per spec §4.3.1 / §6.5.

    See: https://json-schema.org/draft/2020-12/json-schema-core#section-4.3.1
    See: https://json-schema.org/draft/2020-12/json-schema-core#section-6.5
    See: https://json-schema.org/draft/2020-12/json-schema-validation
    """

    model_config = ConfigDict(
        extra="allow",
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )

    # Type — validation §6.1.1
    type: DataType | list[DataType] | MISSING = MISSING

    # Validation — enum / const — validation §6.1.2, §6.1.3
    enum: list[Any] | MISSING = MISSING
    const: Any | MISSING = MISSING

    # Subschemas — core §10.3
    properties: dict[str, SchemaOrRefType] | MISSING = MISSING
    items: SchemaOrRefType | MISSING = MISSING
    additional_properties: SchemaOrRefType | bool | MISSING = MISSING

    # Validation — object — validation §6.5.3
    required: list[str] | MISSING = MISSING

    # Composition — core §10.2.1
    all_of: list[SchemaOrRefType] | MISSING = MISSING
    any_of: list[SchemaOrRefType] | MISSING = MISSING
    one_of: list[SchemaOrRefType] | MISSING = MISSING

    # Validation — numeric — validation §6.2
    multiple_of: float | MISSING = MISSING
    maximum: float | MISSING = MISSING
    exclusive_maximum: float | MISSING = MISSING
    minimum: float | MISSING = MISSING
    exclusive_minimum: float | MISSING = MISSING

    # Validation — string — validation §6.3
    min_length: int | MISSING = MISSING
    max_length: int | MISSING = MISSING

    # Validation — array — validation §6.4
    min_items: int | MISSING = MISSING
    max_items: int | MISSING = MISSING

    # Format — validation §7
    format: str | MISSING = MISSING

    # Metadata — validation §9.1, §9.2, §9.5
    title: str | MISSING = MISSING
    description: str | MISSING = MISSING
    default: Any | MISSING = MISSING
    examples: list[Any] | MISSING = MISSING

    # Definitions — core §8.2.4
    defs: dict[str, SchemaOrRefType] | MISSING = Field(default=MISSING, alias="$defs")
