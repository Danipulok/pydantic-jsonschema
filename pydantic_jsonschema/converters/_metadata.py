"""`Annotated` metadata helpers for array / object value annotations."""

# NOTE: `Schema` fields use `X | MISSING` unions (see `schema/_models.py`). mypy doesn't
#  recognize `MISSING` as a type, so it infers fields without the `Sentinel` branch
#  and flags every `is not MISSING` check as a non-overlapping identity comparison.
# mypy: disable-error-code="comparison-overlap"

from typing import Annotated, Any, cast

import annotated_types
from pydantic import AfterValidator
from pydantic.experimental.missing_sentinel import MISSING

from pydantic_jsonschema.schema import Schema

__all__ = [
    "annotate",
    "array_metadata",
    "object_dict_metadata",
]

type AnnotationType = Any


def _ensure_unique_items(value: list[Any], /) -> list[Any]:
    """Reject arrays with duplicate items (`uniqueItems: true`, validation §6.4.3).

    Items are compared by Python equality, which matches JSON structural equality for the
    common scalar / object / array cases. The check is O(n^2) pairwise rather than `set`-based
    because JSON values can be unhashable (`dict` / `list`).

    NOTE: Python equates `True == 1` and `1 == 1.0`, so e.g. `[true, 1]` is treated as a
    duplicate even though JSON Schema considers the two values distinct. Acceptable edge.

    Reproduce:
        to_model(Schema(type="array", unique_items=True)).model_validate([1, 1])
        # -> ValidationError: Array items must be unique

    :param value: The already-parsed array.
    :returns: The array unchanged when all items are unique.
    :raises ValueError: When two items are equal.
    """
    seen: list[Any] = []
    for item in value:
        if item in seen:
            msg = "Array items must be unique"
            raise ValueError(msg)
        seen.append(item)
    return value


def annotate(annotation: AnnotationType, /, *, metadata: list[Any]) -> type:
    """Wrap an annotation with `Annotated` metadata (validators / constraints).

    :param annotation: Base annotation (e.g. `list[int]`, `dict[str, int]`).
    :param metadata: `Annotated` metadata to attach (empty -> annotation returned as-is).
    :returns: The annotation, wrapped only when there is metadata to attach.
    """
    if not metadata:
        return cast("type", annotation)
    return cast("type", Annotated[(annotation, *metadata)])


def array_metadata(schema: Schema, /) -> list[Any]:
    """`Annotated` metadata for array constraint keywords.

    :param schema: Array schema.
    :returns: Metadata for the array's `list[...]` annotation (add a keyword's check here).
    """
    metadata: list[Any] = []
    # `uniqueItems: false` (and absent) imposes no constraint; only `true` enforces.
    if schema.unique_items is True:
        metadata.append(AfterValidator(_ensure_unique_items))
    return metadata


def object_dict_metadata(schema: Schema, /) -> list[Any]:
    """`Annotated` metadata for object keywords on a `dict` mapping (no declared properties).

    :param schema: Object schema mapped to `dict[str, ...]`.
    :returns: Length metadata for `minProperties` / `maxProperties` (add a keyword's check here).
    """
    metadata: list[Any] = []
    if schema.min_properties is not MISSING:
        metadata.append(annotated_types.MinLen(schema.min_properties))
    if schema.max_properties is not MISSING:
        metadata.append(annotated_types.MaxLen(schema.max_properties))
    return metadata
