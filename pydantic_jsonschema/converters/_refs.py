"""`$defs` extraction, alias-chain resolution and `$ref` sibling normalization.

A `$defs` entry may be a `Reference` pointing at another definition (a def alias). These helpers
flatten such alias chains to the concrete schema they target, failing loudly on external,
circular, or dangling targets. They are stateless: alias resolution depends only on the raw
`$defs` mapping, not on converter state.

A `$ref` beside other keywords applies together with them (core §8.2.3.1), while the parsed node
keeps one half: a `Reference` holds the other keywords as extras, a `Schema` holds the `$ref` as
one. `normalize_ref_siblings` moves such a `$ref` under `allOf`, which the converter checks
together with the keywords beside it.
https://json-schema.org/draft/2020-12/json-schema-core#section-8.2.3.1
"""

# NOTE: `Schema` fields use `X | MISSING` unions (see `schema/_models.py`). mypy doesn't
#  recognize `MISSING` as a type, so it infers fields without the `Sentinel` branch
#  and flags every `is not MISSING` check as a non-overlapping identity comparison.
# mypy: disable-error-code="comparison-overlap"

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Final

from pydantic import ValidationError

from pydantic_jsonschema._compat import MISSING
from pydantic_jsonschema.exceptions import SchemaReferenceError
from pydantic_jsonschema.schema import Reference, Schema

__all__ = [
    "ANNOTATION_KEYWORDS",
    "DEFS_KEY",
    "ResolvedDef",
    "escape_pointer_token",
    "get_inline_defs",
    "normalize_ref_siblings",
    "resolve_def_alias",
]

type JsonValueType = Any  # A parsed JSON value, or a `Schema` / `Reference` node inside one

# JSON Schema 2020-12 definitions key
#  See: https://json-schema.org/draft/2020-12/json-schema-core#section-8.2.4
DEFS_KEY: Final[str] = "$defs"
_REF_KEY: Final[str] = "$ref"
# Beside these alone a `$ref` stays a `Reference`, so a field keeps the shared model and takes
#  them as its metadata, and a union branch keeps its discriminator.
ANNOTATION_KEYWORDS: Final[frozenset[str]] = frozenset(
    {"title", "description", "default", "examples"}
)
_VALIDATING_KEYWORDS: Final[frozenset[str]] = (
    frozenset(field.alias or name for name, field in Schema.model_fields.items())
    - ANNOTATION_KEYWORDS
)
# A field converts these ahead of `allOf` and drops it, so beside the `$ref` they would drop the
#  target; they move into a branch of their own instead.
_OWN_BRANCH_KEYWORDS: Final[frozenset[str]] = frozenset({"enum", "const", "anyOf", "oneOf"})


def escape_pointer_token(token: str, /) -> str:
    """Escape a raw member name into a JSON Pointer reference token.

    `~` and `/` are the two characters a pointer token cannot carry literally, since `/` separates
    tokens. RFC 6901 section 3 escapes them as `~0` and `~1`; `~` must go first, or the `~` written
    by the `/` -> `~1` step would be escaped again into `~01`.

    :param token: Raw member name (a property name, a `$defs` name, an array index).
    :returns: The escaped reference token.
    """
    return token.replace("~", "~0").replace("/", "~1")


@dataclass(frozen=True, slots=True)
class ResolvedDef:
    """A `$defs` entry resolved to its concrete schema and the name that declares that schema.

    The two differ only for a def alias: `{"Author": {"$ref": "#/$defs/User"}}` resolves to
    `User`'s body, declared under the name `User`.
    """

    name: str
    schema: Schema


def get_inline_defs(schema: Schema, /) -> dict[str, ResolvedDef]:
    """Extract inline schema defs from a schema's `$defs` field.

    `Reference` entries (def aliases) are resolved to their target schemas.

    :param schema: Schema to extract defs from.
    :returns: Mapping of reference paths to resolved definitions.
    :raises SchemaReferenceError: If a def alias cannot be resolved.
    """
    if schema.defs is MISSING:
        return {}

    result_defs: dict[str, ResolvedDef] = {}
    for name in schema.defs:
        ref_path = f"#/{DEFS_KEY}/{name}"
        result_defs[ref_path] = resolve_def_alias(schema.defs, name=name)
    return result_defs


def resolve_def_alias(defs: dict[str, Schema | Reference], /, *, name: str) -> ResolvedDef:
    """Resolve a `$defs` entry to a concrete schema, following alias chains.

    :param defs: Raw `$defs` mapping.
    :param name: Definition name to resolve.
    :returns: Concrete schema for the definition, with the name that declares it.
    :raises SchemaReferenceError: If an alias chain is circular, points to a
        missing definition, or targets an external reference.
    """
    seen_names: list[str] = [name]
    current: Schema | Reference = defs[name]

    while isinstance(current, Reference):
        target_name = _check_alias_target(defs, reference=current, seen_names=seen_names)
        seen_names.append(target_name)
        current = defs[target_name]

    return ResolvedDef(
        name=seen_names[-1],
        schema=current,
    )


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


