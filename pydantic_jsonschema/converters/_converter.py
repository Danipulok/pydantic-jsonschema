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
    Union,
    cast,
    get_origin,
)

from pydantic import (
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

from pydantic_jsonschema._markers import (
    Contains,
    DependentSchemas,
    IfThenElse,
    Not,
    OneOf,
    PatternProperties,
    PrefixItems,
    PropertyNames,
    SubschemaMarker,
)
from pydantic_jsonschema._utils import sanitize_identifier
from pydantic_jsonschema.exceptions import SchemaConversionError, SchemaReferenceError
from pydantic_jsonschema.types import DataType, Reference, Schema

from ._discriminator import discriminator_property
from ._field_kwargs import FieldKindType, build_field_kwargs, get_field_default
from ._metadata import annotate, array_metadata, object_dict_metadata
from ._object_keywords import build_dependent_required, build_property_count

__all__ = [
    "SchemaConverter",
    "to_model",
]


# Default model name
_DEFAULT_MODEL_NAME: Final[str] = "Model"
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
type FormatValidatorType = (
    FormatValidator | type | TypeAliasType
)  # `FormatValidator`, type, or `type` alias


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
        self._markers: list[SubschemaMarker] = []

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
        model = self._wrap_root_value_assertions(model, schema)
        self._bind_forward_refs()

        return model

    def _wrap_root_value_assertions(
        self,
        model: type[BaseModel],
        schema: Schema,
        /,
    ) -> type[BaseModel]:
        """Attach `not` / `if` / `then` / `else` to a root object model.

        A root object becomes a plain `BaseModel` (not a `RootModel`), so it bypasses the
        annotation path where these whole-value assertions are otherwise attached. Every other
        shape (root non-object / dict-root, and all nested values) carries them via its
        annotation already.

        :param model: The freshly built root model.
        :param schema: The root schema.
        :returns: The model, wrapped when it is a root object carrying whole-value assertions.
        """
        if issubclass(model, RootModel):
            return model

        if schema.not_ is not MISSING:
            model = self._wrap_root_assertion(model, self._build_not(schema), key="_validate_not")
        if self._has_conditional(schema):
            model = self._wrap_root_assertion(
                model,
                self._build_conditional(schema),
                key="_validate_conditional",
            )
        return model

    def _register[MarkerT: SubschemaMarker](
        self,
        marker: MarkerT,
        /,
    ) -> MarkerT:
        """Register a marker so its `ForwardRef` subschemas are namespace-bound after conversion.

        :param marker: The freshly built marker validator.
        :returns: The same marker, for inline use at the call site.
        """
        self._markers.append(marker)
        return marker

    def _bind_forward_refs(self) -> None:
        """Bind the forward-refs namespace into every marker validator.

        Lets `OneOf` / `Contains` / `Not` / ... resolve `ForwardRef` branches lazily at
        validation time, once the whole schema (including `$defs`) has been converted.
        """
        namespace = self._get_forward_refs_namespace()
        for marker in self._markers:
            marker.bind_namespace(namespace)

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
        validators = self._build_object_validators(schema)

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

    def _build_object_validators(
        self,
        schema: Schema,
        /,
    ) -> dict[str, PythonType]:
        """Collect the `model_validator`s for an object model from every keyword builder.

        Each `_build_*` builder returns a (possibly empty) `__validators__` fragment; merging them
        yields the full mapping. To support a new object-level keyword, add a builder and spread it
        here. Stateless builders are `@staticmethod`; converter-aware ones (subschemas need
        conversion + namespace binding) are instance methods.

        :param schema: Object schema to read keywords from.
        :returns: A `create_model(__validators__=...)` mapping (empty when no keyword applies).
        """
        return {
            **build_property_count(schema),
            **build_dependent_required(schema),
            **self._build_dependent_schemas(schema),
            **self._build_pattern_properties(schema),
            **self._build_property_names(schema),
        }

    def _build_dependent_schemas(
        self,
        schema: Schema,
        /,
    ) -> dict[str, PythonType]:
        """Build the `dependentSchemas` validator for an object model.

        Registers the validator so its `ForwardRef` subschemas (a dependent pointing at a `$ref`)
        are namespace-bound after the whole schema is converted.

        :param schema: Object schema.
        :returns: A `__validators__` mapping (empty when `dependentSchemas` is absent).
        """
        if schema.dependent_schemas is MISSING:
            return {}

        branches: dict[str, PythonType] = {}
        for trigger, sub_schema in schema.dependent_schemas.items():
            with self._track_path(f"dependentSchemas.{trigger}"):
                branches[trigger] = self._constrained_annotation(sub_schema)

        dependent_schemas = self._register(DependentSchemas(branches=branches))

        def _check(data: PythonType) -> PythonType:
            return dependent_schemas.validate(data)

        return {"_validate_dependent_schemas": model_validator(mode="before")(_check)}

    def _build_pattern_properties(
        self,
        schema: Schema,
        /,
    ) -> dict[str, PythonType]:
        """Build the `patternProperties` validator for an object model.

        Registers the validator so its `ForwardRef` subschemas (a pattern value pointing at a
        `$ref`) are namespace-bound after the whole schema is converted.

        :param schema: Object schema.
        :returns: A `__validators__` mapping (empty when `patternProperties` is absent).
        """
        if schema.pattern_properties is MISSING:
            return {}

        branches: dict[str, PythonType] = {}
        for pattern, sub_schema in schema.pattern_properties.items():
            with self._track_path(f"patternProperties.{pattern}"):
                branches[pattern] = self._constrained_annotation(sub_schema)

        pattern_properties = self._register(PatternProperties(branches=branches))

        def _check(data: PythonType) -> PythonType:
            return pattern_properties.validate(data)

        return {"_validate_pattern_properties": model_validator(mode="before")(_check)}

    def _build_property_names(
        self,
        schema: Schema,
        /,
    ) -> dict[str, PythonType]:
        """Build the `propertyNames` validator for an object model.

        Registers the validator so its `ForwardRef` subschema (a `propertyNames` pointing at a
        `$ref`) is namespace-bound after the whole schema is converted.

        :param schema: Object schema.
        :returns: A `__validators__` mapping (empty when `propertyNames` is absent).
        """
        if schema.property_names is MISSING:
            return {}

        with self._track_path("propertyNames"):
            branch = self._constrained_annotation(schema.property_names)

        property_names = self._register(PropertyNames(branch=branch))

        def _check(data: PythonType) -> PythonType:
            return property_names.validate(data)

        return {"_validate_property_names": model_validator(mode="before")(_check)}

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
        default = get_field_default(schema, field_kind=field_kind)

        # `MISSING` must be part of the annotation for Pydantic to accept it as default.
        if default is MISSING:
            valid_annotation = valid_annotation | MISSING

        return FieldInfo(
            annotation=valid_annotation,
            default=default,
            **build_field_kwargs(schema),
        )

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

        # `not` and `if` / `then` / `else` are checked against the raw value before the host type,
        # attached as `Annotated` wrap-validator metadata (the path used for every shape that has a
        # host annotation; root object models take the `before`-validator path instead).
        if schema.not_ is not MISSING:
            annotation = cast("type", Annotated[annotation, self._build_not(schema)])
        if self._has_conditional(schema):
            annotation = cast("type", Annotated[annotation, self._build_conditional(schema)])

        return annotation

    def _constrained_annotation(
        self,
        schema: Schema | Reference,
        /,
    ) -> AnnotationType:
        """Build a subschema annotation with field-level constraints baked in.

        The marker validators (`Not`, `Contains`, `PrefixItems`, `IfThenElse`, `DependentSchemas`)
        validate values against subschemas via a `TypeAdapter`. Plain `_schema_to_annotation` omits
        constraints that the converter normally applies through `FieldInfo` (`minimum`, `maxLength`,
        `pattern`, `multipleOf`, ...), so they are re-applied here as `Annotated` `Field` metadata.

        :param schema: The subschema (or reference) to convert.
        :returns: The annotation, wrapped with `Field(...)` when it carries field-level constraints.
        """
        annotation = self._schema_to_annotation(schema)
        if isinstance(schema, Reference):
            return annotation

        annotation = self._apply_validators(annotation, schema)
        kwargs = build_field_kwargs(schema)
        if kwargs:
            annotation = cast("type", Annotated[annotation, Field(**kwargs)])
        return annotation

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
            branch = self._constrained_annotation(schema.not_)

        return self._register(Not(branch=branch))

    @staticmethod
    def _has_conditional(
        schema: Schema,
        /,
    ) -> bool:
        """Return whether `if` gates an actual `then` / `else` branch.

        :param schema: Schema to inspect.
        :returns: `True` when `if` is present together with `then` and/or `else`.
        """
        return schema.if_ is not MISSING and (
            schema.then is not MISSING or schema.else_ is not MISSING
        )

    def _build_conditional(
        self,
        schema: Schema,
        /,
    ) -> IfThenElse:
        """Build the `if` / `then` / `else` validator, registering it for namespace binding.

        :param schema: Schema carrying `if` / `then` / `else`.
        :returns: An `IfThenElse` validator for the subschemas.
        """
        with self._track_path("if"):
            if_branch = self._constrained_annotation(schema.if_)

        then_branch: AnnotationType | None = None
        if schema.then is not MISSING:
            with self._track_path("then"):
                then_branch = self._constrained_annotation(schema.then)

        else_branch: AnnotationType | None = None
        if schema.else_ is not MISSING:
            with self._track_path("else"):
                else_branch = self._constrained_annotation(schema.else_)

        return self._register(
            IfThenElse(
                if_branch=if_branch,
                then_branch=then_branch,
                else_branch=else_branch,
            )
        )

    def _wrap_root_assertion(
        self,
        model: type[BaseModel],
        marker: Not | IfThenElse,
        /,
        *,
        key: str,
    ) -> type[BaseModel]:
        """Wrap a root object model with a `before` validator enforcing a whole-value assertion.

        A root object is a plain `BaseModel` with no host annotation, so `not` / `if` / `then` /
        `else` cannot ride along as `Annotated` metadata (the path used for every other shape).
        Instead the marker's `check` runs as a `before` model validator on the raw input.

        :param model: The root object `BaseModel`.
        :param marker: The whole-value marker (`Not` or `IfThenElse`), already registered.
        :param key: The `__validators__` key for the validator.
        :returns: A subclass of `model` applying the assertion.
        """

        def _check(data: PythonType) -> PythonType:
            return marker.check(data)

        return self._wrap_root_before(model, key=key, check=_check)

    @staticmethod
    def _wrap_root_before(
        model: type[BaseModel],
        /,
        *,
        key: str,
        check: PythonType,
    ) -> type[BaseModel]:
        """Subclass a root object model, attaching one `before` model validator.

        :param model: The root object `BaseModel`.
        :param key: The `__validators__` key for the validator.
        :param check: The `(data) -> data` validation function.
        :returns: A subclass of `model` with the validator attached.
        """
        validators: dict[str, PythonType] = {key: model_validator(mode="before")(check)}
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
        discriminator = discriminator_property(schema.one_of, defs_cache=self._defs_cache)

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

        one_of_validator = self._register(OneOf(branches=union_args))
        return cast("type", one_of_validator.as_annotation())

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
        metadata: list[PythonType] = array_metadata(schema)
        if prefix_items is not None:
            metadata.append(prefix_items)
        contains = self._build_contains(schema)
        if contains is not None:
            metadata.append(contains)

        return annotate(list_annotation, metadata)

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
                prefixes.append(self._constrained_annotation(sub_schema))

        tail: PythonType | None = None
        if schema.items is not MISSING:
            with self._track_path("items"):
                tail = self._constrained_annotation(schema.items)

        return self._register(PrefixItems(prefixes=prefixes, tail=tail))

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
            branch = self._constrained_annotation(schema.contains)

        # `minContains` defaults to 1; `maxContains` is unbounded when absent.
        min_contains = schema.min_contains if schema.min_contains is not MISSING else 1
        max_contains = schema.max_contains if schema.max_contains is not MISSING else None

        return self._register(
            Contains(branch=branch, min_contains=min_contains, max_contains=max_contains)
        )

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
                return annotate(dict_annotation, object_dict_metadata(schema))

        return annotate(dict[str, Any], object_dict_metadata(schema))


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
