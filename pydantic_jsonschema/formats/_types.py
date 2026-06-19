"""Built-in JSON Schema format types.

All format types are defined as Pydantic-compatible type aliases using `Annotated`.
These types can be used in schemas or passed as `format_validators` to `SchemaConverter`.
"""

import uuid
from datetime import date, datetime, time, timedelta
from ipaddress import IPv4Address, IPv6Address
from typing import Annotated

from pydantic import AfterValidator

from pydantic_jsonschema.formats._email import validate_email, validate_idn_email
from pydantic_jsonschema.formats._hostname import validate_hostname, validate_idn_hostname
from pydantic_jsonschema.formats._json_pointer import (
    validate_json_pointer,
    validate_relative_json_pointer,
)
from pydantic_jsonschema.formats._regex import validate_regex
from pydantic_jsonschema.formats._uri import (
    validate_iri,
    validate_iri_reference,
    validate_uri,
    validate_uri_reference,
)
from pydantic_jsonschema.formats._uri_template import validate_uri_template

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

# Date/Time formats (Pydantic native support)
type DateTime = datetime
"""Date-time value.

Source: [RFC 3339](https://www.rfc-editor.org/rfc/rfc3339)
"""
type Time = time
"""Time value.

Source: [RFC 3339](https://www.rfc-editor.org/rfc/rfc3339)
"""
type Date = date
"""Calendar date.

Source: [RFC 3339](https://www.rfc-editor.org/rfc/rfc3339)
"""
type Duration = timedelta
"""Duration.

Source: [RFC 3339, appendix A](https://www.rfc-editor.org/rfc/rfc3339#appendix-A)
"""

# String formats
type Email = Annotated[str, AfterValidator(validate_email)]
"""Email address.

Source: [RFC 5321](https://www.rfc-editor.org/rfc/rfc5321#section-4.1.2)
"""
type IdnEmail = Annotated[str, AfterValidator(validate_idn_email)]
"""Internationalized email address.

Source: [RFC 6531](https://www.rfc-editor.org/rfc/rfc6531#section-3.3)
"""
type Hostname = Annotated[str, AfterValidator(validate_hostname)]
"""Hostname.

Source: [RFC 1123](https://www.rfc-editor.org/rfc/rfc1123#section-2.1)
"""
type IdnHostname = Annotated[str, AfterValidator(validate_idn_hostname)]
"""Internationalized hostname.

Source: [RFC 5890](https://www.rfc-editor.org/rfc/rfc5890#section-2.3.2.3)
"""
type UUID = uuid.UUID
"""UUID value.

Source: [RFC 4122](https://www.rfc-editor.org/rfc/rfc4122)
"""
type Regex = Annotated[str, AfterValidator(validate_regex)]
"""Regular expression, ECMA-262 dialect.

Source: [JSON Schema §7.3.8](https://json-schema.org/draft/2020-12/json-schema-validation#section-7.3.8)
"""

# IP formats (Pydantic native support)
type IPv4 = IPv4Address
"""IPv4 address.

Source: [RFC 2673, section 3.2](https://www.rfc-editor.org/rfc/rfc2673#section-3.2)
"""
type IPv6 = IPv6Address
"""IPv6 address.

Source: [RFC 4291, section 2.2](https://www.rfc-editor.org/rfc/rfc4291#section-2.2)
"""

# URI/IRI formats
type Uri = Annotated[str, AfterValidator(validate_uri)]
"""Absolute URI with a scheme.

Source: [RFC 3986](https://www.rfc-editor.org/rfc/rfc3986)
"""
type UriReference = Annotated[str, AfterValidator(validate_uri_reference)]
"""URI reference, absolute or relative.

Source: [RFC 3986, section 4.1](https://www.rfc-editor.org/rfc/rfc3986#section-4.1)
"""
type Iri = Annotated[str, AfterValidator(validate_iri)]
"""Absolute internationalized URI.

Source: [RFC 3987](https://www.rfc-editor.org/rfc/rfc3987)
"""
type IriReference = Annotated[str, AfterValidator(validate_iri_reference)]
"""IRI reference, absolute or relative.

Source: [RFC 3987](https://www.rfc-editor.org/rfc/rfc3987)
"""
type UriTemplate = Annotated[str, AfterValidator(validate_uri_template)]
"""URI Template.

Source: [RFC 6570](https://www.rfc-editor.org/rfc/rfc6570#section-2)
"""

# JSON Pointer formats
type JsonPointer = Annotated[str, AfterValidator(validate_json_pointer)]
"""JSON Pointer.

Source: [RFC 6901](https://www.rfc-editor.org/rfc/rfc6901#section-3)
"""
type RelativeJsonPointer = Annotated[str, AfterValidator(validate_relative_json_pointer)]
"""Relative JSON Pointer.

Source: [draft-bhutton-relative-json-pointer-00](https://datatracker.ietf.org/doc/html/draft-bhutton-relative-json-pointer-00#section-3)
"""
