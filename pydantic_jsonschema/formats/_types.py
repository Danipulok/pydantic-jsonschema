"""Built-in JSON Schema format types.

All format types are defined as Pydantic-compatible type aliases using `Annotated`.
These types can be used in schemas or passed as `format_validators` to `SchemaConverter`.
"""

import uuid
from datetime import date, datetime, time, timedelta
from ipaddress import IPv4Address, IPv6Address
from typing import Annotated

from pydantic import AfterValidator

from pydantic_jsonschema.formats._email import validate_email
from pydantic_jsonschema.formats._hostname import validate_hostname
from pydantic_jsonschema.formats._uri import (
    validate_iri,
    validate_iri_reference,
    validate_uri,
    validate_uri_reference,
)

__all__ = [
    "UUID",
    "Date",
    "DateTime",
    "Duration",
    "Email",
    "Hostname",
    "IPv4",
    "IPv6",
    "Iri",
    "IriReference",
    "Time",
    "Uri",
    "UriReference",
]

# Date/Time formats (Pydantic native support)
DateTime = datetime
Time = time
Date = date
Duration = timedelta

# String formats
Email = Annotated[str, AfterValidator(validate_email)]
Hostname = Annotated[str, AfterValidator(validate_hostname)]
UUID = uuid.UUID

# IP formats (Pydantic native support)
IPv4 = IPv4Address
IPv6 = IPv6Address

# URI/IRI formats
Uri = Annotated[str, AfterValidator(validate_uri)]
UriReference = Annotated[str, AfterValidator(validate_uri_reference)]
Iri = Annotated[str, AfterValidator(validate_iri)]
IriReference = Annotated[str, AfterValidator(validate_iri_reference)]
