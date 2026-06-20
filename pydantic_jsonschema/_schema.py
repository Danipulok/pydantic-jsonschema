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

    See [core §4.2.1](https://json-schema.org/draft/2020-12/json-schema-core#section-4.2.1).
    """

    NULL = "null"
    """The `null` type."""
    STRING = "string"
    """The `string` type."""
    NUMBER = "number"
    """The `number` type (any numeric value)."""
    INTEGER = "integer"
    """The `integer` type."""
    BOOLEAN = "boolean"
    """The `boolean` type."""
    ARRAY = "array"
    """The `array` type."""
    OBJECT = "object"
    """The `object` type."""


class Reference(BaseModel):
    """JSON Schema `$ref` reference.

    See [core §8.2.3.1](https://json-schema.org/draft/2020-12/json-schema-core#section-8.2.3.1).
    """

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )

    ref: str = Field(alias="$ref")
    """The `$ref` keyword: a URI reference to another schema."""


class Schema(BaseModel):
    """JSON Schema object.

    Declares the JSON Schema 2020-12 validation and applicator keywords; any other or
    custom keyword is still preserved via ``extra="allow"`` per spec §4.3.1 / §6.5.

    Not every declared keyword is consumed by the converter yet: unsupported ones
    round-trip through parsing and serialization but do not affect the generated model.

    See:

    - [core §4.3.1](https://json-schema.org/draft/2020-12/json-schema-core#section-4.3.1)
    - [core §6.5](https://json-schema.org/draft/2020-12/json-schema-core#section-6.5)
    - [validation](https://json-schema.org/draft/2020-12/json-schema-validation)
    """

    model_config = ConfigDict(
        extra="allow",
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )

    type: DataType | list[DataType] | MISSING = MISSING
    """The `type` keyword: allowed JSON type(s). [Validation §6.1.1](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.1.1)."""

    enum: list[Any] | MISSING = MISSING
    """The `enum` keyword: the set of allowed values. [Validation §6.1.2](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.1.2)."""
    const: Any | MISSING = MISSING
    """The `const` keyword: the single allowed value. [Validation §6.1.3](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.1.3)."""

    properties: dict[str, SchemaOrRefType] | MISSING = MISSING
    """The `properties` keyword: schemas for object properties. [Core §10.3.2.1](https://json-schema.org/draft/2020-12/json-schema-core#section-10.3.2.1)."""
    items: SchemaOrRefType | MISSING = MISSING
    """The `items` keyword: the schema for array elements. [Core §10.3.1.2](https://json-schema.org/draft/2020-12/json-schema-core#section-10.3.1.2)."""
    prefix_items: list[SchemaOrRefType] | MISSING = MISSING
    """The `prefixItems` keyword: schemas for the leading array elements (tuple). [Core §10.3.1.1](https://json-schema.org/draft/2020-12/json-schema-core#section-10.3.1.1)."""
    contains: SchemaOrRefType | MISSING = MISSING
    """The `contains` keyword: at least one array element must match this schema. [Core §10.3.1.3](https://json-schema.org/draft/2020-12/json-schema-core#section-10.3.1.3)."""
    additional_properties: SchemaOrRefType | bool | MISSING = MISSING
    """The `additionalProperties` keyword: schema/toggle for extra properties. [Core §10.3.2.3](https://json-schema.org/draft/2020-12/json-schema-core#section-10.3.2.3)."""
    pattern_properties: dict[str, SchemaOrRefType] | MISSING = MISSING
    """The `patternProperties` keyword: schemas for properties matching a regex. [Core §10.3.2.2](https://json-schema.org/draft/2020-12/json-schema-core#section-10.3.2.2)."""

    required: list[str] | MISSING = MISSING
    """The `required` keyword: names of required properties. [Validation §6.5.3](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.5.3)."""
    min_properties: int | MISSING = MISSING
    """The `minProperties` keyword: minimum number of properties. [Validation §6.5.2](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.5.2)."""
    max_properties: int | MISSING = MISSING
    """The `maxProperties` keyword: maximum number of properties. [Validation §6.5.1](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.5.1)."""
    dependent_required: dict[str, list[str]] | MISSING = MISSING
    """The `dependentRequired` keyword: properties required when another is present. [Validation §6.5.4](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.5.4)."""
    dependent_schemas: dict[str, SchemaOrRefType] | MISSING = MISSING
    """The `dependentSchemas` keyword: subschemas applied when a property is present. [Core §10.2.2.4](https://json-schema.org/draft/2020-12/json-schema-core#section-10.2.2.4)."""

    all_of: list[SchemaOrRefType] | MISSING = MISSING
    """The `allOf` keyword: must match every subschema. [Core §10.2.1.1](https://json-schema.org/draft/2020-12/json-schema-core#section-10.2.1.1)."""
    any_of: list[SchemaOrRefType] | MISSING = MISSING
    """The `anyOf` keyword: must match at least one subschema. [Core §10.2.1.2](https://json-schema.org/draft/2020-12/json-schema-core#section-10.2.1.2)."""
    one_of: list[SchemaOrRefType] | MISSING = MISSING
    """The `oneOf` keyword: must match exactly one subschema. [Core §10.2.1.3](https://json-schema.org/draft/2020-12/json-schema-core#section-10.2.1.3)."""

    # NOTE: `not` / `if` / `else` are Python reserved words, so the fields use a trailing
    # underscore with an explicit alias. `populate_by_name=True` keeps both forms loadable
    # (e.g. `Schema(if_=...)` and `Schema.model_validate({"if": ...})`); dumps use the alias.
    not_: SchemaOrRefType | MISSING = Field(default=MISSING, alias="not")
    """The `not` keyword: must NOT match this subschema. [Core §10.2.1.4](https://json-schema.org/draft/2020-12/json-schema-core#section-10.2.1.4)."""

    if_: SchemaOrRefType | MISSING = Field(default=MISSING, alias="if")
    """The `if` keyword: condition subschema gating `then` / `else`. [Core §10.2.2.1](https://json-schema.org/draft/2020-12/json-schema-core#section-10.2.2.1)."""
    then: SchemaOrRefType | MISSING = MISSING
    """The `then` keyword: applied when `if` validates. [Core §10.2.2.2](https://json-schema.org/draft/2020-12/json-schema-core#section-10.2.2.2)."""
    else_: SchemaOrRefType | MISSING = Field(default=MISSING, alias="else")
    """The `else` keyword: applied when `if` fails. [Core §10.2.2.3](https://json-schema.org/draft/2020-12/json-schema-core#section-10.2.2.3)."""

    multiple_of: float | MISSING = MISSING
    """The `multipleOf` keyword: value must be a multiple of this. [Validation §6.2.1](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.2.1)."""
    maximum: float | MISSING = MISSING
    """The `maximum` keyword: inclusive upper bound. [Validation §6.2.2](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.2.2)."""
    exclusive_maximum: float | MISSING = MISSING
    """The `exclusiveMaximum` keyword: exclusive upper bound. [Validation §6.2.3](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.2.3)."""
    minimum: float | MISSING = MISSING
    """The `minimum` keyword: inclusive lower bound. [Validation §6.2.4](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.2.4)."""
    exclusive_minimum: float | MISSING = MISSING
    """The `exclusiveMinimum` keyword: exclusive lower bound. [Validation §6.2.5](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.2.5)."""

    min_length: int | MISSING = MISSING
    """The `minLength` keyword: minimum string length. [Validation §6.3.2](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.3.2)."""
    max_length: int | MISSING = MISSING
    """The `maxLength` keyword: maximum string length. [Validation §6.3.1](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.3.1)."""
    pattern: str | MISSING = MISSING
    """The `pattern` keyword: regex the string must match. [Validation §6.3.3](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.3.3)."""

    min_items: int | MISSING = MISSING
    """The `minItems` keyword: minimum array length. [Validation §6.4.2](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.4.2)."""
    max_items: int | MISSING = MISSING
    """The `maxItems` keyword: maximum array length. [Validation §6.4.1](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.4.1)."""
    unique_items: bool | MISSING = MISSING
    """The `uniqueItems` keyword: array elements must be unique. [Validation §6.4.3](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.4.3)."""
    max_contains: int | MISSING = MISSING
    """The `maxContains` keyword: max elements matching `contains`. [Validation §6.4.4](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.4.4)."""
    min_contains: int | MISSING = MISSING
    """The `minContains` keyword: min elements matching `contains`. [Validation §6.4.5](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.4.5)."""

    format: str | MISSING = MISSING
    """The `format` keyword: a semantic format (e.g. `date-time`). [Validation §7](https://json-schema.org/draft/2020-12/json-schema-validation#section-7)."""

    title: str | MISSING = MISSING
    """The `title` keyword: a human-readable name. [Validation §9.1](https://json-schema.org/draft/2020-12/json-schema-validation#section-9.1)."""
    description: str | MISSING = MISSING
    """The `description` keyword: a human-readable explanation. [Validation §9.1](https://json-schema.org/draft/2020-12/json-schema-validation#section-9.1)."""
    default: Any | MISSING = MISSING
    """The `default` keyword: a default value for the instance. [Validation §9.2](https://json-schema.org/draft/2020-12/json-schema-validation#section-9.2)."""
    examples: list[Any] | MISSING = MISSING
    """The `examples` keyword: example values. [Validation §9.5](https://json-schema.org/draft/2020-12/json-schema-validation#section-9.5)."""

    defs: dict[str, SchemaOrRefType] | MISSING = Field(default=MISSING, alias="$defs")
    """The `$defs` keyword: reusable subschema definitions. [Core §8.2.4](https://json-schema.org/draft/2020-12/json-schema-core#section-8.2.4)."""
