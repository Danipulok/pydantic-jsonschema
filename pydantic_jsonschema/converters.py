"""Convert a JSON Schema `Schema` into a Pydantic model (`to_model` / `SchemaConverter`)."""

# NOTE: `Schema` fields use `X | MISSING` unions (see `_schema.py`). mypy doesn't
# recognize `MISSING` as a type, so it infers fields without the `Sentinel` branch
# and flags every `is not MISSING` check as a non-overlapping identity comparison.
# mypy: disable-error-code="comparison-overlap"

from collections.abc import Iterator
from contextlib import contextmanager
from types import NoneType
from typing import (
    Annotated,
    Any,
    Final,
    ForwardRef,
    Literal,
    Protocol,
    TypeAliasType,
    TypedDict,
    Union,
    cast,
    get_origin,
)

import annotated_types
from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    RootModel,
    create_model,
    model_validator,
)
from pydantic.experimental.missing_sentinel import MISSING
from pydantic.fields import FieldInfo

from ._contains import Contains
from ._not import Not
from ._one_of import OneOf
from ._prefix_items import PrefixItems
from ._utils import sanitize_identifier
from .exceptions import SchemaConversionError, SchemaReferenceError
from .types import DataType, Reference, Schema

__all__ = [
    "SchemaConverter",
    "to_model",
]


# Default model name
_DEFAULT_MODEL_NAME: Final[str] = "Model"
# Missing value for `default` field
# See: https://github.com/pydantic/pydantic/blob/6800281ba87625346daf5826563740ded8a9851b/pydantic/fields.py#L241-L247
# For mypy issue, see: https://github.com/python/mypy/issues/7818
_PYDANTIC_DEFAULT_MISSING: Final[Ellipsis] = ...  # type: ignore[valid-type]
# JSON Schema 2020-12 definitions key
# See: https://json-schema.org/draft/2020-12/json-schema-core#section-8.2.4
_DEFS_KEY: Final[str] = "$defs"
# A discriminated union needs at least two members for Pydantic to tag-dispatch.
_MIN_DISCRIMINATED_UNION_MEMBERS: Final[int] = 2

# NOTE: `ARRAY` / `OBJECT` entries are only reachable from multi-type unions
# (`{"type": ["object", "string"]}`) — single `array` / `object` schemas are handled
# by `_type_annotation` before the mapping is consulted.
# `OBJECT` must not map to `Any`: `Union[Any, str]` collapses to `Any`,
# and the union stops rejecting anything.
_DATA_TYPE_ANNOTATION_MAPPING: Final[dict[DataType, type]] = {
    DataType.NULL: NoneType,
    DataType.STRING: str,
    DataType.NUMBER: float,
    DataType.INTEGER: int,
    DataType.BOOLEAN: bool,
    DataType.ARRAY: list[Any],
    DataType.OBJECT: dict[str, Any],
}

# Type aliases
type Ref = str  # Reference path like "#/$defs/User"
type SchemaHash = str  # Schema cache key (JSON hash)
type FormatName = str  # Format name like "date-time", "uuid"
type AnnotationType = Any  # `type`, `Annotated`, `Union`, `Literal`, `ForwardRef`, etc.
type PythonType = Any  # Anything that Pydantic supports
type FieldKindType = Literal["required", "optional", "root"]  # How a field is used in a model
type FormatValidatorType = (
    FormatValidator | type | TypeAliasType
)  # `FormatValidator`, type, or `type` alias
type TagType = str | int | None  # Scalar discriminator tag value (`bool` is an `int`)


class FormatValidator(Protocol):
    """Callable that validates a raw value for a JSON Schema `format`.

    This describes the *callable* form of a `format_validators` entry (a value may also be a
    Pydantic type or an `Annotated` type). The callable receives the raw input before
    Pydantic's standard validation and returns the validated value, or raises `ValueError`.

    See [validation §7.1](https://json-schema.org/draft/2020-12/json-schema-validation#section-7.1).

    For Pydantic validators, see
    [annotated validators](https://docs.pydantic.dev/latest/concepts/validators/#annotated-validators)
    and [after validators](https://docs.pydantic.dev/latest/concepts/validators/#after-validators).
    """

    # NOTE: `value` must stay `Any`-typed: protocol parameters are contravariant,
    # so narrowing it (e.g. to `JsonValue`) stops narrow user validators like
    # `def validate_sku(value: str) -> str` from matching the protocol.
    #
    # Reproduce with `value: JsonValue`:
    #   uv run mypy examples/custom_validators.py
    #   # -> error: Dict entry 0 has incompatible type "str": "Callable[[str], str]"
    def __call__(
        self,
        value: PythonType,
    ) -> PythonType:
        """Process the raw value before Pydantic's standard validation."""
        ...


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


def _ensure_unique_items(value: list[PythonType], /) -> list[PythonType]:
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
    seen: list[PythonType] = []
    for item in value:
        if item in seen:
            msg = "Array items must be unique"
            raise ValueError(msg)
        seen.append(item)
    return value


