"""JSON Schema to Pydantic model converter."""

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
    Union,
    cast,
    get_origin,
)

from pydantic import BaseModel, BeforeValidator, ConfigDict, RootModel, create_model
from pydantic.fields import FieldInfo

from ._lax import COERCE_FUNCTIONS
from ._utils import sanitize_identifier
from .exceptions import SchemaConvertionError, SchemaReferenceError
from .types import DataType, JsonType, Reference, Schema

__all__ = [
    "BeforeValidatorFunc",
    "FormatName",
    "FormatValidator",
    "LaxSchemaConverter",
    "Ref",
    "SchemaConverter",
    "SchemaHash",
    "to_lax_model",
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

_DATA_TYPE_ANNOTATION_MAPPING: Final[dict[DataType, type]] = {
    DataType.NULL: NoneType,
    DataType.STRING: str,
    DataType.NUMBER: float,
    DataType.INTEGER: int,
    DataType.BOOLEAN: bool,
    DataType.ARRAY: list[Any],
    DataType.OBJECT: Any,
}

# Type aliases
type Ref = str  # Reference path like "#/$defs/User"
type SchemaHash = str  # Schema cache key (JSON hash)
type FormatName = str  # Format name like "date-time", "uuid"
type AnnotationType = Any  # `type`, `Annotated`, `Union`, `Literal`, `ForwardRef`, etc.
type PythonType = Any  # Anything that Pydantic supports
type FormatValidatorType = FormatValidator | type  # `FormatValidator` or `Annotated`


class FormatValidator(Protocol):
    """Protocol for format validator callables.

    Can be:
    - Callable: validation function
    - type: Pydantic type class (e.g., from pydantic-extra-types)
    - Annotated type with validators (e.g., Annotated[int, AfterValidator(...)])

    Accepts any JSON Schema type: string, number, integer, boolean, null, array, object.
    Called after Pydantic's standard validation.

    See:
    https://json-schema.org/draft/2020-12/json-schema-validation#section-7.1

    For Pydantic validation details, see:
    https://docs.pydantic.dev/latest/concepts/validators/#annotated-validators
    https://docs.pydantic.dev/latest/concepts/validators/#after-validators
    """

    def __call__(
        self,
        value: PythonType,
    ) -> PythonType:
        """Process the value after Pydantic's standard validation."""
        ...


class BeforeValidatorFunc(Protocol):
    """Protocol for before validator callables.

    Called before Pydantic's standard validation.
    Should either accept any value and return processed value of the desired type,
    or raise a ValueError.

    For Pydantic validation details, see:
    https://docs.pydantic.dev/latest/concepts/validators/#annotated-validators
    https://docs.pydantic.dev/latest/concepts/validators/#before-validators
    """

    def __call__(
        self,
        value: JsonType,
    ) -> PythonType:
        """Process the value before Pydantic's standard validation."""
        ...


class SchemaConverter:
    """Stateful converter from JSON Schema to Pydantic models."""

    def __init__(
        self,
        *,
        default_model_name: str = _DEFAULT_MODEL_NAME,
        refs: dict[Ref, type[BaseModel]] | None = None,
        # FormatValidator can be a callable, type class, or Annotated type
        format_validators: dict[FormatName, FormatValidatorType] | None = None,
    ) -> None:
        self._default_model_name: str = default_model_name
        self._refs: dict[Ref, type[BaseModel]] = refs or {}
        self._format_validators: dict[FormatName, FormatValidatorType] = format_validators or {}

        self._defs_cache: dict[Ref, Schema] = {}
        self._models_cache: dict[SchemaHash, type[BaseModel]] = {}
        self._resolution_path: list[str] = []  # Track path for error reporting

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
        :raises SchemaConvertionError: If schema cannot be converted.
        """
        # Build defs cache from `$defs`
        self._build_defs_cache(schema)

        # Build model using common logic
        return self._build_model(schema, model_name=model_name)

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
        :raises SchemaConvertionError: If schema contains $defs (only allowed in root).
        """
        # Validate that `$defs` is not present in nested schemas
        if schema.model_extra and _DEFS_KEY in schema.model_extra:
            msg = f"{_DEFS_KEY} is only allowed in root schema, not in nested schemas"
            raise SchemaConvertionError(msg)

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

        :param schema: Schema to convert.
        :param model_name: Name for the generated model.
        :returns: Pydantic model class.
        """
        # Check if model already cached
        cache_key = self._hash_schema(schema)
        if cache_key in self._models_cache:
            return self._models_cache[cache_key]

        # Determine model name
        name: str = (
            model_name or sanitize_identifier(schema.title or "") or self._default_model_name
        )

        # Handle `allOf` composition -> base classes
        base_classes = self._get_base_classes(schema)

        # Handle non-object types -> RootModel
        if schema.type != DataType.OBJECT:
            model = self._create_root_model(
                schema,
                model_name=name,
                base_classes=base_classes,
            )
            self._models_cache[cache_key] = model
            return model

        # Handle `allOf` without properties -> combined base class
        if schema.allOf and not schema.properties:
            # Single base class
            if len(base_classes) == 1:
                self._models_cache[cache_key] = base_classes[0]
                return base_classes[0]

            # Create combined base class
            created_model = type(name, base_classes, {"__module__": __name__})
            model = cast("type[BaseModel]", created_model)
            self._models_cache[cache_key] = model
            return model

        # Build fields from properties
        fields = self._build_fields(schema)

        # Configure model (extra fields, etc)
        model_config = self._build_model_config(schema)

        # Create model
        # For some reason, `create_model` "accepts" `fields` values as `tuple[str, Any]`,
        # when in reality it accepts `tuple[type, FieldInfo]`
        created_model = create_model(  # type: ignore[call-overload]
            name,
            __config__=model_config,
            __doc__=schema.description,
            __base__=base_classes,
            __module__=__name__,
            **fields,
        )
        model = cast("type[BaseModel]", created_model)
        self._models_cache[cache_key] = model
        return model

    @staticmethod
    def _get_inline_defs(
        schema: Schema,
        /,
    ) -> dict[Ref, Schema]:
        """Extract inline schema defs from `$defs` field.

        :param schema: Schema to extract defs from.
        :returns: Mapping of reference paths to schemas.
        """
        result_defs: dict[Ref, Schema] = {}

        if not schema.model_extra:
            return result_defs

        raw_defs = schema.model_extra.get(_DEFS_KEY, {})
        for name, schema_def in raw_defs.items():
            schema_instance = Schema.model_validate(schema_def)

            # Store with full reference path
            ref_path = f"#/{_DEFS_KEY}/{name}"
            result_defs[ref_path] = schema_instance

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

        # Rebuild all models with forward refs
        forward_refs = self._get_forward_refs_namespace()
        for schema_def in defs.values():
            cache_key = self._hash_schema(schema_def)
            # Model is guaranteed to be in cache after `_convert_nested_schema above`
            model = self._models_cache[cache_key]
            # Model is guaranteed to be in `forward_refs` as it was just added
            model.model_rebuild(_types_namespace=forward_refs)

    def _get_forward_refs_namespace(self) -> dict[str, type[BaseModel]]:
        """Get namespace for forward reference resolution."""
        namespace: dict[str, type[BaseModel]] = {}

        # Add models from defs cache
        # Models are guaranteed to be in cache after `_build_defs_cache`
        for ref, schema in self._defs_cache.items():
            cache_key = self._hash_schema(schema)
            namespace[sanitize_identifier(ref)] = self._models_cache[cache_key]

        # Add pre-built ref models
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
        :raises ReferenceError: If reference cannot be resolved.
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

        # Check if already generated
        schema = self._defs_cache[ref]
        cache_key = self._hash_schema(schema)
        if cache_key in self._models_cache:
            return self._models_cache[cache_key]

        # Generate model from schema
        model = self._convert_nested_schema(schema)
        self._models_cache[cache_key] = model
        return model

    def _get_base_classes(
        self,
        schema: Schema,
        /,
    ) -> tuple[type[BaseModel], ...]:
        """Get base classes from `allOf` composition.

        :param schema: Schema to extract base classes from.
        :returns: Tuple of base classes.
        """
        if not schema.allOf:
            return (BaseModel,)

        # Convert each `allOf` schema to model
        base_models = []
        for idx, sub_schema in enumerate(schema.allOf):
            with self._track_path(f"allOf[{idx}]"):
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
        base_classes: tuple[type[BaseModel], ...],
    ) -> type[BaseModel]:
        """Create RootModel for non-object schemas."""
        if schema.allOf and base_classes:
            return base_classes[0]

        field = self._schema_to_field(schema)

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

        for field_name, field_schema in (schema.properties or {}).items():
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
                    is_required=field_name in (schema.required or []),
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

        Handles three types of validators:
        - Annotated types: used directly as annotation (replaces original)
        - type classes: used directly as annotation (replaces original)
        - Callables: wrapped with BeforeValidator
        - SchemaFormat: use its validator attribute

        :param annotation: Original annotation.
        :param schema: Schema to check for format.
        :returns: Annotation with validator applied if applicable.
        """
        if schema.schema_format not in self._format_validators:
            return annotation

        validator = self._format_validators[schema.schema_format]

        # Handle SchemaFormat objects (without importing to avoid circular dependency)
        # TODO: rewrite
        if hasattr(validator, "validator"):
            nested_validator = validator.validator
            if nested_validator is None:
                return annotation
            validator = nested_validator

        # If validator is an Annotated type, use it directly as the annotation
        if get_origin(validator) is Annotated:
            return validator

        # If validator is a type/class
        # (custom Pydantic type or a python native type, supported by Pydantic) —
        # use it directly as the annotation
        if isinstance(validator, type):
            return validator

        # Otherwise, it's a callable function - wrap it with `BeforeValidator`
        return Annotated[annotation, BeforeValidator(validator)]

    @staticmethod
    def _build_model_config(
        schema: Schema,
        /,
    ) -> ConfigDict:
        """Build model config from schema."""
        config: ConfigDict = {}

        # Handle `additionalProperties`
        if schema.additionalProperties is False:
            config["extra"] = "forbid"
        else:
            config["extra"] = "allow"

        return config

    def _schema_to_field(
        self,
        schema: Schema,
        /,
        *,
        is_required: bool | None = None,
        annotation: AnnotationType | None = None,
    ) -> FieldInfo:
        """Convert schema to Pydantic FieldInfo.

        :param schema: Schema to convert.
        :param is_required: Whether field is is_required.
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
        default = self._get_field_default(schema, is_required=is_required)

        # Get examples
        examples = schema.examples or ([schema.example] if schema.example else None)

        # Create FieldInfo
        return FieldInfo(
            annotation=valid_annotation,
            default=default,
            examples=examples,
            title=schema.title,
            description=schema.description,
            ge=schema.minimum,
            gt=schema.exclusiveMinimum,
            le=schema.maximum,
            lt=schema.exclusiveMaximum,
            multiple_of=schema.multipleOf,
            min_length=self._get_min_length(schema),
            max_length=self._get_max_length(schema),
        )

    def _schema_to_annotation(  # noqa: C901, PLR0911, PLR0912
        self,
        schema: Schema | Reference,
        /,
    ) -> type | ForwardRef:
        """Convert schema to Python type annotation.

        :param schema: Schema to convert.
        :returns: Type annotation.
        """
        # Handle Reference
        if isinstance(schema, Reference):
            # Check if reference can be resolved
            if schema.ref in self._refs or schema.ref in self._defs_cache:
                return self._get_model(schema.ref)

            # Return `ForwardRef` if not yet resolved
            return ForwardRef(sanitize_identifier(schema.ref))

        # `enum` / `const` -> `Literal`:
        if schema.enum or schema.const:
            values = schema.enum or (schema.const,)
            literal_type = Literal[tuple(values)]  # type: ignore[valid-type]
            return cast("type", literal_type)

        # `anyOf` / `oneOf` -> `Union`:
        if schema.anyOf or schema.oneOf:
            union_type = "anyOf" if schema.anyOf else "oneOf"
            union_schemas = schema.anyOf or schema.oneOf or []
            union_args: list[type | ForwardRef] = []
            for idx, sub_schema in enumerate(union_schemas):
                with self._track_path(f"{union_type}[{idx}]"):
                    sub_schema_annotation = self._schema_to_annotation(sub_schema)
                    union_args.append(sub_schema_annotation)
            union_annotation = Union[tuple(union_args)]  # type: ignore[valid-type]  # noqa: UP007
            return cast("type", union_annotation)

        # `allOf` -> nested model:
        if schema.allOf:
            return self._convert_nested_schema(schema)

        # `array` -> list:
        if schema.type == DataType.ARRAY:
            item_type: type | ForwardRef = Any
            if schema.items:
                with self._track_path("items"):
                    item_type = self._schema_to_annotation(schema.items)
            list_annotation = list[item_type]  # type: ignore[valid-type]
            return cast("type", list_annotation)

        # `object` -> `dict` / `BaseModel`:
        if schema.type == DataType.OBJECT:
            if schema.properties:
                return self._convert_nested_schema(schema)

            # Handle additionalProperties
            if schema.additionalProperties is False:
                return dict[str, Any]

            if isinstance(schema.additionalProperties, (Schema, Reference)):
                with self._track_path("additionalProperties"):
                    value_annotation = self._schema_to_annotation(schema.additionalProperties)
                    dict_annotation = dict[str, value_annotation]  # type: ignore[valid-type]
                    return cast("type", dict_annotation)

            return dict[str, Any]

        # Handle basic types
        if schema.type:
            if isinstance(schema.type, DataType):
                return _DATA_TYPE_ANNOTATION_MAPPING[schema.type]
            union_args = [_DATA_TYPE_ANNOTATION_MAPPING[data_type] for data_type in schema.type]
            union_annotation = Union[tuple(union_args)]  # noqa: UP007
            return cast("type", union_annotation)

        return Any

    @staticmethod
    def _get_field_default(
        schema: Schema,
        /,
        *,
        is_required: bool | None,
    ) -> Any:  # noqa:  ANN401
        """Determine default value for the field based on its schema.

        :param schema: Schema to get default from.
        :param is_required: Whether field is required.
        :returns: Default value or Ellipsis for required fields.
        """
        if is_required:
            return _PYDANTIC_DEFAULT_MISSING

        # Return `default` field only if it was explicitly set
        # We can't just check for `None`, since `default`'s default is `None`
        if "default" in schema.model_fields_set:
            return schema.default

        # Field is not required and has no default
        return None

    @staticmethod
    def _get_min_length(
        schema: Schema,
        /,
    ) -> int | None:
        """Get min items length based on the schema type.

        :param schema: Schema to get min length from.
        :returns: min items length or None.
        """
        if schema.type == DataType.ARRAY:
            return schema.minItems
        return schema.minLength

    @staticmethod
    def _get_max_length(
        schema: Schema,
        /,
    ) -> int | None:
        """Get max items length based on the schema type.

        :param schema: Schema to get max length from.
        :returns: max items length or None.
        """
        if schema.type == DataType.ARRAY:
            return schema.maxItems
        return schema.maxLength


class LaxSchemaConverter(SchemaConverter):
    """Lax schema conversion with type coercion.

    Provides lax validation that:
    - Adds before validators to coerce values to expected types
    - Uses user-provided coerce functions or defaults from _lax module
    """

    def __init__(
        self,
        *,
        default_model_name: str = _DEFAULT_MODEL_NAME,
        refs: dict[Ref, type[BaseModel]] | None = None,
        format_validators: dict[FormatName, FormatValidatorType] | None = None,
        coerce_functions: dict[type, BeforeValidatorFunc] | None = None,
        model_validators: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            default_model_name=default_model_name,
            refs=refs,
            format_validators=format_validators,
        )
        # Use user-provided coerce functions or defaults
        self._coerce_functions = (
            coerce_functions if coerce_functions is not None else COERCE_FUNCTIONS
        )
        # Store model validators for passing to create_model
        self._model_validators = model_validators or {}

    def _apply_validators(
        self,
        annotation: AnnotationType,
        schema: Schema,
        /,
    ) -> AnnotationType:
        """Apply validators to annotation with lax coercion.

        Adds BeforeValidators for type coercion before format validators.

        :param annotation: Original annotation.
        :param schema: Schema to check for format.
        :returns: Annotation with validators applied.
        """
        # Extract base type for coercion (before format validators)
        base_type = self._extract_base_type(annotation)

        # Apply format validators from parent
        annotation_with_format = super()._apply_validators(annotation, schema)

        # If no coercion needed, return early
        if base_type not in self._coerce_functions:
            return annotation_with_format

        coerce_func = self._coerce_functions[base_type]
        coerce_validator = BeforeValidator(coerce_func)

        # If already Annotated (from format validator), add coerce validator
        # mypy doesn't understand that `AnnotationType` can be `Annotated` special form
        if get_origin(annotation_with_format) is Annotated:  # type: ignore[comparison-overlap]
            # `annotation_with_format` is `Annotated`, so it has `__args__` and `__metadata__`
            assert hasattr(annotation_with_format, "__args__")  # noqa: S101
            assert hasattr(annotation_with_format, "__metadata__")  # noqa: S101

            # Extract the base type and existing metadata
            base_annotation = annotation_with_format.__args__[0]
            existing_metadata = annotation_with_format.__metadata__
            # Add coerce validator AFTER existing metadata
            # (BeforeValidators run in reverse order - last one runs first)
            return Annotated[base_annotation, *existing_metadata, coerce_validator]

        # Wrap with coerce validator
        return Annotated[annotation_with_format, coerce_validator]

    def _build_model(
        self,
        schema: Schema,
        /,
        *,
        model_name: str | None = None,
    ) -> type[BaseModel]:
        """Build Pydantic model from schema with model validators support.

        Overrides parent to add model validators support.

        :param schema: Schema to convert.
        :param model_name: Name for the generated model.
        :returns: Pydantic model class.
        """
        # Check if model already cached
        cache_key = self._hash_schema(schema)
        if cache_key in self._models_cache:
            return self._models_cache[cache_key]

        # Determine model name
        name: str = (
            model_name or sanitize_identifier(schema.title or "") or self._default_model_name
        )

        # Handle `allOf` composition -> base classes
        base_classes = self._get_base_classes(schema)

        # Handle non-object types -> RootModel
        if schema.type != DataType.OBJECT:
            model = self._create_root_model(
                schema,
                model_name=name,
                base_classes=base_classes,
            )
            self._models_cache[cache_key] = model
            return model

        # Handle `allOf` without properties -> combined base class
        if schema.allOf and not schema.properties:
            # Single base class
            if len(base_classes) == 1:
                self._models_cache[cache_key] = base_classes[0]
                return base_classes[0]

            # Create combined base class
            created_model = type(name, base_classes, {"__module__": __name__})
            model = cast("type[BaseModel]", created_model)
            self._models_cache[cache_key] = model
            return model

        # Build fields from properties
        fields = self._build_fields(schema)

        # Configure model (extra fields, etc)
        model_config = self._build_model_config(schema)

        # Create model with model validators support
        created_model = create_model(  # type: ignore[call-overload]
            name,
            __config__=model_config,
            __doc__=schema.description,
            __base__=base_classes,
            __module__=__name__,
            __validators__=self._model_validators,
            **fields,
        )
        model = cast("type[BaseModel]", created_model)
        self._models_cache[cache_key] = model
        return model

    @staticmethod
    def _extract_base_type(annotation: AnnotationType) -> type | None:
        """Extract base type from annotation for coercion.

        :param annotation: Type annotation to extract from.
        :returns: Base type if coercible, None otherwise.
        """
        # Handle Annotated types (shouldn't happen at this stage, but just in case)
        # mypy doesn't understand that `AnnotationType` can be `Annotated` special form
        if get_origin(annotation) is Annotated:  # type: ignore[comparison-overlap]
            # `annotation` is `Annotated`, so it has __args__
            assert hasattr(annotation, "__args__")  # noqa: S101
            annotation = annotation.__args__[0]

        # Handle direct types
        if annotation in (str, int, float):
            return cast("type", annotation)

        # Handle list types (list[...])
        origin = get_origin(annotation)
        # mypy doesn't understand that `get_origin` can return `list` type
        if origin is list:  # type: ignore[comparison-overlap]
            return list

        return None


# Convenience functions
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


def to_lax_model(  # noqa: PLR0913
    schema: Schema,
    /,
    *,
    model_name: str | None = None,
    refs: dict[Ref, type[BaseModel]] | None = None,
    format_validators: dict[FormatName, FormatValidatorType] | None = None,
    coerce_functions: dict[type, BeforeValidatorFunc] | None = None,
    model_validators: dict[str, Any] | None = None,
) -> type[BaseModel]:
    """Convert schema to Pydantic model with lax validation.

    All fields are optional and have sensible defaults.

    :param schema: Schema to convert.
    :param model_name: Name for the generated model.
    :param refs: Pre-built reference models.
    :param format_validators: Custom format validators (callables, types, or Annotated).
    :param coerce_functions: Custom type coercion functions. Maps Python types to
        coercion callables that transform values before validation.
        If None, uses default coercions (str, int, float, list).
    :param model_validators: Custom model validators (dict of validator_name -> validator callable).
        Validators will be added to the generated model using Pydantic's __validators__ parameter.
    :returns: Pydantic model class with lax validation.
    """
    converter = LaxSchemaConverter(
        refs=refs,
        format_validators=format_validators,
        coerce_functions=coerce_functions,
        model_validators=model_validators,
    )
    return converter.convert_schema(schema, model_name=model_name)
