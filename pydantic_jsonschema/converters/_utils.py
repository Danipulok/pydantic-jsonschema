"""Small shared utilities for the converter package."""

# `Schema` fields use `X | MISSING` unions (see `schema/_models.py`), and so does `unwrap`
#  below. mypy rejects `MISSING` as a type (`valid-type`), then infers the fields without
#  the `Sentinel` branch and flags every `is not MISSING` check as a non-overlapping
#  identity comparison (`comparison-overlap`). This module needs only the first; the
#  modules that compare fields disable the second.
# mypy: disable-error-code="valid-type"

from typing import Any, Union, cast

from pydantic.experimental.missing_sentinel import MISSING

__all__ = [
    "make_union",
    "unwrap",
]

type PythonType = Any


def unwrap[ValueT](value: ValueT | MISSING, /, *, default: ValueT) -> ValueT:
    """Return a `Schema` field's value, or `default` when it is the `MISSING` sentinel.

    Replaces the `value if value is not MISSING else default` ternary repeated across the
    converter, so a field name is named once instead of twice.

    :param value: A `Schema` field that may hold the `MISSING` sentinel.
    :param default: Value to use when the field is absent.
    :returns: The field value, or `default` when absent.
    """
    return value if value is not MISSING else default


def make_union(args: list[Any], /) -> type:
    """Build a `Union` annotation from a dynamic list of member types.

    The `X | Y` operator form is impossible for a runtime-built tuple, so this is the one place
    that suppresses the `valid-type` (dynamic subscript) and `UP007` (prefer `X | Y`) diagnostics.

    :param args: Member annotations (types or `ForwardRef`s).
    :returns: The `Union[...]` annotation.
    """
    return cast("type", Union[tuple(args)])  # noqa: UP007