def _annotate(annotation: AnnotationType, metadata: list[PythonType], /) -> type:
    """Wrap an annotation with `Annotated` metadata (validators / constraints).

    :param annotation: Base annotation (e.g. `list[int]`, `dict[str, int]`).
    :param metadata: `Annotated` metadata to attach (empty -> annotation returned as-is).
    :returns: The annotation, wrapped only when there is metadata to attach.
    """
    if not metadata:
        return cast("type", annotation)
    return cast("type", Annotated[(annotation, *metadata)])


def _array_metadata(schema: Schema, /) -> list[PythonType]:
    """`Annotated` metadata for array constraint keywords.

    :param schema: Array schema.
    :returns: Metadata for the array's `list[...]` annotation (add a keyword's check here).
    """
    metadata: list[PythonType] = []
    # `uniqueItems: false` (and absent) imposes no constraint; only `true` enforces.
    if schema.unique_items is True:
        metadata.append(AfterValidator(_ensure_unique_items))
    return metadata


def _object_dict_metadata(schema: Schema, /) -> list[PythonType]:
    """`Annotated` metadata for object keywords on a `dict` mapping (no declared properties).

    :param schema: Object schema mapped to `dict[str, ...]`.
    :returns: Length metadata for `minProperties` / `maxProperties` (add a keyword's check here).
    """
    metadata: list[PythonType] = []
    if schema.min_properties is not MISSING:
        metadata.append(annotated_types.MinLen(schema.min_properties))
    if schema.max_properties is not MISSING:
        metadata.append(annotated_types.MaxLen(schema.max_properties))
    return metadata


def _property_count_validator(schema: Schema, /) -> PythonType | None:
    """`minProperties` / `maxProperties`: bound the number of properties of an object model.

    Counts the raw input mapping's keys before field parsing. That key count is exactly the
    JSON Schema "number of properties" (declared fields plus `extra` keys) and is unambiguous
    regardless of which keys map to declared fields (validation §6.5.1 / §6.5.2).

    :param schema: Object schema.
    :returns: A `model_validator(mode="before")`, or `None` when neither bound is set.
    """
    min_properties = schema.min_properties if schema.min_properties is not MISSING else None
    max_properties = schema.max_properties if schema.max_properties is not MISSING else None
    if min_properties is None and max_properties is None:
        return None

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

    return model_validator(mode="before")(_check)


def _dependent_required_validator(schema: Schema, /) -> PythonType | None:
    """`dependentRequired`: when a property is present, the listed properties are required too.

    Checks the raw input mapping keys before field parsing, so it sees every present property
    (declared fields plus `extra` keys) (validation §6.5.4).

    :param schema: Object schema.
    :returns: A `model_validator(mode="before")`, or `None` when the keyword is absent.
    """
    if schema.dependent_required is MISSING:
        return None

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

    return model_validator(mode="before")(_check)


class _ObjectValidatorBuilder(Protocol):
    """Builds a `model_validator` for one object keyword, or `None` when the schema omits it."""

    # Each builder is a module-level function; its name is the `__validators__` key.
    __name__: str

    def __call__(self, schema: Schema, /) -> PythonType | None:
        """Return the keyword's validator for `schema`, or `None` to skip it."""
        ...


# Registry of object-model validators. To support a new object-level keyword, write a
# builder `(schema) -> validator | None` and add it here — no other wiring is needed.
_OBJECT_MODEL_VALIDATORS: Final[tuple[_ObjectValidatorBuilder, ...]] = (
    _property_count_validator,
    _dependent_required_validator,
)


def _build_object_validators(schema: Schema, /) -> dict[str, PythonType]:
    """Collect the `model_validator`s for an object model from the keyword registry.

    :param schema: Object schema to read keywords from.
    :returns: A `create_model(__validators__=...)` mapping (empty when no keyword applies).
    """
    validators: dict[str, PythonType] = {}
    for builder in _OBJECT_MODEL_VALIDATORS:
        validator = builder(schema)
        if validator is not None:
            validators[builder.__name__] = validator
    return validators


