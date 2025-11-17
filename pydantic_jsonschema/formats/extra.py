import importlib.util

try:
    importlib.util.find_spec("pydantic_extra_types")
except ImportError as _import_error:
    msg = (
        "`pydantic-extra-types` is required to use extra formats. "
        "Install it with: `pip install pydantic-jsonschema[formats-extra]` or "
        "`pip install pydantic-jsonschema[formats-all]`."
    )
    raise ImportError(msg) from _import_error

from pydantic_extra_types.country import (
    CountryAlpha2,
    CountryAlpha3,
    CountryNumericCode,
    CountryShortName,
)
from pydantic_extra_types.currency_code import Currency
from pydantic_extra_types.domain import DomainStr
from pydantic_extra_types.isbn import ISBN as ISBNType  # noqa: N811
from pydantic_extra_types.language_code import LanguageAlpha2, LanguageName
from pydantic_extra_types.mac_address import MacAddress
from pydantic_extra_types.mongo_object_id import MongoObjectId
from pydantic_extra_types.payment import PaymentCardNumber
from pydantic_extra_types.phone_numbers import PhoneNumber
from pydantic_extra_types.s3 import S3Path
from pydantic_extra_types.script_code import ISO_15924 as ScriptCodeType  # noqa: N811
from pydantic_extra_types.semantic_version import SemanticVersion
from pydantic_extra_types.timezone_name import TimeZoneName
from ulid import ULID as _ULID

from pydantic_jsonschema.types import DataType

from ._base import SchemaFormat

__all__ = [
    # Network & Web
    "DOMAIN",
    # Identifiers
    "ISBN",
    "ISO_639_1_ALPHA_2",
    "ISO_639_LANGUAGE_NAME",
    "ISO_3166_ALPHA_2",
    "ISO_3166_ALPHA_3",
    "ISO_3166_NUMERIC",
    "ISO_3166_SHORT_NAME",
    # ISO Standards
    "ISO_4217",
    "ISO_15924",
    "MAC_ADDRESS",
    "MONGO_OBJECT_ID",
    # Financial
    "PAYMENT_CARD_NUMBER",
    "PHONE_NUMBER",
    "S3_PATH",
    "SEMANTIC_VERSION",
    # Other
    "TIMEZONE_NAME",
    "ULID",
]

# ISO Standards

ISO_4217 = SchemaFormat(
    key="iso-4217",
    title="Currency Code",
    examples=["USD", "EUR", "GBP", "JPY"],
    types=[DataType.STRING],
    validator=lambda value: Currency._validate(value, None),  # type: ignore[arg-type]  # noqa: SLF001
)

ISO_639_1_ALPHA_2 = SchemaFormat(
    key="iso-639-1-alpha-2",
    title="Language Code (Alpha-2)",
    examples=["en", "fr", "de", "es"],
    types=[DataType.STRING],
    validator=lambda value: LanguageAlpha2._validate(value, None),  # type: ignore[arg-type]  # noqa: SLF001
)

ISO_639_LANGUAGE_NAME = SchemaFormat(
    key="iso-639-language-name",
    title="Language Name",
    examples=["English", "French", "German", "Spanish"],
    types=[DataType.STRING],
    validator=lambda value: LanguageName._validate(value, None),  # type: ignore[arg-type]  # noqa: SLF001
)

ISO_3166_ALPHA_2 = SchemaFormat(
    key="iso-3166-alpha-2",
    title="Country Code (Alpha-2)",
    examples=["US", "GB", "FR", "DE"],
    types=[DataType.STRING],
    validator=lambda value: CountryAlpha2._validate(value, None),  # type: ignore[arg-type]  # noqa: SLF001
)

ISO_3166_ALPHA_3 = SchemaFormat(
    key="iso-3166-alpha-3",
    title="Country Code (Alpha-3)",
    examples=["USA", "GBR", "FRA", "DEU"],
    types=[DataType.STRING],
    validator=lambda value: CountryAlpha3._validate(value, None),  # type: ignore[arg-type]  # noqa: SLF001
)

