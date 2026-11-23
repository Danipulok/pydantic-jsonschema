"""Small shared utilities for the converter package."""

from typing import Any, Union, cast

from pydantic_jsonschema._compat import MISSING
from pydantic_jsonschema.schema import Schema

__all__ = [
    "make_union",
    "produces_all_of_model",
    "unwrap",
]

# mypy resolves `get_origin()` of a PEP 695 alias of `Any` to its first overload, which returns
#  `ParamSpec`, so `get_origin(value) is Annotated` reads as a non-overlapping identity check;
#  each such check carries a line ignore that `warn_unused_ignores` reports once mypy is fixed.
#  Reproduce with mypy 2.4.1 `--strict`: annotate `x` with `type T = Any` and return
#  `get_origin(x) is Annotated`, which prints `Non-overlapping identity check (left operand type:
#  "ParamSpec", right operand type: "<typing special form>")`; a plain `x: Any` passes.
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

    The `X | Y` operator form is impossible for a runtime-built tuple, so this call
    suppresses `UP007` (prefer `X | Y`).

    :param args: Member annotations (types or `ForwardRef`s).
    :returns: The `Union[...]` annotation.
    """
    return cast("type", Union[tuple(args)])  # noqa: UP007


def produces_all_of_model(schema: Schema, /) -> bool:
    """Return whether the schema converts to its `allOf` model, which checks its other keywords.

    `enum` / `const`, then `anyOf` / `oneOf`, take precedence over `allOf` for the annotation, and
    then no `allOf` model is built.

    :param schema: Schema to inspect.
    :returns: `True` when `allOf` produces the annotation.
    """
    return schema.all_of is not MISSING and all(
        keyword is MISSING for keyword in (schema.enum, schema.const, schema.any_of, schema.one_of)
    )
