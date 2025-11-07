from dataclasses import dataclass
from typing import Any


@dataclass
class BasePydanticJsonSchemaError(Exception):
    """Base schema exception."""

    message: str

    def __post_init__(self) -> None:
        super().__init__(self.message)

    def __str__(self) -> str:
        return repr(self)


@dataclass
class SchemaConvertionError(BasePydanticJsonSchemaError):
    """Schema convertion failed."""


@dataclass
class SchemaReferenceError(BasePydanticJsonSchemaError):
    """Reference resolution failed."""

    path: list[str]


@dataclass
class FormatValidationError(BasePydanticJsonSchemaError, ValueError):
    """Format validation failed."""

    value: Any = None
