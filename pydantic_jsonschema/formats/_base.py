import inspect
from collections.abc import Callable, Iterable
from datetime import date, datetime, time, timedelta
from ipaddress import IPv4Address, IPv6Address
from typing import Any, Final, Self, get_origin
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from pydantic_jsonschema._utils import validate_with_type
from pydantic_jsonschema.types import DataType, JsonType

__all__ = ["SchemaFormat"]

# TODO: docs - add `required` everywhere

# Python native types that Pydantic handles natively
_NATIVE_TYPES: Final[Iterable[type]] = (
    date,
    time,
    datetime,
    timedelta,
    UUID,
    IPv4Address,
    IPv6Address,
)


def _is_type_validator(validator: Any) -> bool:  # noqa: ANN401
    """Check if validator is a type (class) or Annotated type."""
    # Check if it's a class/type
    if inspect.isclass(validator):
        return True
    # Check if it's a type (isinstance doesn't work for all types)
    if isinstance(validator, type):  # pragma: no cover
        return True
    # Check if it's an Annotated type
    return get_origin(validator) is not None


class SchemaFormat(BaseModel):
    """Schema format definition with validation.

    Represents a JSON Schema format with examples and optional validation.

    :param key: Format identifier (e.g., "date-time", "email").
    :param title: Human-readable format name.
        Auto-generated from key if None.
    :param examples: List of valid example values for this format.
    :param types: JSON Schema types that can use this format.
    :param validator: Optional validator - can be:
        - Callable: validation function (e.g., validate_email)
        - type: Pydantic type class (e.g., Currency from pydantic-extra
            - Annotated type with validators (e.g., Annotated[int, AfterValidator(...)])
            Should raise `ValueError` on an invalid input.
    """

    key: str = Field(
        description="Format identifier for JSON Schema",
    )
    title: str | None = Field(
        default=None,
        description="Human-readable name",
    )  #  Auto-generated from key if None
    examples: list[Any] = Field(
        default_factory=list,
        description="Example values",
    )
    types: list[DataType] = Field(
        default_factory=list,
        description="Accepted JSON Schema data types",
    )
    # Can be callable, type class, or Annotated type
    validator: Callable[[Any], Any] | type | None = Field(
        default=None,
        exclude=True,
    )

    @model_validator(mode="after")
    def auto_generate_title(self) -> Self:
        """Auto-generate title from key if not provided."""
        if self.title is None:
            self.title = " ".join(word.capitalize() for word in self.key.split("-"))
        return self

    @model_validator(mode="after")
    def validate_examples(self) -> Self:
        """Validate that all examples pass the validator."""
        if self.validator is None:
            return self

        for example in self.examples:
            try:
                # For types (classes, Annotated types), use Pydantic validation
                if _is_type_validator(self.validator):
                    validate_with_type(self.validator, example)
                # For callable validators, call them directly
                else:
                    self.validator(example)
            except Exception as exc:
                msg = f"Invalid example `{example!r}` for format `{self.key!r}`: `{exc}`"
                raise ValueError(msg) from exc

        return self

    def __call__(self, value: JsonType) -> Any:  # noqa: ANN401
        """Validate and return value using the validator if defined.

        :param value: Value to validate
        :returns: Validated value (or validated instance for type validators)
        :raises ValueError: If validator raises an error.
        """
        if self.validator is None:
            return value

        # For types (classes, Annotated types), use Pydantic validation
        if _is_type_validator(self.validator):
            return validate_with_type(self.validator, value)
        # For callable validators, call them directly
        return self.validator(value)
