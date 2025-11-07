from collections.abc import Iterator
from contextlib import contextmanager
from typing import (
    Annotated,
    Any,
    Final,
    ForwardRef,
    Literal,
    Protocol,
    Union,
    cast,
)

from openapi_pydantic import DataType, Reference, Schema
from pydantic import BaseModel, ConfigDict, RootModel, create_model
from pydantic.fields import FieldInfo
from pydantic.functional_validators import BeforeValidator

from .exceptions import ParsingError, ReferenceError
from .utils import sanitize_identifier

__all__ = [
    "BeforeValidatorFunc",
    "FormatName",
    "FormatValidator",
    "Ref",
    "SchemaConverter",
    "SchemaHash",
    "convert_schema",
]


_DEFAULT_MODEL_NAME: Final[str] = "Model"
# Missing value for `default` field
_PYDANTIC_DEFAULT_MISSING: Final[Ellipsis] = ...  # type: ignore[valid-type]
_DEFS_KEY: Final[str] = "$defs"  # JSON Schema 2020-12 definitions key

_TYPE_MAPPING: Final[dict[DataType, type]] = {
    DataType.NULL: None,  # type: ignore[dict-item]
    DataType.STRING: str,
    DataType.NUMBER: float,
    DataType.INTEGER: int,
    DataType.BOOLEAN: bool,
    DataType.ARRAY: list[Any],
    DataType.OBJECT: type[BaseModel],  # type: ignore[dict-item]
}


class FormatValidator(Protocol):
    """
    Protocol for format validator callables.

    Accepts any JSON Schema type: string, number, integer, boolean, null, array, object.

    See:
    https://json-schema.org/draft/2020-12/json-schema-validation#section-7.1

    # todo: add pydantic validation info
    # todo: accept BaseModel
    """

    def __call__(
        self,
        value: str | float | bool | None | list[Any] | Any,
    ) -> Any: ...


class BeforeValidatorFunc(Protocol):
    """
    Protocol for before validator callables.

    Called before Pydantic's standard validation.
    Should either accept any value and return processed value of the desired type,
    or raise a ValueError.

    # todo: add pydantic validation info
    # todo: accept all JsonSchema types
    """

    def __call__(self, value: Any) -> Any: ...


# Type aliases
type Ref = str  # Reference path like "#/$defs/User"
type SchemaHash = str  # Schema cache key (JSON hash)
type FormatName = str  # Format name like "date-time", "uuid"


