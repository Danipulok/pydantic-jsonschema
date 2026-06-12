"""JSON Schema to Pydantic model converter."""

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
    Union,
    cast,
    get_origin,
)

from pydantic import BaseModel, BeforeValidator, ConfigDict, RootModel, create_model
from pydantic.experimental.missing_sentinel import MISSING
from pydantic.fields import FieldInfo

from ._one_of import OneOf
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

        :param default_model_name: Fallback name for models without `title`.
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

        # Bind the forward-refs namespace so `OneOf` validators can resolve
        # `ForwardRef` branches lazily at validation time.
        namespace = self._get_forward_refs_namespace()
        for one_of_validator in self._one_of_validators:
            one_of_validator.bind_namespace(namespace)

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

        :param schema: Schema to convert.
        :param model_name: Name for the generated model.
        :returns: Pydantic model class.
        """
        # Check if model already cached
        cache_key = self._hash_schema(schema)
        if cache_key in self._models_cache:
            return self._models_cache[cache_key]

        # Determine model name
        title: str = schema.title if schema.title is not MISSING else ""
        name: str = model_name or sanitize_identifier(title) or self._default_model_name

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

        # Root object without `properties` but with schema-valued `additionalProperties`
        # -> `RootModel[dict[str, ...]]`, so values are validated the same way as in
        # nested objects (a plain `BaseModel` with `extra="allow"` would not check them).
        if (
            schema.properties is MISSING
            and schema.all_of is MISSING
            and isinstance(schema.additional_properties, (Schema, Reference))
        ):
            model = self._create_root_model(
                schema,
                model_name=name,
                base_classes=base_classes,
            )
            self._models_cache[cache_key] = model
            return model

        # Handle `allOf` without properties -> combined base class
        if schema.all_of is not MISSING and schema.properties is MISSING:
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
            __doc__=schema.description if schema.description is not MISSING else None,
            __base__=base_classes,
            __module__=__name__,
            **fields,
        )
        model = cast("type[BaseModel]", created_model)
        self._models_cache[cache_key] = model
        return model

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
        if schema.all_of is MISSING:
            return (BaseModel,)

        # Convert each `allOf` schema to model
        base_models = []
        for idx, sub_schema in enumerate(schema.all_of):
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
        if schema.all_of is not MISSING and base_classes:
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

        properties: dict[str, Reference | Schema] = (
            schema.properties if schema.properties is not MISSING else {}
        )
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
                    is_required=field_name
                    in (schema.required if schema.required is not MISSING else []),
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

    def _schema_to_field(  # noqa: C901
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

        # Build kwargs, only including fields that are explicitly set
        kwargs: dict[str, Any] = {}
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

        min_length = self._get_min_length(schema)
        if min_length is not None:
            kwargs["min_length"] = min_length

        max_length = self._get_max_length(schema)
        if max_length is not None:
            kwargs["max_length"] = max_length

        return FieldInfo(
            annotation=valid_annotation,
            default=default,
            **kwargs,
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
        if schema.enum is not MISSING or schema.const is not MISSING:
            values = schema.enum if schema.enum is not MISSING else (schema.const,)
            literal_type = Literal[tuple(values)]  # type: ignore[valid-type]
            return cast("type", literal_type)

        # `anyOf` -> `Union`:
        if schema.any_of is not MISSING:
            union_args: list[type | ForwardRef] = self._union_args(schema.any_of, kind="anyOf")
            union_annotation = Union[tuple(union_args)]  # type: ignore[valid-type]  # noqa: UP007
            return cast("type", union_annotation)

        # `oneOf` -> union of branches + exactly-one-branch validation:
        if schema.one_of is not MISSING:
            one_of_validator = OneOf(branches=self._union_args(schema.one_of, kind="oneOf"))
            self._one_of_validators.append(one_of_validator)
            return cast("type", one_of_validator.as_annotation())

        # `allOf` -> nested model:
        if schema.all_of is not MISSING:
            return self._convert_nested_schema(schema)

        # `array` -> list:
        if schema.type == DataType.ARRAY:
            item_type: type | ForwardRef = Any
            if schema.items is not MISSING:
                with self._track_path("items"):
                    item_type = self._schema_to_annotation(schema.items)
            list_annotation = list[item_type]  # type: ignore[valid-type]
            return cast("type", list_annotation)

        # `object` -> `dict` / `BaseModel`:
        if schema.type == DataType.OBJECT:
            if schema.properties is not MISSING:
                return self._convert_nested_schema(schema)

            if schema.additional_properties is False:
                return self._convert_nested_schema(schema)

            if isinstance(schema.additional_properties, (Schema, Reference)):
                with self._track_path("additionalProperties"):
                    value_annotation = self._schema_to_annotation(schema.additional_properties)
                    dict_annotation = dict[str, value_annotation]  # type: ignore[valid-type]
                    return cast("type", dict_annotation)

            return dict[str, Any]

        # Handle basic types
        if schema.type is not MISSING:
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

        if schema.default is not MISSING:
            return schema.default

        # Field is not required and has no default
        return None

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
