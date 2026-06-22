"""`oneOf` discriminator detection.

When every `oneOf` branch is an object tagged by a shared constant property, the union can be
promoted to a native Pydantic discriminated union (`Field(discriminator=...)`) instead of the
probing `OneOf` validator.
"""

# NOTE: `Schema` fields use `X | MISSING` unions (see `_schema.py`). mypy doesn't
# recognize `MISSING` as a type, so it infers fields without the `Sentinel` branch
# and flags every `is not MISSING` check as a non-overlapping identity comparison.
# mypy: disable-error-code="comparison-overlap"

from types import NoneType

from pydantic.experimental.missing_sentinel import MISSING

from pydantic_jsonschema.types import Reference, Schema

from ._helpers import unwrap

__all__ = ["discriminator_property"]

type TagType = str | int | None  # Scalar discriminator tag value (`bool` is an `int`)


def discriminator_property(
    one_of_schemas: list[Schema | Reference],
    /,
    *,
    defs_cache: dict[str, Schema],
) -> str | None:
    """Find the property that tags every `oneOf` branch with a distinct constant.

    A property qualifies as a discriminator when, in *every* branch, it is a required
    property whose schema is a single constant (`const` or single-value `enum`),
    and its constant value is distinct across branches.

    :param one_of_schemas: Sub-schemas of the `oneOf` composition.
    :param defs_cache: Resolved local `$defs`, for introspecting `$ref` branches.
    :returns: The discriminator property name, or `None` when zero or more than
        one property qualifies (ambiguous discriminators stay on the `OneOf` path).
    """
    branch_count: int = len(one_of_schemas)

    # Collect each branch's tag value per property name.
    tags_by_property: dict[str, list[TagType]] = {}
    for branch in one_of_schemas:
        branch_schema = _resolve_branch_schema(branch, defs_cache=defs_cache)
        if branch_schema is None or branch_schema.properties is MISSING:
            return None

        for name, tag in _branch_tag_values(branch_schema).items():
            tags_by_property.setdefault(name, []).append(tag)

    # A discriminator tags every branch (count of tags == branch count)
    # with a distinct value (count of unique tags == branch count).
    qualified: list[str] = [
        name
        for name, tags in tags_by_property.items()
        if len(tags) == branch_count == len(set(tags))
    ]

    # Exactly one qualifying property keeps promotion predictable.
    if len(qualified) != 1:
        return None
    return qualified[0]


def _resolve_branch_schema(
    branch: Schema | Reference,
    /,
    *,
    defs_cache: dict[str, Schema],
) -> Schema | None:
    """Resolve a `oneOf` branch to a concrete object schema, if known.

    :param branch: A `oneOf` sub-schema or reference.
    :param defs_cache: Resolved local `$defs`.
    :returns: The inline schema, the cached schema for a local `$ref`, or `None`
        when the reference can't be introspected (external / forward / pre-built).
    """
    if isinstance(branch, Reference):
        return defs_cache.get(branch.ref)
    return branch


def _branch_tag_values(
    schema: Schema,
    /,
) -> dict[str, TagType]:
    """Map each required single-constant property of a branch to its tag value.

    Only scalar constants (`str` / `int` / `bool` / `None`) are eligible tags —
    they are the hashable, `Literal`-compatible values Pydantic accepts as discriminators.

    :param schema: Object branch schema.
    :returns: Mapping of property name to its constant tag value.
    """
    required: set[str] = set(unwrap(schema.required, default=[]))
    tags: dict[str, TagType] = {}
    for name, prop in schema.properties.items():
        if name not in required or isinstance(prop, Reference):
            continue

        if prop.const is not MISSING:
            tag = prop.const
        elif prop.enum is not MISSING and len(prop.enum) == 1:
            tag = prop.enum[0]
        else:
            continue

        # NOTE: Only scalar tags are accepted. `discriminator_property` puts these
        # values in a `set()` to check distinctness across branches, so a non-hashable
        # `const` (array/object) would crash. `float` is excluded on purpose:
        # float-equality discrimination is fragile, so such unions fall back to `OneOf`.
        if isinstance(tag, (str, int, NoneType)):
            tags[name] = tag

    return tags