class SchemaConverter:
    """Stateful converter from JSON Schema to Pydantic models."""

    def __init__(
        self,
        *,
        default_model_name: str = _DEFAULT_MODEL_NAME,
        refs: dict[Ref, type[BaseModel]] | None = None,
        format_validators: dict[FormatName, FormatValidatorType] | None = None,
    ) -> None:
        """Initialize converter with optional pre-built refs and format validators.

        :param default_model_name: Fallback name for models without `title` (default: `Model`).
        :param refs: Pre-built Pydantic models for `$ref` resolution.
        :param format_validators: Validators keyed by JSON Schema `format` value.
        """
        self._default_model_name: str = default_model_name
        self._refs: dict[Ref, type[BaseModel]] = refs or {}
        self._format_validators: dict[FormatName, FormatValidatorType] = format_validators or {}

        self._defs_cache: dict[Ref, Schema] = {}
        self._models_cache: dict[SchemaHash, type[BaseModel]] = {}
        self._resolution_path: list[str] = []  # Track path for error reporting
        self._one_of_validators: list[OneOf] = []
        self._contains_validators: list[Contains] = []
        self._prefix_items_validators: list[PrefixItems] = []
        self._not_validators: list[Not] = []

    @staticmethod
    def _hash_schema(
        schema: Schema,
        /,
    ) -> SchemaHash:
        """Get cache key for schema.

        :param schema: Schema to hash.
        :returns: hash string (using JSON representation).
        """
        return schema.model_dump_json(exclude_unset=True)

    @contextmanager
    def _track_path(
        self,
        segment: str,
        /,
    ) -> Iterator[None]:
        """Context manager for tracking resolution path.

        :param segment: Path segment to add.
        :yields: None
        """
        self._resolution_path.append(segment)
        try:
            yield
        finally:
            self._resolution_path.pop()

    def convert_schema(
        self,
        schema: Schema,
        /,
        *,
        model_name: str | None = None,
    ) -> type[BaseModel]:
        """Convert JSON Schema (root schema) to Pydantic model.

        :param schema: Schema to convert.
        :param model_name: Name for the generated model.
        :returns: Pydantic model class.
        :raises SchemaConversionError: If schema cannot be converted.
        """
        # Build defs cache from `$defs`
        self._build_defs_cache(schema)

        # Build model using common logic
        model = self._build_model(schema, model_name=model_name)

        # A root object becomes a plain `BaseModel` (not a `RootModel`), so it bypasses the
        # annotation path where `not` is otherwise attached — wrap it explicitly here. Every
        # other shape (root non-object / dict-root, and all nested values) carries `not` via
        # its annotation already.
        if schema.not_ is not MISSING and not issubclass(model, RootModel):
            model = self._wrap_root_not(model, schema)

        # Bind the forward-refs namespace so `OneOf` / `Contains` validators can resolve
        # `ForwardRef` branches lazily at validation time.
        namespace = self._get_forward_refs_namespace()
        for one_of_validator in self._one_of_validators:
            one_of_validator.bind_namespace(namespace)
        for contains_validator in self._contains_validators:
            contains_validator.bind_namespace(namespace)
        for prefix_items_validator in self._prefix_items_validators:
            prefix_items_validator.bind_namespace(namespace)
        for not_validator in self._not_validators:
            not_validator.bind_namespace(namespace)

        return model

    def _convert_nested_schema(
        self,
        schema: Schema,
        /,
        *,
        model_name: str | None = None,
    ) -> type[BaseModel]:
        """Convert JSON Schema to Pydantic model (for nested/def schemas).

        :param schema: Schema to convert.
        :param model_name: Name for the generated model.
        :returns: Pydantic model class.
        :raises SchemaConversionError: If schema contains `$defs` (only allowed in root).
        """
        # Validate that `$defs` is not present in nested schemas
        if schema.defs is not MISSING:
            msg = f"{_DEFS_KEY} is only allowed in root schema, not in nested schemas"
            raise SchemaConversionError(msg)

        # Build model using common logic
        return self._build_model(schema, model_name=model_name)

    def _build_model(
        self,
        schema: Schema,
        /,
        *,
        model_name: str | None = None,
    ) -> type[BaseModel]:
        """Build Pydantic model from schema (common logic for root and nested).

        Models are cached by schema hash, so each schema is built at most once.

        :param schema: Schema to convert.
        :param model_name: Name for the generated model.
        :returns: Pydantic model class.
        """
        cache_key = self._hash_schema(schema)
        if cache_key in self._models_cache:
            return self._models_cache[cache_key]

        title: str = schema.title if schema.title is not MISSING else ""
        name: str = model_name or sanitize_identifier(title) or self._default_model_name

        model = self._create_model(schema, model_name=name)
        self._models_cache[cache_key] = model
        return model

    def _create_model(
        self,
        schema: Schema,
        /,
        *,
        model_name: str,
    ) -> type[BaseModel]:
        """Pick the model flavor for the schema and build it.

        :param schema: Schema to convert.
        :param model_name: Name for the generated model.
        :returns: Pydantic model class.
        """
        # Handle `allOf` composition -> base classes
        base_classes = self._get_base_classes(schema)

        # Non-object types -> `RootModel`.
        if schema.type != DataType.OBJECT:
            # `allOf` base already wraps the value (e.g. a string `RootModel`).
            if schema.all_of is not MISSING and base_classes:
                return base_classes[0]
            return self._create_root_model(schema, model_name=model_name)

        # Root object without `properties` but with schema-valued `additionalProperties`
        # -> `RootModel[dict[str, ...]]`, so values are validated the same way as in
        # nested objects (a plain `BaseModel` with `extra="allow"` would not check them).
        if (
            schema.properties is MISSING
            and schema.all_of is MISSING
            and isinstance(schema.additional_properties, (Schema, Reference))
        ):
            return self._create_root_model(schema, model_name=model_name)

        # `allOf` without own properties -> combined base class
        if schema.all_of is not MISSING and schema.properties is MISSING:
            return self._combine_base_classes(base_classes, model_name=model_name)

        return self._create_object_model(
            schema,
            model_name=model_name,
            base_classes=base_classes,
        )

    @staticmethod
    def _combine_base_classes(
        base_classes: tuple[type[BaseModel], ...],
        /,
        *,
        model_name: str,
    ) -> type[BaseModel]:
        """Combine `allOf` base classes into a single model.

        :param base_classes: Models generated from `allOf` sub-schemas.
        :param model_name: Name for the combined model.
        :returns: The single base as-is, or a new class inheriting all bases.
        """
        if len(base_classes) == 1:
            return base_classes[0]

        created_model = type(model_name, base_classes, {"__module__": __name__})
        return cast("type[BaseModel]", created_model)

    def _create_object_model(
        self,
        schema: Schema,
        /,
        *,
        model_name: str,
        base_classes: tuple[type[BaseModel], ...],
    ) -> type[BaseModel]:
        """Create a model with fields from an object schema.

        :param schema: Object schema to convert.
        :param model_name: Name for the generated model.
        :param base_classes: Base classes from `allOf` composition.
        :returns: Pydantic model class.
        """
        fields = self._build_fields(schema)
        model_config = self._build_model_config(schema)
        validators = _build_object_validators(schema)

        # For some reason, `create_model` "accepts" `fields` values as `tuple[str, Any]`,
        # when in reality it accepts `tuple[type, FieldInfo]`
        created_model = create_model(  # type: ignore[call-overload]
            model_name,
            __config__=model_config,
            __doc__=schema.description if schema.description is not MISSING else None,
            __base__=base_classes,
            __module__=__name__,
            __validators__=validators,
            **fields,
        )
        return cast("type[BaseModel]", created_model)

    def _check_alias_target(
        self,
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
        local_ref_prefix: str = f"#/{_DEFS_KEY}/"

        if not reference.ref.startswith(local_ref_prefix):
            msg = (
                f"Cannot resolve {_DEFS_KEY} alias `{alias_name}`: "
                f"external reference `{reference.ref}`"
            )
            raise SchemaReferenceError(
                message=msg,
                path=seen_names.copy(),
            )

        target_name: str = reference.ref.removeprefix(local_ref_prefix)
        if target_name in seen_names:
            msg = f"Circular {_DEFS_KEY} alias chain: {' -> '.join([*seen_names, target_name])}"
            raise SchemaReferenceError(
                message=msg,
                path=seen_names.copy(),
            )

        if target_name not in defs:
            msg = (
                f"Cannot resolve {_DEFS_KEY} alias `{alias_name}`: unknown target `{reference.ref}`"
            )
            raise SchemaReferenceError(
                message=msg,
                path=seen_names.copy(),
            )

        return target_name

    def _resolve_def_alias(
        self,
        defs: dict[str, Schema | Reference],
        /,
        *,
        name: str,
    ) -> Schema:
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
            target_name = self._check_alias_target(
                defs,
                reference=current,
                seen_names=seen_names,
            )
            seen_names.append(target_name)
            current = defs[target_name]

        return current

    def _get_inline_defs(
        self,
        schema: Schema,
        /,
    ) -> dict[Ref, Schema]:
        """Extract inline schema defs from `$defs` field.

        `Reference` entries (def aliases) are resolved to their target schemas.

        :param schema: Schema to extract defs from.
        :returns: Mapping of reference paths to schemas.
        :raises SchemaReferenceError: If a def alias cannot be resolved.
        """
        if schema.defs is MISSING:
            return {}

        result_defs: dict[Ref, Schema] = {}
        for name in schema.defs:
            ref_path = f"#/{_DEFS_KEY}/{name}"
            result_defs[ref_path] = self._resolve_def_alias(
                schema.defs,
                name=name,
            )
        return result_defs

    def _build_defs_cache(
        self,
        schema: Schema,
        /,
    ) -> None:
        """Build defs cache from schema `$defs` field.

        :param schema: Schema to extract defs from.
        :returns: None
        """
        defs = self._get_inline_defs(schema)

        for ref, schema_def in defs.items():
            # Store in defs cache
            self._defs_cache[ref] = schema_def
            # Convert and cache nested models
            self._convert_nested_schema(schema_def)

        self._rebuild_def_models(defs)

    def _rebuild_def_models(
        self,
        defs: dict[Ref, Schema],
        /,
    ) -> None:
        """Re-resolve `ForwardRef` annotations in def models.

        :param defs: Definitions whose models should be rebuilt.
        """
        forward_refs = self._get_forward_refs_namespace()
        for ref in defs:
            self._get_model(ref).model_rebuild(_types_namespace=forward_refs)

    def _get_forward_refs_namespace(self) -> dict[str, type[BaseModel]]:
        """Get namespace for forward reference resolution."""
        namespace: dict[str, type[BaseModel]] = {
            sanitize_identifier(ref): self._get_model(ref) for ref in self._defs_cache
        }

        # Pre-built ref models take precedence over generated ones.
        for ref, model in self._refs.items():
            namespace[sanitize_identifier(ref)] = model

        return namespace

    def _get_model(
        self,
        ref: Ref,
        /,
    ) -> type[BaseModel]:
        """Get or generate Pydantic model for reference.

        :param ref: Reference path (e.g., "#/$defs/User").
        :returns: Pydantic model (from cache or generated).
        :raises SchemaReferenceError: If reference cannot be resolved.
        """
        # Check if pre-built model exists
        if ref in self._refs:
            return self._refs[ref]

        # Try to resolve schema from defs
        if ref not in self._defs_cache:
            path_str = " -> ".join(self._resolution_path) if self._resolution_path else "root"
            msg = f"Cannot resolve reference `{ref}` at path: `{path_str}`"
            raise SchemaReferenceError(
                message=msg,
                path=self._resolution_path.copy(),
            )

        # `_build_model` handles model caching by schema hash.
        schema = self._defs_cache[ref]
        return self._convert_nested_schema(schema)

    def _get_base_classes(
        self,
        schema: Schema,
        /,
    ) -> tuple[type[BaseModel], ...]:
        """Get base classes from `allOf` composition.

        :param schema: Schema to extract base classes from.
        :returns: Tuple of base classes.
        """
        if schema.all_of is MISSING:
            return (BaseModel,)

        # Convert each `allOf` schema to model
        base_models = []
        for index, sub_schema in enumerate(schema.all_of):
            with self._track_path(f"allOf[{index}]"):
                if isinstance(sub_schema, Reference):
                    model = self._get_model(sub_schema.ref)
                else:
                    model = self._convert_nested_schema(sub_schema)
                base_models.append(model)

        return tuple(base_models)

    def _create_root_model(
        self,
        schema: Schema,
        /,
        *,
        model_name: str,
    ) -> type[BaseModel]:
        """Create `RootModel` wrapping the schema's value annotation.

        :param schema: Schema describing the root value.
        :param model_name: Name for the generated model.
        :returns: `RootModel` subclass.
        """
        field = self._schema_to_field(schema, field_kind="root")

        created_model = type(
            model_name,
            (RootModel,),
            {
                "root": field,
                "__annotations__": {"root": field.annotation},
                "__module__": __name__,
            },
        )
        return cast("type[BaseModel]", created_model)

    def _build_fields(
        self,
        schema: Schema,
        /,
    ) -> dict[str, tuple[Any, FieldInfo]]:
        """Build Pydantic fields from schema properties."""
        fields: dict[str, tuple[Any, FieldInfo]] = {}

        properties: dict[str, Reference | Schema] = (
            schema.properties if schema.properties is not MISSING else {}
        )
        required_names: list[str] = schema.required if schema.required is not MISSING else []

        for field_name, field_schema in properties.items():
            with self._track_path(f"properties.{field_name}"):
                # Handle reference fields
                annotation: AnnotationType | None = None
                schema_for_field: Schema

                if isinstance(field_schema, Reference):
                    # Get model for annotation
                    annotation = self._get_model(field_schema.ref)
                    # Use schema from defs for field metadata, or empty schema
                    schema_for_field = self._defs_cache.get(field_schema.ref, Schema())
                else:
                    schema_for_field = field_schema

                # Convert to Pydantic field
                field = self._schema_to_field(
                    schema_for_field,
                    field_kind="required" if field_name in required_names else "optional",
                    annotation=annotation,
                )

                fields[field_name] = (field.annotation, field)

        return fields

    def _apply_validators(
        self,
        annotation: AnnotationType,
        schema: Schema,
        /,
    ) -> AnnotationType:
        """Apply validator to annotation.

        Handles these validator kinds:
        - `type` aliases (the built-in format types): unwrapped to their underlying
          `Annotated` / type, then handled like the cases below.
        - Annotated types: used directly as annotation (replaces original).
        - Type classes: used directly as annotation (replaces original).
        - Callables: wrapped with `BeforeValidator`.

        :param annotation: Original annotation.
        :param schema: Schema to check for format.
        :returns: Annotation with validator applied if applicable.
        """
        if schema.format is MISSING or schema.format not in self._format_validators:
            return annotation

        validator = self._format_validators[schema.format]

        # Built-in format types (`Email`, `UUID`, ...) are PEP 695 `type` aliases, i.e.
        # `TypeAliasType`. Unwrap to the actual `Annotated` / class they alias so the field
        # annotation stays clean (`str`, `uuid.UUID`) instead of the alias wrapper.
        if isinstance(validator, TypeAliasType):
            validator = validator.__value__

        if get_origin(validator) is Annotated:
            return validator

        if isinstance(validator, type):
            return validator

        return Annotated[annotation, BeforeValidator(validator)]

    @staticmethod
    def _build_model_config(
        schema: Schema,
        /,
    ) -> ConfigDict:
        """Build model config from schema."""
        config: ConfigDict = {}

        # Handle `additionalProperties`
        if schema.additional_properties is False:
            config["extra"] = "forbid"
        else:
            config["extra"] = "allow"

        return config

    def _schema_to_field(
        self,
        schema: Schema,
        /,
        *,
        field_kind: FieldKindType,
        annotation: AnnotationType | None = None,
    ) -> FieldInfo:
        """Convert schema to Pydantic FieldInfo.

        :param schema: Schema to convert.
        :param field_kind: `required` / `optional` object property, or `root` model value.
        :param annotation: Pre-computed annotation.
        :returns: Pydantic FieldInfo.
        """
        # Get annotation if not provided
        if annotation is None:
            valid_annotation: AnnotationType = self._schema_to_annotation(schema)
        else:
            valid_annotation = annotation

        # Apply validators
        valid_annotation = self._apply_validators(valid_annotation, schema)

        # Determine default value
        default = self._get_field_default(schema, field_kind=field_kind)

        # `MISSING` must be part of the annotation for Pydantic to accept it as default.
        if default is MISSING:
            valid_annotation = valid_annotation | MISSING

        return FieldInfo(
            annotation=valid_annotation,
            default=default,
            **self._build_field_kwargs(schema),
        )

    def _build_field_kwargs(  # noqa: C901
        self,
        schema: Schema,
        /,
    ) -> _FieldKwargs:
        """Build `FieldInfo` kwargs, only including constraints that are explicitly set.

        :param schema: Schema to extract constraints and metadata from.
        :returns: Keyword arguments for `FieldInfo`.
        """
        kwargs: _FieldKwargs = {}
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

        min_length = self._get_min_length(schema)
        if min_length is not None:
            kwargs["min_length"] = min_length

        max_length = self._get_max_length(schema)
        if max_length is not None:
            kwargs["max_length"] = max_length

        return kwargs

    def _union_args(
        self,
        union_schemas: list[Schema | Reference],
        /,
        *,
        kind: Literal["anyOf", "oneOf"],
    ) -> list[type | ForwardRef]:
        """Convert union sub-schemas to annotations.

        :param union_schemas: Sub-schemas of an `anyOf` / `oneOf` composition.
        :param kind: Composition keyword for path tracking (`anyOf` or `oneOf`).
        :returns: Annotations for every sub-schema.
        """
        union_args: list[type | ForwardRef] = []
        for index, sub_schema in enumerate(union_schemas):
            with self._track_path(f"{kind}[{index}]"):
                union_args.append(self._schema_to_annotation(sub_schema))
        return union_args

    def _schema_to_annotation(
        self,
        schema: Schema | Reference,
        /,
    ) -> type | ForwardRef:
        """Convert schema to Python type annotation.

        :param schema: Schema to convert.
        :returns: Type annotation.
        """
        if isinstance(schema, Reference):
            return self._reference_annotation(schema)

        # `enum` / `const` -> `Literal`:
        if schema.enum is not MISSING or schema.const is not MISSING:
            annotation: type | ForwardRef = self._literal_annotation(schema)
        else:
            # `anyOf` / `oneOf` / `allOf` -> union or nested model; else `type` (or `Any`).
            composition_annotation = self._composition_annotation(schema)
            annotation = (
                composition_annotation
                if composition_annotation is not None
                else self._type_annotation(schema)
            )

        # `not` is checked against the raw value before the host type (a wrap-validator).
        if schema.not_ is not MISSING:
            annotation = self._apply_not(annotation, schema)

        return annotation

    def _apply_not(
        self,
        annotation: AnnotationType,
        schema: Schema,
        /,
    ) -> type:
        """Wrap a value annotation with the `not` check.

        :param annotation: The value's base annotation.
        :param schema: Schema carrying `not`.
        :returns: `Annotated[annotation, Not(...)]`.
        """
        not_validator = self._build_not(schema)
        return cast("type", Annotated[annotation, not_validator])

    def _build_not(
        self,
        schema: Schema,
        /,
    ) -> Not:
        """Build the `not` validator, registering it for namespace binding.

        :param schema: Schema carrying `not`.
        :returns: A `Not` validator for the subschema.
        """
        with self._track_path("not"):
            branch = self._schema_to_annotation(schema.not_)

        not_validator = Not(branch=branch)
        self._not_validators.append(not_validator)
        return not_validator

    def _wrap_root_not(
        self,
        model: type[BaseModel],
        schema: Schema,
        /,
    ) -> type[BaseModel]:
        """Wrap a root object model with a `before` validator enforcing `not`.

        :param model: The root object `BaseModel`.
        :param schema: Root schema carrying `not`.
        :returns: A subclass of `model` that rejects inputs matching the `not` subschema.
        """
        not_validator = self._build_not(schema)

        def _check(data: PythonType) -> PythonType:
            if not_validator.matches(data):
                msg = "Value must not match the `not` schema"
                raise ValueError(msg)
            return data

        validators: dict[str, PythonType] = {
            "_validate_not": model_validator(mode="before")(_check),
        }
        wrapped = create_model(
            model.__name__,
            __base__=model,
            __module__=__name__,
            __validators__=validators,
        )
        return cast("type[BaseModel]", wrapped)

    def _reference_annotation(
        self,
        reference: Reference,
        /,
    ) -> type | ForwardRef:
        """Resolve a reference to a model, or defer it via `ForwardRef`.

        :param reference: Reference to resolve.
        :returns: Resolved model or `ForwardRef` for later resolution.
        """
        if reference.ref in self._refs or reference.ref in self._defs_cache:
            return self._get_model(reference.ref)

        return ForwardRef(sanitize_identifier(reference.ref))

    @staticmethod
    def _literal_annotation(
        schema: Schema,
        /,
    ) -> type:
        """Convert `enum` / `const` to a `Literal` annotation.

        :param schema: Schema with `enum` or `const` set.
        :returns: `Literal` annotation.
        """
        values = schema.enum if schema.enum is not MISSING else (schema.const,)
        literal_type = Literal[tuple(values)]  # type: ignore[valid-type]
        return cast("type", literal_type)

    def _composition_annotation(
        self,
        schema: Schema,
        /,
    ) -> type | None:
        """Convert `anyOf` / `oneOf` / `allOf` composition to an annotation.

        :param schema: Schema to convert.
        :returns: Annotation, or `None` if the schema has no composition keyword.
        """
        # `anyOf` -> `Union`:
        if schema.any_of is not MISSING:
            union_args = self._union_args(schema.any_of, kind="anyOf")
            union_annotation = Union[tuple(union_args)]  # type: ignore[valid-type]  # noqa: UP007
            return cast("type", union_annotation)

        # `oneOf` -> discriminated union or exactly-one-branch validation:
        if schema.one_of is not MISSING:
            return self._one_of_annotation(schema)

        # `allOf` -> nested model:
        if schema.all_of is not MISSING:
            return self._convert_nested_schema(schema)

        return None

    def _one_of_annotation(
        self,
        schema: Schema,
        /,
    ) -> type:
        """Convert a `oneOf` composition to an annotation.

        When all branches are object schemas tagged by a shared discriminator
        property, the union maps to a native Pydantic discriminated (tagged) union
        via `Field(discriminator=...)`:
        Pydantic routes to a single branch by the tag value instead of probing
        every branch, which is faster and yields branch-specific errors.

        Otherwise it falls back to the `OneOf` wrap-validator,
        which enforces exactly-one-branch semantics by probing.

        :param schema: Schema with `oneOf` set.
        :returns: Discriminated `Union` annotation or `OneOf`-wrapped union.
        """
        union_args = self._union_args(schema.one_of, kind="oneOf")
        discriminator = self._discriminator_property(schema.one_of)

        # A discriminated union needs >= 2 concrete members to introspect the tag field.
        # Unresolved `ForwardRef` branches keep the `OneOf` lazy path.
        if (
            discriminator is not None
            and len(union_args) >= _MIN_DISCRIMINATED_UNION_MEMBERS
            and not any(isinstance(arg, ForwardRef) for arg in union_args)
        ):
            union_annotation = Union[tuple(union_args)]  # type: ignore[valid-type]  # noqa: UP007
            discriminated = Annotated[union_annotation, Field(discriminator=discriminator)]  # type: ignore[valid-type]
            return cast("type", discriminated)

        one_of_validator = OneOf(branches=union_args)
        self._one_of_validators.append(one_of_validator)
        return cast("type", one_of_validator.as_annotation())

    def _discriminator_property(
        self,
        one_of_schemas: list[Schema | Reference],
        /,
    ) -> str | None:
        """Find the property that tags every `oneOf` branch with a distinct constant.

        A property qualifies as a discriminator when, in *every* branch, it is a required
        property whose schema is a single constant (`const` or single-value `enum`),
        and its constant value is distinct across branches.

        :param one_of_schemas: Sub-schemas of the `oneOf` composition.
        :returns: The discriminator property name, or `None` when zero or more than
            one property qualifies (ambiguous discriminators stay on the `OneOf` path).
        """
        branch_count: int = len(one_of_schemas)

        # Collect each branch's tag value per property name.
        tags_by_property: dict[str, list[TagType]] = {}
        for branch in one_of_schemas:
            branch_schema = self._resolve_branch_schema(branch)
            if branch_schema is None or branch_schema.properties is MISSING:
                return None

            for name, tag in self._branch_tag_values(branch_schema).items():
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
        self,
        branch: Schema | Reference,
        /,
    ) -> Schema | None:
        """Resolve a `oneOf` branch to a concrete object schema, if known.

        :param branch: A `oneOf` sub-schema or reference.
        :returns: The inline schema, the cached schema for a local `$ref`, or `None`
            when the reference can't be introspected (external / forward / pre-built).
        """
        if isinstance(branch, Reference):
            return self._defs_cache.get(branch.ref)
        return branch

    @staticmethod
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
        required: set[str] = set(schema.required) if schema.required is not MISSING else set()
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

            # NOTE: Only scalar tags are accepted. `_discriminator_property` puts these
            # values in a `set()` to check distinctness across branches, so a non-hashable
            # `const` (array/object) would crash. `float` is excluded on purpose:
            # float-equality discrimination is fragile, so such unions fall back to `OneOf`.
            if isinstance(tag, (str, int, NoneType)):
                tags[name] = tag

        return tags

    def _type_annotation(
        self,
        schema: Schema,
        /,
    ) -> type:
        """Convert the `type` keyword to a Python type annotation.

        :param schema: Schema to convert.
        :returns: Type annotation (`Any` when `type` is absent).
        """
        if schema.type == DataType.ARRAY:
            return self._array_annotation(schema)

        if schema.type == DataType.OBJECT:
            return self._object_annotation(schema)

        if schema.type is not MISSING:
            if isinstance(schema.type, DataType):
                return _DATA_TYPE_ANNOTATION_MAPPING[schema.type]
            union_args = [_DATA_TYPE_ANNOTATION_MAPPING[data_type] for data_type in schema.type]
            union_annotation = Union[tuple(union_args)]  # type: ignore[valid-type]  # noqa: UP007
            return cast("type", union_annotation)

        return Any

    def _array_annotation(
        self,
        schema: Schema,
        /,
    ) -> type:
        """Convert an array schema to a `list` annotation, applying array constraints.

        :param schema: Array schema to convert.
        :returns: `list[...]` annotation, wrapped with array constraint metadata when set.
        """
        # With `prefixItems`, element types are positional, so the base stays `list[Any]` and
        # `PrefixItems` validates each position (including the `items` tail). Without it, `items`
        # is the homogeneous element type.
        prefix_items = self._build_prefix_items(schema)

        item_type: type | ForwardRef = Any
        if prefix_items is None and schema.items is not MISSING:
            with self._track_path("items"):
                item_type = self._schema_to_annotation(schema.items)
        list_annotation = list[item_type]  # type: ignore[valid-type]

        # `uniqueItems` is stateless; `contains` / `prefixItems` need the converter.
        metadata: list[PythonType] = _array_metadata(schema)
        if prefix_items is not None:
            metadata.append(prefix_items)
        contains = self._build_contains(schema)
        if contains is not None:
            metadata.append(contains)

        return _annotate(list_annotation, metadata)

    def _build_prefix_items(
        self,
        schema: Schema,
        /,
    ) -> PrefixItems | None:
        """Build the `prefixItems` positional validator for an array.

        Registers the validator so its `ForwardRef` subschemas (a prefix / tail pointing at a
        `$ref`) are namespace-bound after the whole schema is converted.

        :param schema: Array schema.
        :returns: A `PrefixItems` validator, or `None` when `prefixItems` is absent.
        """
        if schema.prefix_items is MISSING:
            return None

        prefixes: list[PythonType] = []
        for index, sub_schema in enumerate(schema.prefix_items):
            with self._track_path(f"prefixItems[{index}]"):
                prefixes.append(self._schema_to_annotation(sub_schema))

        tail: PythonType | None = None
        if schema.items is not MISSING:
            with self._track_path("items"):
                tail = self._schema_to_annotation(schema.items)

        prefix_items = PrefixItems(prefixes=prefixes, tail=tail)
        self._prefix_items_validators.append(prefix_items)
        return prefix_items

    def _build_contains(
        self,
        schema: Schema,
        /,
    ) -> Contains | None:
        """Build the `contains` / `minContains` / `maxContains` validator for an array.

        Registers the validator so its `ForwardRef` subschema (a `contains` pointing at a
        `$ref`) is namespace-bound after the whole schema is converted.

        :param schema: Array schema.
        :returns: A `Contains` validator, or `None` when `contains` is absent.
        """
        if schema.contains is MISSING:
            return None

        with self._track_path("contains"):
            branch = self._schema_to_annotation(schema.contains)

        # `minContains` defaults to 1; `maxContains` is unbounded when absent.
        min_contains = schema.min_contains if schema.min_contains is not MISSING else 1
        max_contains = schema.max_contains if schema.max_contains is not MISSING else None

        contains = Contains(branch=branch, min_contains=min_contains, max_contains=max_contains)
        self._contains_validators.append(contains)
        return contains

    def _object_annotation(
        self,
        schema: Schema,
        /,
    ) -> type:
        """Convert an object schema to a model or typed dict annotation.

        :param schema: Object schema to convert.
        :returns: Generated model or `dict[str, ...]` annotation.
        """
        if schema.properties is not MISSING:
            return self._convert_nested_schema(schema)

        if schema.additional_properties is False:
            return self._convert_nested_schema(schema)

        if isinstance(schema.additional_properties, (Schema, Reference)):
            with self._track_path("additionalProperties"):
                value_annotation = self._schema_to_annotation(schema.additional_properties)
                dict_annotation = dict[str, value_annotation]  # type: ignore[valid-type]
                return _annotate(dict_annotation, _object_dict_metadata(schema))

        return _annotate(dict[str, Any], _object_dict_metadata(schema))

    @staticmethod
    def _get_field_default(
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

    @staticmethod
    def _get_min_length(
        schema: Schema,
        /,
    ) -> int | None:
        """Get min length based on schema type.

        :param schema: Schema to extract constraint from.
        :returns: `minItems` for arrays, `minLength` for strings, `None` if unset.
        """
        if schema.type == DataType.ARRAY:
            return schema.min_items if schema.min_items is not MISSING else None
        return schema.min_length if schema.min_length is not MISSING else None

    @staticmethod
    def _get_max_length(
        schema: Schema,
        /,
    ) -> int | None:
        """Get max length based on schema type.

        :param schema: Schema to extract constraint from.
        :returns: `maxItems` for arrays, `maxLength` for strings, `None` if unset.
        """
        if schema.type == DataType.ARRAY:
            return schema.max_items if schema.max_items is not MISSING else None
        return schema.max_length if schema.max_length is not MISSING else None


def to_model(
    schema: Schema,
    /,
    *,
    model_name: str | None = None,
    refs: dict[Ref, type[BaseModel]] | None = None,
    format_validators: dict[FormatName, FormatValidatorType] | None = None,
) -> type[BaseModel]:
    """Convert schema to Pydantic model.

    :param schema: Schema to convert.
    :param refs: Pre-built reference models.
    :param format_validators: Custom format validators (callables, types, or Annotated).
    :param model_name: Name for the generated model.
    :returns: Pydantic model class.
    """
    converter = SchemaConverter(
        refs=refs,
        format_validators=format_validators,
    )
    return converter.convert_schema(schema, model_name=model_name)
