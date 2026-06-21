"""Stateless object-keyword `model_validator` builders.

Each builder turns one object-level keyword into a `__validators__` fragment (empty when the
keyword is absent). These keywords need no subschema conversion, so they are plain functions; the
converter-aware ones (`dependentSchemas` / `patternProperties` / `propertyNames`) stay on the
`SchemaConverter`.
"""

# NOTE: `Schema` fields use `X | MISSING` unions (see `_schema.py`). mypy doesn't
# recognize `MISSING` as a type, so it infers fields without the `Sentinel` branch
# and flags every `is not MISSING` check as a non-overlapping identity comparison.
# mypy: disable-error-code="comparison-overlap"

from typing import Any

from pydantic import model_validator
from pydantic.experimental.missing_sentinel import MISSING

from pydantic_jsonschema.types import Schema

__all__ = [
    "build_dependent_required",
    "build_property_count",
]

type PythonType = Any


def build_property_count(schema: Schema, /) -> dict[str, PythonType]:
    """`minProperties` / `maxProperties`: bound the number of properties of an object model.

    Counts the raw input mapping's keys before field parsing. That key count is exactly the
    JSON Schema "number of properties" (declared fields plus `extra` keys) and is unambiguous
    regardless of which keys map to declared fields (validation §6.5.1 / §6.5.2).

    :param schema: Object schema.
    :returns: A `__validators__` mapping (empty when neither bound is set).
    """
    min_properties = schema.min_properties if schema.min_properties is not MISSING else None
    max_properties = schema.max_properties if schema.max_properties is not MISSING else None
    if min_properties is None and max_properties is None:
        return {}

    def _check(data: PythonType) -> PythonType:
        # Non-mapping input is left for the normal type validation to reject.
        if not isinstance(data, dict):
            return data

        count: int = len(data)
        if min_properties is not None and count < min_properties:
            msg = f"Object must have at least `{min_properties}` properties"
            raise ValueError(msg)
        if max_properties is not None and count > max_properties:
            msg = f"Object must have at most `{max_properties}` properties"
            raise ValueError(msg)

        return data

    return {"_validate_property_count": model_validator(mode="before")(_check)}


def build_dependent_required(schema: Schema, /) -> dict[str, PythonType]:
    """`dependentRequired`: when a property is present, the listed properties are required too.

    Checks the raw input mapping keys before field parsing, so it sees every present property
    (declared fields plus `extra` keys) (validation §6.5.4).

    :param schema: Object schema.
    :returns: A `__validators__` mapping (empty when the keyword is absent).
    """
    if schema.dependent_required is MISSING:
        return {}

    dependent_required: dict[str, list[str]] = schema.dependent_required

    def _check(data: PythonType) -> PythonType:
        # Non-mapping input is left for the normal type validation to reject.
        if not isinstance(data, dict):
            return data

        for trigger, required in dependent_required.items():
            if trigger not in data:
                continue
            missing = [name for name in required if name not in data]
            if missing:
                missing_list = "`, `".join(missing)
                msg = f"Property `{trigger}` requires `{missing_list}`"
                raise ValueError(msg)

        return data

    return {"_validate_dependent_required": model_validator(mode="before")(_check)}
