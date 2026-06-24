"""`FieldInfo` kwargs and defaults derived from JSON Schema constraints."""

# NOTE: `Schema` fields use `X | MISSING` unions (see `schema/_models.py`). mypy doesn't
# recognize `MISSING` as a type, so it infers fields without the `Sentinel` branch
# and flags every `is not MISSING` check as a non-overlapping identity comparison.
# mypy: disable-error-code="comparison-overlap"

from types import EllipsisType
from typing import Any, Final, Literal, TypedDict

import annotated_types
from pydantic.experimental.missing_sentinel import MISSING

from pydantic_jsonschema.schema import DataType, Schema

from ._utils import unwrap

__all__ = [
    "FieldKindType",
    "build_field_kwargs",
    "get_field_default",
]

type FieldKindType = Literal["required", "optional", "root"]  # How a field is used in a model

# Pydantic's "required, no default" marker for a field default (`...`).
# See: https://github.com/pydantic/pydantic/blob/6800281ba87625346daf5826563740ded8a9851b/pydantic/fields.py#L241-L247
_PYDANTIC_DEFAULT_MISSING: Final[EllipsisType] = ...


class _FieldKwargs(TypedDict, total=False):
    """Subset of Pydantic `FieldInfo` kwargs produced from JSON Schema constraints.

    Field names and types mirror `pydantic.fields._FromFieldInfoInputs`.
    See: https://github.com/pydantic/pydantic/blob/v2.13.4/pydantic/fields.py#L50
    """

    examples: list[Any] | None
    title: str | None
    description: str | None
    ge: annotated_types.SupportsGe | None
    gt: annotated_types.SupportsGt | None
    le: annotated_types.SupportsLe | None
    lt: annotated_types.SupportsLt | None
    multiple_of: float | None
    min_length: int | None
    max_length: int | None
    pattern: str | None


def build_field_kwargs(schema: Schema, /, *, include_metadata: bool = True) -> _FieldKwargs:  # noqa: C901
    """Build `FieldInfo` kwargs, only including constraints that are explicitly set.

    :param schema: Schema to extract constraints and metadata from.
    :param include_metadata: When `False`, omit non-validating metadata (`title` / `description` /
        `examples`). Used for union branches, where these are not field metadata and would otherwise
        leak into the dumped `anyOf` / `oneOf` (e.g. a `title` on a discriminated `$ref` branch).
    :returns: Keyword arguments for `FieldInfo`.
    """
    kwargs: _FieldKwargs = {}

    if include_metadata:
        if schema.examples is not MISSING:
            kwargs["examples"] = schema.examples
        if schema.title is not MISSING:
            kwargs["title"] = schema.title
        if schema.description is not MISSING:
            kwargs["description"] = schema.description

    if schema.minimum is not MISSING:
        kwargs["ge"] = schema.minimum
    if schema.exclusive_minimum is not MISSING:
        kwargs["gt"] = schema.exclusive_minimum
    if schema.maximum is not MISSING:
        kwargs["le"] = schema.maximum
    if schema.exclusive_maximum is not MISSING:
        kwargs["lt"] = schema.exclusive_maximum
    if schema.multiple_of is not MISSING:
        kwargs["multiple_of"] = schema.multiple_of
    if schema.pattern is not MISSING:
        kwargs["pattern"] = schema.pattern

    min_length = _get_min_length(schema)
    if min_length is not None:
        kwargs["min_length"] = min_length

    max_length = _get_max_length(schema)
    if max_length is not None:
        kwargs["max_length"] = max_length

    return kwargs


def get_field_default(
    schema: Schema,
    /,
    *,
    field_kind: FieldKindType,
) -> Any:  # noqa: ANN401
    """Determine default value for the field based on its schema.

    :param schema: Schema to get default from.
    :param field_kind: `required` / `optional` object property, or `root` model value.
    :returns: Default value, `...` for required fields, or the `MISSING` sentinel.
    """
    if field_kind == "required":
        return _PYDANTIC_DEFAULT_MISSING

    if schema.default is not MISSING:
        return schema.default

    # Root model values have no "absent" concept:
    # a bare `{"type": "string"}` root schema always validates a value.
    if field_kind == "root":
        return _PYDANTIC_DEFAULT_MISSING

    # Optional field without explicit default -> `MISSING` sentinel, so the
    # field is omitted from dumps instead of carrying a fabricated `None`
    # default that would not even validate against the annotation.
    return MISSING


def _get_min_length(schema: Schema, /) -> int | None:
    """Get min length based on schema type.

    :param schema: Schema to extract constraint from.
    :returns: `minItems` for arrays, `minLength` for strings, `None` if unset.
    """
    if schema.type == DataType.ARRAY:
        return unwrap(schema.min_items, default=None)
    return unwrap(schema.min_length, default=None)


def _get_max_length(schema: Schema, /) -> int | None:
    """Get max length based on schema type.

    :param schema: Schema to extract constraint from.
    :returns: `maxItems` for arrays, `maxLength` for strings, `None` if unset.
    """
    if schema.type == DataType.ARRAY:
        return unwrap(schema.max_items, default=None)
    return unwrap(schema.max_length, default=None)
