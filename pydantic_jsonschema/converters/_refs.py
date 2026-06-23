"""`$defs` extraction and alias-chain resolution.

A `$defs` entry may be a `Reference` pointing at another definition (a def alias). These helpers
flatten such alias chains to the concrete schema they target, failing loudly on external,
circular, or dangling targets. They are stateless: alias resolution depends only on the raw
`$defs` mapping, not on converter state.
"""

# NOTE: `Schema` fields use `X | MISSING` unions (see `schema/_models.py`). mypy doesn't
# recognize `MISSING` as a type, so it infers fields without the `Sentinel` branch
# and flags every `is not MISSING` check as a non-overlapping identity comparison.
# mypy: disable-error-code="comparison-overlap"

from typing import Final

from pydantic.experimental.missing_sentinel import MISSING

from pydantic_jsonschema.exceptions import SchemaReferenceError
from pydantic_jsonschema.schema import Reference, Schema

__all__ = [
    "DEFS_KEY",
    "get_inline_defs",
    "resolve_def_alias",
]

# JSON Schema 2020-12 definitions key
# See: https://json-schema.org/draft/2020-12/json-schema-core#section-8.2.4
DEFS_KEY: Final[str] = "$defs"


def get_inline_defs(schema: Schema, /) -> dict[str, Schema]:
    """Extract inline schema defs from a schema's `$defs` field.

    `Reference` entries (def aliases) are resolved to their target schemas.

    :param schema: Schema to extract defs from.
    :returns: Mapping of reference paths to schemas.
    :raises SchemaReferenceError: If a def alias cannot be resolved.
    """
    if schema.defs is MISSING:
        return {}

    result_defs: dict[str, Schema] = {}
    for name in schema.defs:
        ref_path = f"#/{DEFS_KEY}/{name}"
        result_defs[ref_path] = resolve_def_alias(schema.defs, name=name)
    return result_defs


def resolve_def_alias(defs: dict[str, Schema | Reference], /, *, name: str) -> Schema:
    """Resolve a `$defs` entry to a concrete schema, following alias chains.

    :param defs: Raw `$defs` mapping.
    :param name: Definition name to resolve.
    :returns: Concrete schema for the definition.
    :raises SchemaReferenceError: If an alias chain is circular, points to a
        missing definition, or targets an external reference.
    """
    seen_names: list[str] = [name]
    current: Schema | Reference = defs[name]

    while isinstance(current, Reference):
        target_name = _check_alias_target(defs, reference=current, seen_names=seen_names)
        seen_names.append(target_name)
        current = defs[target_name]

    return current


def _check_alias_target(
    defs: dict[str, Schema | Reference],
    /,
    *,
    reference: Reference,
    seen_names: list[str],
) -> str:
    """Validate a single alias step and return the target definition name.

    :param defs: Raw `$defs` mapping.
    :param reference: Alias reference to validate.
    :param seen_names: Definition names already visited in the chain.
    :returns: Target definition name.
    :raises SchemaReferenceError: If the target is external, circular, or missing.
    """
    alias_name: str = seen_names[0]
    local_ref_prefix: str = f"#/{DEFS_KEY}/"

    if not reference.ref.startswith(local_ref_prefix):
        msg = (
            f"Cannot resolve {DEFS_KEY} alias `{alias_name}`: external reference `{reference.ref}`"
        )
        raise SchemaReferenceError(
            message=msg,
            path=seen_names.copy(),
        )

    target_name: str = reference.ref.removeprefix(local_ref_prefix)
    if target_name in seen_names:
        msg = f"Circular {DEFS_KEY} alias chain: {' -> '.join([*seen_names, target_name])}"
        raise SchemaReferenceError(
            message=msg,
            path=seen_names.copy(),
        )

    if target_name not in defs:
        msg = f"Cannot resolve {DEFS_KEY} alias `{alias_name}`: unknown target `{reference.ref}`"
        raise SchemaReferenceError(
            message=msg,
            path=seen_names.copy(),
        )

    return target_name
