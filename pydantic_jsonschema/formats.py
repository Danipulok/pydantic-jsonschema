from collections.abc import Callable
from typing import Any

from openapi_pydantic.v3 import DataType
from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_core.core_schema import ValidationInfo, ValidatorFunctionWrapHandler

from pydantic_jsonschema.types import JsonItem
from pydantic_jsonschema.validators import (
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

# from pydantic_extra_types.currency_code import Currency
# from pydantic_extra_types.language_code import LanguageAlpha2


__all__ = [
    "SchemaFormat",
    "DATE",
    "TIME",
    "DATE_TIME",
    "DURATION",
    "EMAIL",
    "HOSTNAME",
    "IPV_4",
    "IPV_6",
    "UUID",
    "URI",
    "URI_REFERENCE",
    "IRI",
    "IRI_REFERENCE",
    "ISO_4217",
    "ISO_639_1_ALPHA_2",
]


class SchemaFormat(BaseModel):
    """
    Schema format definition with validation.

    :param display_name: Human-readable format name.
    :param examples: Example values for this format.
    :param acceptable_types: JSON Schema types that can use this format.
    :param validator: Optional validator function or type.
    """

    key: str
    display_name: str
    examples: list[Any]
    acceptable_types: list[DataType]
    validator: type | Callable[[Any], Any] | None = Field(None, exclude=True)

    model_config = ConfigDict(
        json_schema_extra={
            "exclude": ["validator"],
        },
    )

    def __call__(
        self,
        value: JsonItem,
    ) -> Any:
        """Call the validator if defined."""
        if self.validator is None:
            return value
        return self.validator(value)

    @model_validator(mode="wrap")
    @classmethod
    def _validate_examples(
        cls,
        data: Any,
        handler: ValidatorFunctionWrapHandler,
        _info: ValidationInfo,
    ) -> "SchemaFormat":
        """Validate that examples match the validator."""
        validated = handler(data)

        if not validated.validator:
            return validated

        # Validate each example
        for example in validated.examples:
            try:
                validated.validator(example)
            except Exception as exc:
                raise ValueError(
                    f"Invalid example '{example}' for format "
                    f"'{validated.display_name}': {exc}",
                ) from exc

        return validated


DATE_TIME = SchemaFormat(
    key="date-time",
    display_name="Date Time",
    examples=["2018-11-13T20:20:39+00:00"],
    acceptable_types=[DataType.STRING],
    validator=validate_datetime,
)
TIME = SchemaFormat(
    key="time",
    display_name="Time",
    examples=["20:20:39+00:00"],
    acceptable_types=[DataType.STRING],
    validator=validate_time,
)
DATE = SchemaFormat(
    key="date",
    display_name="Date",
    examples=["2018-11-13"],
    acceptable_types=[DataType.STRING],
    validator=validate_date,
)
DURATION = SchemaFormat(
    key="duration",
    display_name="Duration",
    examples=["P3D"],
    acceptable_types=[DataType.STRING],
    validator=validate_duration,
)
EMAIL = SchemaFormat(
    key="email",
    display_name="Email",
    examples=["example@example.com"],
    acceptable_types=[DataType.STRING],
    validator=validate_email,
)
HOSTNAME = SchemaFormat(
    key="hostname",
    display_name="Hostname",
    examples=["example.com"],
    acceptable_types=[DataType.STRING],
    validator=validate_hostname,
)
IPV_4 = SchemaFormat(
    key="ipv4",
    display_name="IPv4",
    examples=["192.168.1.1"],
    acceptable_types=[DataType.STRING],
    validator=validate_ipv4,
)
IPV_6 = SchemaFormat(
    key="ipv6",
    display_name="IPv6",
    examples=["2001:0db8:85a3:0000:0000:8a2e:0370:7334"],
    acceptable_types=[DataType.STRING],
    validator=validate_ipv6,
)
UUID = SchemaFormat(
    key="uuid",
    display_name="UUID",
    examples=["3e4666bf-d5e5-4aa7-b8ce-cefe41c7568a"],
    acceptable_types=[DataType.STRING],
    validator=validate_uuid,
)
URI = SchemaFormat(
    key="uri",
    display_name="URI",
    examples=["https://www.example.com/resource"],
    acceptable_types=[DataType.STRING],
    validator=validate_uri,
)
URI_REFERENCE = SchemaFormat(
    key="uri-reference",
    display_name="URI Reference",
    examples=["/relative/path/to/resource"],
    acceptable_types=[DataType.STRING],
    validator=validate_uri_reference,
)
IRI = SchemaFormat(
    key="iri",
    display_name="IRI",
    examples=["https://www.example.com/こんにちは"],
    acceptable_types=[DataType.STRING],
    validator=validate_iri,
)
IRI_REFERENCE = SchemaFormat(
    key="iri-reference",
    display_name="IRI Reference",
    examples=["/relative/path/to/こんにちは"],
    acceptable_types=[DataType.STRING],
    validator=validate_iri_reference,
)
ISO_4217 = SchemaFormat(
    key="iso-4217",
    display_name="Currency Code",
    examples=["USD", "EUR"],
    acceptable_types=[DataType.STRING],
    validator=None,  # TODO: Use pydantic_extra_types.currency_code.Currency
)
ISO_639_1_ALPHA_2 = SchemaFormat(
    key="iso-639-1-alpha-2",
    display_name="Language Code",
    examples=["en", "fr"],
    acceptable_types=[DataType.STRING],
    validator=None,  # TODO: Use pydantic_extra_types.language_code.LanguageAlpha2
)
