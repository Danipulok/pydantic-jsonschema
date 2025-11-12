"""Built-in JSON Schema format validators."""

import uuid
from datetime import date, datetime, time, timedelta
from ipaddress import IPv4Address, IPv6Address

from pydantic import EmailStr

from pydantic_jsonschema.formats._base import SchemaFormat
from pydantic_jsonschema.formats._validators import (
    validate_hostname,
    validate_iri,
    validate_iri_reference,
    validate_uri,
    validate_uri_reference,
)
from pydantic_jsonschema.types import DataType

__all__ = [
    "DATE",
    "DATE_TIME",
    "DURATION",
    "EMAIL",
    "HOSTNAME",
    "IPV4",
    "IPV6",
    "IRI",
    "IRI_REFERENCE",
    "TIME",
    "URI",
    "URI_REFERENCE",
    "UUID",
]


DATE_TIME = SchemaFormat(
    key="date-time",
    title="Date Time",
    examples=["2018-11-13T20:20:39+00:00"],
    types=[DataType.STRING],
    validator=datetime,
)
TIME = SchemaFormat(
    key="time",
    title="Time",
    examples=["20:20:39+00:00"],
    types=[DataType.STRING],
    validator=time,
)
DATE = SchemaFormat(
    key="date",
    title="Date",
    examples=["2018-11-13"],
    types=[DataType.STRING],
    validator=date,
)
DURATION = SchemaFormat(
    key="duration",
    title="Duration",
    examples=["P3D"],
    types=[DataType.STRING],
    validator=timedelta,
)
EMAIL = SchemaFormat(
    key="email",
    title="Email",
    examples=["example@example.com"],
    types=[DataType.STRING],
    validator=EmailStr,
)
HOSTNAME = SchemaFormat(
    key="hostname",
    title="Hostname",
    examples=["example.com"],
    types=[DataType.STRING],
    validator=validate_hostname,
)
IPV4 = SchemaFormat(
    key="ipv4",
    title="IPv4",
    examples=["192.168.1.1"],
    types=[DataType.STRING],
    validator=IPv4Address,
)
IPV6 = SchemaFormat(
    key="ipv6",
    title="IPv6",
    examples=["2001:0db8:85a3:0000:0000:8a2e:0370:7334"],
    types=[DataType.STRING],
    validator=IPv6Address,
)
UUID = SchemaFormat(
    key="uuid",
    title="UUID",
    examples=["3e4666bf-d5e5-4aa7-b8ce-cefe41c7568a"],
    types=[DataType.STRING],
    validator=uuid.UUID,
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