class SchemaConverter:  # stateful
    """Stateful converter from JSON Schema to Pydantic models."""

    def __init__(
        self,
        *,
        default_model_name: str = _DEFAULT_MODEL_NAME,
        refs: dict[Ref, type[BaseModel]] | None = None,
        format_validators: dict[FormatName, FormatValidator] | None = None,
        before_validators: dict[FormatName, BeforeValidatorFunc] | None = None,
    ) -> None:
        self._default_model_name: str = default_model_name
        self._refs: dict[Ref, type[BaseModel]] = refs or {}
        self._format_validators: dict[FormatName, FormatValidator] = format_validators or {}
        self._before_validators: dict[FormatName, BeforeValidatorFunc] = before_validators or {}

        self._defs_cache: dict[Ref, Schema] = {}
        self._models_cache: dict[SchemaHash, type[BaseModel]] = {}
        self._resolution_path: list[str] = []  # Track path for error reporting

    @staticmethod
    def _hash_schema(
        schema: Schema,
        /,
    ) -> SchemaHash:
        """
        Get cache key for schema.

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
        """
        Context manager for tracking resolution path.

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
        """
        Convert JSON Schema (root schema) to Pydantic model.

        :param schema: Schema to convert.
        :param model_name: Name for the generated model.
        :returns: Pydantic model class.
        :raises ParsingError: If schema cannot be converted.
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
        """
        Convert JSON Schema to Pydantic model (for nested/def schemas).

        :param schema: Schema to convert.
        :param model_name: Name for the generated model.
        :returns: Pydantic model class.
        :raises ParsingError: If schema contains $defs (only allowed in root).
        """
        # Validate that `$defs` is not present in nested schemas
        if schema.model_extra and _DEFS_KEY in schema.model_extra:
            msg = f"{_DEFS_KEY} is only allowed in root schema, not in nested schemas"
            raise ParsingError(msg)

        # Build model using common logic
        return self._build_model(schema, model_name=model_name)

    def _build_model(
        self,
        schema: Schema,
        /,
        *,
        model_name: str | None = None,
    ) -> type[BaseModel]:
        """
        Build Pydantic model from schema (common logic for root and nested).

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
        model = create_model(  # type: ignore[call-overload]
            name,
            __config__=model_config,
            __doc__=schema.description,
            __base__=base_classes,
            __module__=__name__,
            **fields,
        )
        self._models_cache[cache_key] = model
        return model  # type: ignore[no-any-return]

    @staticmethod
    def _get_inline_defs(
        schema: Schema,
        /,
    ) -> dict[Ref, Schema]:
        """
        Extract inline schema defs from `$defs` field.

        :param schema: Schema to extract defs from.
        :returns: Mapping of reference paths to schemas.
        """
        defs: dict[Ref, Schema] = {}

        if not schema.model_extra:
            return defs

        # Extract $defs (JSON Schema 2020-12)
        # See: https://json-schema.org/draft/2020-12/json-schema-core#section-8.2.4
        defs = schema.model_extra.get(_DEFS_KEY, {})

        for name, schema_def in defs.items():
            schema_instance = Schema.model_validate(schema_def)

            # Store with full reference path
            ref_path = f"#/{_DEFS_KEY}/{name}"
            defs[ref_path] = schema_instance

        return defs

    def _build_defs_cache(
        self,
        schema: Schema,
        /,
    ) -> None:
        """
        Build defs cache from schema `$defs` field.

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
            if cache_key in self._models_cache:
                model = self._models_cache[cache_key]
                if model in forward_refs:  # type: ignore[comparison-overlap]
                    model.model_rebuild(_types_namespace=forward_refs)

    def _get_forward_refs_namespace(self) -> dict[str, type[BaseModel]]:
        """Get namespace for forward reference resolution."""
        namespace: dict[str, type[BaseModel]] = {}

        # Add models from defs cache
        for ref, schema in self._defs_cache.items():
            cache_key = self._hash_schema(schema)
            if cache_key in self._models_cache:
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
        """
        Get or generate Pydantic model for reference.

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
            raise ReferenceError(
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
        return model

    def _get_base_classes(
        self,
        schema: Schema,
        /,
    ) -> tuple[type[BaseModel], ...]:
        """
        Get base classes from `allOf` composition.

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
                annotation: type[BaseModel] | None = None
                if isinstance(field_schema, Reference):
                    # Get model for annotation
                    annotation = self._get_model(field_schema.ref)
                    # Use schema from defs for field metadata, or empty schema
                    field_schema = self._defs_cache.get(field_schema.ref, Schema())

                # Convert to Pydantic field
                field = self._schema_to_field(
                    field_schema,
                    is_required=field_name in (schema.required or []),
                    annotation=annotation,
                )

                fields[field_name] = (field.annotation, field)

        return fields

    def _apply_validator(
        self,
        annotation: Any,
        schema: Schema,
        /,
    ) -> Any:
        """
        Apply before validator to annotation.

        :param annotation: Original annotation.
        :param schema: Schema to check for format.
        :returns: Annotation wrapped with BeforeValidator if applicable.
        """
        # Check if schema has format and we have a before_validator for it
        if not schema.schema_format:
            return annotation

        validator = self._before_validators.get(schema.schema_format)
        if not validator:
            return annotation

        # Wrap annotation with BeforeValidator
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
            config["extra"] = cast("Literal['forbid']", "forbid")  # type: ignore[redundant-cast]
        else:
            config["extra"] = cast("Literal['allow']", "allow")  # type: ignore[redundant-cast]

        return config

    def _schema_to_field(
        self,
        schema: Schema,
        /,
        *,
        is_required: bool | None = None,
        annotation: Any | None = None,
    ) -> FieldInfo:
        """
        Convert schema to Pydantic FieldInfo.

        :param schema: Schema to convert.
        :param is_required: Whether field is is_required.
        :param annotation: Pre-computed annotation.
        :returns: Pydantic FieldInfo.
        """
        # Get annotation if not provided
        if annotation is None:
            annotation = self._schema_to_annotation(schema)

        # Apply before validator if configured
        annotation = self._apply_validator(annotation, schema)

        # Determine default value
        default = self._get_field_default(schema, is_required=is_required)

        # Get examples
        examples = schema.examples or ([schema.example] if schema.example else None)

        # Create FieldInfo
        return FieldInfo(
            annotation=annotation,
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

    def _schema_to_annotation(
        self,
        schema: Schema | Reference,
        /,
    ) -> type | ForwardRef:
        """
        Convert schema to Python type annotation.

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
            return Literal[tuple(values)]  # type: ignore[return-value]

        # `anyOf` / `oneOf` -> `Union`:
        if schema.anyOf or schema.oneOf:
            union_type = "anyOf" if schema.anyOf else "oneOf"
            union_schemas = schema.anyOf or schema.oneOf or []
            union_args = []
            for idx, sub_schema in enumerate(union_schemas):
                with self._track_path(f"{union_type}[{idx}]"):
                    union_args.append(self._schema_to_annotation(sub_schema))
            return Union[tuple(union_args)]  # type: ignore[return-value]

        # `allOf` -> nested model:
        if schema.allOf:
            return self._convert_nested_schema(schema)

        # `array` -> list:
        if schema.type == DataType.ARRAY:
            item_type = Any
            if schema.items:
                with self._track_path("items"):
                    item_type = self._schema_to_annotation(schema.items)  # type: ignore[assignment]
            return list[item_type]  # type: ignore[valid-type]

        # `object` -> `dict` / `BaseModel`:
        if schema.type == DataType.OBJECT:
            if schema.properties:
                return self._convert_nested_schema(schema)

            # Handle additionalProperties
            if schema.additionalProperties is False:
                return dict[str, Any]

            if isinstance(schema.additionalProperties, (Schema, Reference)):
                with self._track_path("additionalProperties"):
                    value_type = self._schema_to_annotation(schema.additionalProperties)
                    return dict[str, value_type]  # type: ignore[valid-type]

            return dict[str, Any]

        # Handle format validation
        if schema.schema_format:
            validator = self._get_format_validator(schema.schema_format)
            if validator:
                return validator  # type: ignore[return-value]

        # Handle basic types
        if schema.type:
            if isinstance(schema.type, list):
                return Union[tuple(_TYPE_MAPPING[t] for t in schema.type)]  # type: ignore[return-value]
            return _TYPE_MAPPING.get(schema.type, Any)

        return Any

    @staticmethod
    def _get_field_default(
        schema: Schema,
        /,
        *,
        is_required: bool | None,
    ) -> Any:
        """
        Determine default value for the field based on its schema.

        :param schema: Schema to get default from.
        :param is_required: Whether field is is_required.
        :returns: Default value or Ellipsis for required fields.
        """
        if is_required:
            return _PYDANTIC_DEFAULT_MISSING

        # TODO: check if `schema.default` was set explicitly
        if schema.default is not None:
            return schema.default

        return None

    @staticmethod
    def _get_min_length(
        schema: Schema,
        /,
    ) -> int | None:
        """
        Get min items length based on the schema type.

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
        """
        Get max items length based on the schema type.

        :param schema: Schema to get max length from.
        :returns: max items length or None.
        """
        if schema.type == DataType.ARRAY:
            return schema.maxItems
        return schema.maxLength

    def _get_format_validator(
        self,
        format_name: FormatName,
        /,
    ) -> FormatValidator | None:
        """
        Get validator for format.

        :param format_name: Format name.
        :returns: Format validator callable or None.
        """
        return self._format_validators.get(format_name)


# Convenience functions
def convert_schema(
    schema: Schema,
    /,
    *,
    model_name: str | None = None,
) -> type[BaseModel]:
    """Convert schema to Pydantic model."""
    converter = SchemaConverter()
    return converter.convert_schema(schema, model_name=model_name)