def normalize_ref_siblings(schema: Schema, /, *, path: Sequence[str] = ()) -> Schema:
    """Move every `$ref` whose siblings must apply with it under `allOf`.

    The root `$ref` always moves. Elsewhere a `$ref` moves beside a validating keyword, whichever
    of `Reference` and `Schema` it parsed as; beside annotations and unknown keywords alone it is
    a `Reference`.

    :param schema: Root schema.
    :param path: Location of `schema`, for the error a non-string `$ref` raises.
    :returns: The schema with every such `$ref` as the first `allOf` branch.
    :raises SchemaReferenceError: If a `$ref` is not a string, or a keyword beside it is invalid.
    """
    ref: str | None = _schema_ref(schema, path=path)
    if ref is None:
        return _normalize_children(schema, path=path)

    return _ref_under_all_of(
        ref,
        siblings=_ref_siblings(schema),
        path=path,
    )


def _normalize_node(node: Schema | Reference, /, *, path: Sequence[str]) -> Schema | Reference:
    if isinstance(node, Reference):
        reference_siblings: dict[str, JsonValueType] = node.model_extra or {}
        if reference_siblings.keys().isdisjoint(_VALIDATING_KEYWORDS):
            annotations: dict[str, JsonValueType] = {
                key: value
                for key, value in reference_siblings.items()
                if key in ANNOTATION_KEYWORDS
            }
            _check_siblings(annotations, path=path)
            return node

        return _ref_under_all_of(
            node.ref,
            siblings=reference_siblings,
            path=path,
        )

    ref: str | None = _schema_ref(node, path=path)
    if ref is None:
        return _normalize_children(node, path=path)

    siblings: dict[str, JsonValueType] = _ref_siblings(node)
    if siblings.keys().isdisjoint(_VALIDATING_KEYWORDS):
        return Reference.model_validate({_REF_KEY: ref, **siblings})

    return _ref_under_all_of(
        ref,
        siblings=siblings,
        path=path,
    )


def _schema_ref(schema: Schema, /, *, path: Sequence[str]) -> str | None:
    extra: dict[str, JsonValueType] = schema.model_extra or {}
    if _REF_KEY not in extra:
        return None

    ref: JsonValueType = extra[_REF_KEY]
    if not isinstance(ref, str):
        msg = f"`{_REF_KEY}` must be a string, got `{ref!r}`"
        raise SchemaReferenceError(
            message=msg,
            path=list(path),
        )

    return ref


def _ref_siblings(schema: Schema, /) -> dict[str, JsonValueType]:
    siblings: dict[str, JsonValueType] = schema.model_dump(
        by_alias=True,
        exclude_unset=True,
    )
    del siblings[_REF_KEY]
    return siblings


def _check_siblings(siblings: dict[str, JsonValueType], /, *, path: Sequence[str]) -> None:
    try:
        Schema.model_validate(siblings)
    except ValidationError as er:
        error = er.errors()[0]
        # Only the keyword: below `pydantic` 2.14 the location goes on into the union member,
        #  `title.str` for `title: 5`.
        keyword: str = str(error["loc"][0])
        msg: str = f"Invalid keyword beside `{_REF_KEY}` at `{keyword}`: {error['msg']}"
        raise SchemaReferenceError(
            message=msg,
            path=list(path),
        ) from er


def _ref_under_all_of(
    ref: str,
    /,
    *,
    siblings: dict[str, JsonValueType],
    path: Sequence[str],
) -> Schema:
    _check_siblings(siblings, path=path)

    own_branch: dict[str, JsonValueType] = {
        key: value for key, value in siblings.items() if key in _OWN_BRANCH_KEYWORDS
    }
    rest: dict[str, JsonValueType] = {
        key: value for key, value in siblings.items() if key not in _OWN_BRANCH_KEYWORDS
    }
    all_of: list[JsonValueType] = [{_REF_KEY: ref}, *rest.get("allOf", [])]
    if own_branch:
        all_of.insert(1, own_branch)

    return _normalize_children(Schema.model_validate({**rest, "allOf": all_of}), path=path)


def _normalize_children(schema: Schema, /, *, path: Sequence[str]) -> Schema:
    update: dict[str, JsonValueType] = {}
    set_fields: set[str] = schema.model_fields_set
    for name, field in type(schema).model_fields.items():
        # Every field defaults to `MISSING`, so an unset one holds no subschema, and walking all
        #  of them made `to_model` of a wide schema about a third slower.
        if name not in set_fields:
            continue

        value: JsonValueType = getattr(schema, name)
        normalized: JsonValueType = _normalize_value(
            value,
            path=path,
            segment=field.alias or name,
        )

        if normalized is not value:
            update[name] = normalized

    if not update:
        return schema

    return schema.model_copy(update=update)


def _normalize_value(
    value: JsonValueType,
    /,
    *,
    path: Sequence[str],
    segment: str,
) -> JsonValueType:
    if isinstance(value, Schema | Reference):
        return _normalize_node(value, path=[*path, segment])

    if isinstance(value, list):
        items: list[JsonValueType] = [
            _normalize_value(
                item,
                path=path,
                segment=f"{segment}[{index}]",
            )
            for index, item in enumerate(value)
        ]
        unchanged: bool = all(new is old for new, old in zip(items, value, strict=True))
        return value if unchanged else items

    if isinstance(value, dict):
        entries: dict[str, JsonValueType] = {
            key: _normalize_value(
                item,
                path=path,
                segment=f"{segment}.{key}",
            )
            for key, item in value.items()
        }
        unchanged = all(entries[key] is item for key, item in value.items())
        return value if unchanged else entries

    return value
