from dataclasses import dataclass, fields
from typing import Any


@dataclass
class BasePydanticJsonSchemaError(Exception):
    """Base schema exception."""

    message: str

    def __post_init__(self) -> None:
        # Dynamically collect all field values and pass to Exception.__init__
        field_values = tuple(getattr(self, field.name) for field in fields(self))
        super().__init__(*field_values)

    def __str__(self) -> str:
        return repr(self)


@dataclass
class SchemaConvertionError(BasePydanticJsonSchemaError):
    """Schema conversion failed."""


@dataclass
class SchemaReferenceError(BasePydanticJsonSchemaError):
    """Reference resolution failed."""

    path: list[str]


@dataclass
class FormatValidationError(BasePydanticJsonSchemaError, ValueError):
    """Format validation failed."""

    value: Any = None
