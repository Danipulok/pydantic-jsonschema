"""Small shared utilities for the converter package."""

# NOTE: `Schema` fields use `X | MISSING` unions (see `_schema.py`). mypy doesn't
# recognize `MISSING` as a type, so it infers fields without the `Sentinel` branch
# and flags every `is not MISSING` check as a non-overlapping identity comparison.
# mypy: disable-error-code="comparison-overlap"

from typing import Any, Protocol, Union, cast

from pydantic import model_validator
from pydantic.experimental.missing_sentinel import MISSING

__all__ = [
    "before_validator",
    "make_union",
    "unwrap",
]

type PythonType = Any


class _Validatable(Protocol):
    """A subschema marker exposing a whole-value `before`-validator entry point."""

    def validate(self, data: PythonType, /) -> PythonType:
        """Validate the raw input, returning it unchanged or raising `ValueError`."""
        ...


def unwrap[T](value: T, /, *, default: T) -> T:
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


def before_validator(key: str, /, *, marker: _Validatable) -> dict[str, PythonType]:
    """Wrap a marker's `validate` as a `before` `model_validator` `__validators__` fragment.

    :param key: The `__validators__` key for the validator.
    :param marker: The registered marker whose `validate` runs on the raw input.
    :returns: A single-entry `create_model(__validators__=...)` mapping.
    """

    def _check(data: PythonType) -> PythonType:
        return marker.validate(data)

    return {key: model_validator(mode="before")(_check)}
