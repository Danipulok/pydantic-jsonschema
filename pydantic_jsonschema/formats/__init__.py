"""Built-in format types for JSON Schema validation.

This module exports Pydantic-compatible types for all formats defined in
[JSON Schema §7.3](https://json-schema.org/draft/2020-12/json-schema-validation#section-7.3).
Use them directly in Pydantic models or pass them as `formats` to `SchemaConverter`.
"""

from ._types import (
    UUID,
    Date,
    DateTime,
    Duration,
    Email,
    Hostname,
    IdnEmail,
    IdnHostname,
    IPv4,
    IPv6,
    Iri,
    IriReference,
    JsonPointer,
    Regex,
    RelativeJsonPointer,
    Time,
    Uri,
    UriReference,
    UriTemplate,
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
    "IdnEmail",
    "IdnHostname",
    "Iri",
    "IriReference",
    "JsonPointer",
    "Regex",
    "RelativeJsonPointer",
    "Time",
    "Uri",
    "UriReference",
    "UriTemplate",
]
