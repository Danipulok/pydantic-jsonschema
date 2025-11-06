"""
Lax schema conversion for LLM-friendly validation.

Provides relaxed validation that:
- Makes all fields optional (T | None with default None)
- Adds defaults for required list/dict fields with no constraints
- Coerces string representations to target types
"""

from typing import Any

from openapi_pydantic import DataType, Schema
from pydantic.fields import FieldInfo

from .converters import (
    SchemaConverter,
    _PYDANTIC_DEFAULT_MISSING,
)

__all__ = [
    "LaxSchemaConverter",
    "convert_schema_lax",
]


class LaxSchemaConverter(SchemaConverter):
    """
    Lax converter for LLM-friendly validation.

    Makes validation less strict by:
    - Making all fields optional (adds | None, default=None)
    - Providing defaults for required lists/dicts without constraints
    - Enabling automatic type coercion
    """

    def _get_field_default(
        self,
        schema: Schema,
        /,
        *,
        is_required: bool | None,
    ) -> Any:
        """
        Determine default value with lax rules.

        Lax mode:
        - All fields get None as default (even if required)
        - Lists without minItems get [] as default
        - Objects without minProperties get {} as default

        :param schema: Schema to get default from.
        :param is_required: Whether field is required (ignored in lax mode).
        :returns: Default value (never MISSING in lax mode).
        """
        # Check for explicit default in schema
        if schema.default is not None:
            return schema.default

        # Lax mode: provide sensible defaults
        if schema.type == DataType.ARRAY and schema.minItems is None:
            return []
        if schema.type == DataType.OBJECT and schema.minProperties is None:
            return {}

        # All other fields default to None
        return None

    def _schema_to_field(
        self,
        schema: Schema,
        /,
        *,
        is_required: bool | None = None,
        annotation: Any | None = None,
    ) -> FieldInfo:
        """
        Convert schema to Pydantic FieldInfo with lax rules.

        In lax mode, all fields are optional (adds | None).

        :param schema: Schema to convert.
        :param is_required: Whether field is required (ignored in lax mode).
        :param annotation: Pre-computed annotation.
        :returns: Pydantic FieldInfo.
        """
        # Get base field info
        field = super()._schema_to_field(
            schema,
            is_required=False,  # Force non-required
            annotation=annotation,
        )

        # Make annotation optional if not already
        if field.annotation is not None:
            original_annotation = field.annotation
            # Check if already optional
            if not self._is_optional_annotation(original_annotation):
                # Make it optional
                field.annotation = original_annotation | None

        return field

    @staticmethod
    def _is_optional_annotation(annotation: Any) -> bool:
        """
        Check if annotation is already optional (has None in union).

        :param annotation: Type annotation to check.
        :returns: True if annotation includes None.
        """
        # Handle Union types
        if hasattr(annotation, "__args__"):
            return type(None) in annotation.__args__
        return False


def convert_schema_lax(
    schema: Schema,
    /,
    *,
    model_name: str | None = None,
) -> type:
    """
    Convert schema to Pydantic model with lax validation.

    All fields are optional and have sensible defaults.

    :param schema: Schema to convert.
    :param model_name: Name for the generated model.
    :returns: Pydantic model class with lax validation.
    """
    converter = LaxSchemaConverter()
    return converter.convert_schema(schema, model_name=model_name)
