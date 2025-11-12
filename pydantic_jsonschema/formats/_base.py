from collections.abc import Callable
from typing import Any, Self

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_core.core_schema import ValidationInfo

from pydantic_jsonschema.types import DataType, JsonType

__all__ = ["SchemaFormat"]


class SchemaFormat(BaseModel):
    """Schema format definition with validation.

    Represents a JSON Schema format with examples and optional validation.

    Attributes:
        key: Format identifier (e.g., "date-time", "email"). Used in JSON Schema.
        title: Human-readable format name. Auto-generated from key if None.
        examples: List of valid example values for this format.
        types: JSON Schema types that can use this format.
        validator: Optional validator - can be:
            - Callable: validation function (e.g., validate_email)
            - type: Pydantic type class (e.g., Currency from pydantic-extra-types)
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
        description="Example values",
    )
    types: list[DataType] = Field(
        description="Accepted JSON Schema data types",
    )
    # Can be callable, type class, or Annotated type
    validator: Callable[[Any], Any] | type | None = Field(
        default=None,
        exclude=True,
    )

    @field_validator("title", mode="before")
    @classmethod
    def auto_generate_title(
        cls,
        value: str | None,
        info: ValidationInfo,
    ) -> str:
        """Auto-generate title from key if not provided."""
        if value is not None:
            return value
        key = str(info.data.get("key", ""))
        return " ".join(word.capitalize() for word in key.split("-"))

    @model_validator(mode="after")
    def validate_examples(self) -> Self:
        """Validate that all examples pass the validator."""
        if self.validator is None:
            return self

        for example in self.examples:
            try:
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

        self.validator(value)
        return value