ISO_3166_NUMERIC = SchemaFormat(
    key="iso-3166-numeric",
    title="Country Code (Numeric)",
    examples=["840", "826", "250", "276"],
    types=[DataType.STRING],
    validator=lambda value: CountryNumericCode._validate(value, None),  # type: ignore[arg-type]  # noqa: SLF001
)

ISO_3166_SHORT_NAME = SchemaFormat(
    key="iso-3166-short-name",
    title="Country Short Name",
    examples=["United States", "United Kingdom", "France", "Germany"],
    types=[DataType.STRING],
    validator=lambda value: CountryShortName._validate(value, None),  # type: ignore[arg-type]  # noqa: SLF001
)

ISO_15924 = SchemaFormat(
    key="iso-15924",
    title="Script Code",
    examples=["Latn", "Cyrl", "Arab", "Hani"],
    types=[DataType.STRING],
    validator=lambda value: ScriptCodeType._validate(value, None),  # type: ignore[arg-type]  # noqa: SLF001
)

# Identifiers

ISBN = SchemaFormat(
    key="isbn",
    title="ISBN",
    examples=["9780306406157", "0306406152"],
    types=[DataType.STRING],
    validator=lambda value: ISBNType._validate(value, None),  # noqa: SLF001
)

MAC_ADDRESS = SchemaFormat(
    key="mac-address",
    title="MAC Address",
    examples=["00:1B:44:11:3A:B7", "00-1B-44-11-3A-B7"],
    types=[DataType.STRING],
    validator=lambda value: MacAddress._validate(value, None),  # noqa: SLF001
)

ULID = SchemaFormat(
    key="ulid",
    title="ULID",
    examples=["01ARZ3NDEKTSV4RRFFQ69G5FAV"],
    types=[DataType.STRING],
    validator=lambda value: _ULID.from_str(value),
)

MONGO_OBJECT_ID = SchemaFormat(
    key="mongo-object-id",
    title="MongoDB ObjectId",
    examples=["507f1f77bcf86cd799439011"],
    types=[DataType.STRING],
    validator=MongoObjectId.validate,
)

# Network & Web

DOMAIN = SchemaFormat(
    key="domain",
    title="Domain Name",
    examples=["example.com", "sub.example.co.uk"],
    types=[DataType.STRING],
    validator=DomainStr._validate,  # noqa: SLF001
)

PHONE_NUMBER = SchemaFormat(
    key="phone-number",
    title="Phone Number",
    examples=["+1-202-555-0173", "+44 20 7946 0958"],
    types=[DataType.STRING],
    validator=lambda value: PhoneNumber._validate(value, None),  # type: ignore[arg-type]  # noqa: SLF001
)

S3_PATH = SchemaFormat(
    key="s3-path",
    title="AWS S3 Path",
    examples=["s3://bucket-name/path/to/file.txt"],
    types=[DataType.STRING],
    validator=lambda value: S3Path._validate(value, None),  # type: ignore[arg-type]  # noqa: SLF001
)

# Financial

PAYMENT_CARD_NUMBER = SchemaFormat(
    key="payment-card-number",
    title="Payment Card Number",
    examples=["4532015112830366", "5425233430109903"],
    types=[DataType.STRING],
    validator=lambda value: PaymentCardNumber.validate(value, None),  # type: ignore[arg-type]
)

# Note: ABARoutingNumber is not included because it does not have any validate methods

# Other

TIMEZONE_NAME = SchemaFormat(
    key="timezone-name",
    title="IANA Timezone Name",
    examples=["America/New_York", "Europe/London", "Asia/Tokyo"],
    types=[DataType.STRING],
    validator=lambda value: TimeZoneName._validate(value, None),  # type: ignore[arg-type]  # noqa: SLF001
)

SEMANTIC_VERSION = SchemaFormat(
    key="semantic-version",
    title="Semantic Version",
    examples=["1.2.3", "2.0.0-alpha.1", "1.0.0+20130313144700"],
    types=[DataType.STRING],
    validator=SemanticVersion.validate_from_str,
)
