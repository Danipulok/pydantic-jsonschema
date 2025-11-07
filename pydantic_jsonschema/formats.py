from collections.abc import Callable
from typing import Any

from openapi_pydantic.v3 import DataType
from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_core.core_schema import ValidationInfo

from ._validators import (
    validate_date,
    validate_datetime,
    validate_duration,
    validate_email,
    validate_hostname,
    validate_ipv4,
    validate_ipv6,
    validate_iri,
    validate_iri_reference,
    validate_time,
    validate_uri,
    validate_uri_reference,
    validate_uuid,
)
from .types import JsonItem

__all__ = [
    "DATE",
    "DATE_TIME",
    "DURATION",
    "EMAIL",
    "HOSTNAME",
    "IPV_4",
    "IPV_6",
    "IRI",
    "IRI_REFERENCE",
    "ISO_639_1_ALPHA_2",
    "ISO_4217",
    "TIME",
    "URI",
    "URI_REFERENCE",
    "UUID",
    "SchemaFormat",
]


class SchemaFormat(BaseModel):
    """
    Schema format definition with validation.

    Represents a JSON Schema format with examples and optional validation.

    Attributes:
        key: Format identifier (e.g., "date-time", "email"). Used in JSON Schema.
        title: Human-readable format name. Auto-generated from key if None.
        examples: List of valid example values for this format.
        types: JSON Schema types that can use this format.
        validator: Optional validation function. Raises ValueError on invalid input.
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
    validator: Callable[[Any], Any] | None = Field(
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
    def validate_examples(self) -> "SchemaFormat":
        """Validate that all examples pass the validator."""
        if not self.validator:
            return self

        for example in self.examples:
            try:
                self.validator(example)
            except Exception as exc:
                msg = f"Invalid example `{example!r}` for format `{self.key!r}`: `{exc}`"
                raise ValueError(msg) from exc

        return self

    def __call__(self, value: JsonItem) -> Any:
        """Validate and return value using the validator if defined.

        Args:
            value: The value to validate.

        Returns:
            The validated value.

        Raises:
            Exception: If validator raises an error.
        """
        if self.validator is None:
            return value
        return self.validator(value)


DATE_TIME = SchemaFormat(
    key="date-time",
    title="Date Time",
    examples=["2018-11-13T20:20:39+00:00"],
    types=[DataType.STRING],
    validator=validate_datetime,
)
TIME = SchemaFormat(
    key="time",
    title="Time",
    examples=["20:20:39+00:00"],
    types=[DataType.STRING],
    validator=validate_time,
)
DATE = SchemaFormat(
    key="date",
    title="Date",
    examples=["2018-11-13"],
    types=[DataType.STRING],
    validator=validate_date,
)
DURATION = SchemaFormat(
    key="duration",
    title="Duration",
    examples=["P3D"],
    types=[DataType.STRING],
    validator=validate_duration,
)
EMAIL = SchemaFormat(
    key="email",
    title="Email",
    examples=["example@example.com"],
    types=[DataType.STRING],
    validator=validate_email,
)
HOSTNAME = SchemaFormat(
    key="hostname",
    title="Hostname",
    examples=["example.com"],
    types=[DataType.STRING],
    validator=validate_hostname,
)
IPV_4 = SchemaFormat(
    key="ipv4",
    title="IPv4",
    examples=["192.168.1.1"],
    types=[DataType.STRING],
    validator=validate_ipv4,
)
IPV_6 = SchemaFormat(
    key="ipv6",
    title="IPv6",
    examples=["2001:0db8:85a3:0000:0000:8a2e:0370:7334"],
    types=[DataType.STRING],
    validator=validate_ipv6,
)
UUID = SchemaFormat(
    key="uuid",
    title="UUID",
    examples=["3e4666bf-d5e5-4aa7-b8ce-cefe41c7568a"],
    types=[DataType.STRING],
    validator=validate_uuid,
)
URI = SchemaFormat(
    key="uri",
    title="URI",
    examples=["https://www.example.com/resource"],
    types=[DataType.STRING],
    validator=validate_uri,
)
URI_REFERENCE = SchemaFormat(
    key="uri-reference",
    title="URI Reference",
    examples=["/relative/path/to/resource"],
    types=[DataType.STRING],
    validator=validate_uri_reference,
)
IRI = SchemaFormat(
    key="iri",
    title="IRI",
    examples=["https://www.example.com/こんにちは"],
    types=[DataType.STRING],
    validator=validate_iri,
)
IRI_REFERENCE = SchemaFormat(
    key="iri-reference",
    title="IRI Reference",
    examples=["/relative/path/to/こんにちは"],
    types=[DataType.STRING],
    validator=validate_iri_reference,
)
ISO_4217 = SchemaFormat(
    key="iso-4217",
    title="Currency Code",
    examples=["USD", "EUR"],
    types=[DataType.STRING],
    # TODO: Use `pydantic_extra_types.currency_code.Currency` if available
)
ISO_639_1_ALPHA_2 = SchemaFormat(
    key="iso-639-1-alpha-2",
    title="Two Letter Language Code",
    examples=["en", "fr"],
    types=[DataType.STRING],
    # TODO: Use `pydantic_extra_types.language_code.LanguageAlpha2` if available
)
