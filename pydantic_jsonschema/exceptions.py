"""Custom exceptions for schema conversion, reference resolution, and format validation."""

from dataclasses import dataclass, fields
from typing import Any

__all__ = [
    "BasePydanticJsonSchemaError",
    "FormatValidationError",
    "SchemaConversionError",
    "SchemaReferenceError",
]


@dataclass
class BasePydanticJsonSchemaError(Exception):
    """Base schema exception."""

    message: str

    def __post_init__(self) -> None:
        """Pass all dataclass field values to `Exception.__init__` for `args`."""
        field_values = tuple(getattr(self, field.name) for field in fields(self))
        super().__init__(*field_values)

    def __str__(self) -> str:
        """Delegate to `repr` for consistent error display."""
        return repr(self)


@dataclass
class SchemaConversionError(BasePydanticJsonSchemaError):
    """Schema conversion failed."""


@dataclass
class SchemaReferenceError(BasePydanticJsonSchemaError):
    """Reference resolution failed."""

    path: list[str]


@dataclass
class FormatValidationError(BasePydanticJsonSchemaError, ValueError):
    """Format validation failed."""

    value: Any = None
