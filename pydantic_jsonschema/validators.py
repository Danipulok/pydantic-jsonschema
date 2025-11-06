"""
Format validators for JSON Schema formats.

Uses Python standard library for common formats:
- date, time, date-time: datetime module
- ipv4, ipv6: ipaddress module
- uuid: uuid module
- email: simple validation
- hostname: basic validation
- uri, uri-reference: urllib.parse

For complex formats (IRI, currency, language codes), use pydantic-extra-types.
"""

import ipaddress
import re
from datetime import date, datetime, time
from typing import Any
from urllib.parse import urlparse
from uuid import UUID

__all__ = [
    "validate_date",
    "validate_time",
    "validate_datetime",
    "validate_duration",
    "validate_email",
    "validate_hostname",
    "validate_ipv4",
    "validate_ipv6",
    "validate_uuid",
    "validate_uri",
    "validate_uri_reference",
]


# Date/Time validators
def validate_date(value: Any) -> str:
    """
    Validate ISO 8601 date format (YYYY-MM-DD).

    :param value: Value to validate.
    :returns: Original value if valid.
    :raises ValueError: If value is not a valid date.
    """
    if not isinstance(value, str):
        raise ValueError(f"Expected string, got {type(value).__name__}")

    try:
        date.fromisoformat(value)
        return value
    except ValueError as e:
        raise ValueError(f"Invalid date format: {value}") from e


def validate_time(value: Any) -> str:
    """
    Validate ISO 8601 time format (HH:MM:SS or HH:MM:SS.ffffff with optional timezone).

    :param value: Value to validate.
    :returns: Original value if valid.
    :raises ValueError: If value is not a valid time.
    """
    if not isinstance(value, str):
        raise ValueError(f"Expected string, got {type(value).__name__}")

    try:
        # Try parsing with datetime module
        time.fromisoformat(value)
        return value
    except ValueError as e:
        raise ValueError(f"Invalid time format: {value}") from e


def validate_datetime(value: Any) -> str:
    """
    Validate ISO 8601 datetime format (RFC 3339).

    :param value: Value to validate.
    :returns: Original value if valid.
    :raises ValueError: If value is not a valid datetime.
    """
    if not isinstance(value, str):
        raise ValueError(f"Expected string, got {type(value).__name__}")

    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return value
    except ValueError as e:
        raise ValueError(f"Invalid datetime format: {value}") from e


# ISO 8601 Duration validator
_DURATION_PATTERN = re.compile(
    r"^P(?:\d+Y)?(?:\d+M)?(?:\d+W)?(?:\d+D)?"
    r"(?:T(?:\d+H)?(?:\d+M)?(?:\d+(?:\.\d+)?S)?)?$"
)


def validate_duration(value: Any) -> str:
    """
    Validate ISO 8601 duration format (P[n]Y[n]M[n]DT[n]H[n]M[n]S).

    :param value: Value to validate.
    :returns: Original value if valid.
    :raises ValueError: If value is not a valid duration.
    """
    if not isinstance(value, str):
        raise ValueError(f"Expected string, got {type(value).__name__}")

    if not _DURATION_PATTERN.match(value):
        raise ValueError(f"Invalid duration format: {value}")

    # Must have at least one time component
    if value == "P" or value == "PT":
        raise ValueError(f"Duration must have at least one component: {value}")

    return value


# Email validator
_EMAIL_PATTERN = re.compile(
    r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}"
    r"[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
)


def validate_email(value: Any) -> str:
    """
    Validate email address format (simple validation).

    :param value: Value to validate.
    :returns: Original value if valid.
    :raises ValueError: If value is not a valid email.
    """
    if not isinstance(value, str):
        raise ValueError(f"Expected string, got {type(value).__name__}")

    if not _EMAIL_PATTERN.match(value):
        raise ValueError(f"Invalid email format: {value}")

    return value


# Hostname validator
_HOSTNAME_PATTERN = re.compile(
    r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.[A-Za-z0-9-]{1,63})*$"
)


def validate_hostname(value: Any) -> str:
    """
    Validate hostname format (RFC 1123).

    :param value: Value to validate.
    :returns: Original value if valid.
    :raises ValueError: If value is not a valid hostname.
    """
    if not isinstance(value, str):
        raise ValueError(f"Expected string, got {type(value).__name__}")

    if not _HOSTNAME_PATTERN.match(value):
        raise ValueError(f"Invalid hostname format: {value}")

    return value


# IP address validators
def validate_ipv4(value: Any) -> str:
    """
    Validate IPv4 address format.

    :param value: Value to validate.
    :returns: Original value if valid.
    :raises ValueError: If value is not a valid IPv4 address.
    """
    if not isinstance(value, str):
        raise ValueError(f"Expected string, got {type(value).__name__}")

    try:
        ipaddress.IPv4Address(value)
        return value
    except ipaddress.AddressValueError as e:
        raise ValueError(f"Invalid IPv4 address: {value}") from e


def validate_ipv6(value: Any) -> str:
    """
    Validate IPv6 address format.

    :param value: Value to validate.
    :returns: Original value if valid.
    :raises ValueError: If value is not a valid IPv6 address.
    """
    if not isinstance(value, str):
        raise ValueError(f"Expected string, got {type(value).__name__}")

    try:
        ipaddress.IPv6Address(value)
        return value
    except ipaddress.AddressValueError as e:
        raise ValueError(f"Invalid IPv6 address: {value}") from e


# UUID validator
def validate_uuid(value: Any) -> str:
    """
    Validate UUID format (RFC 4122).

    :param value: Value to validate.
    :returns: Original value if valid.
    :raises ValueError: If value is not a valid UUID.
    """
    if not isinstance(value, str):
        raise ValueError(f"Expected string, got {type(value).__name__}")

    try:
        # Validate UUID format and check hyphens are in correct positions
        uuid_obj = UUID(value)
        # Ensure canonical format with hyphens
        if value != str(uuid_obj):
            raise ValueError(f"UUID must be in canonical format: {value}")
        return value
    except (ValueError, AttributeError) as e:
        raise ValueError(f"Invalid UUID format: {value}") from e


# URI validators
def validate_uri(value: Any) -> str:
    """
    Validate URI format (RFC 3986).

    :param value: Value to validate.
    :returns: Original value if valid.
    :raises ValueError: If value is not a valid URI.
    """
    if not isinstance(value, str):
        raise ValueError(f"Expected string, got {type(value).__name__}")

    try:
        result = urlparse(value)
        # URI must have scheme
        if not result.scheme:
            raise ValueError(f"URI must have scheme: {value}")
        return value
    except Exception as e:
        raise ValueError(f"Invalid URI format: {value}") from e


def validate_uri_reference(value: Any) -> str:
    """
    Validate URI reference format (RFC 3986).
    Can be absolute URI, relative reference, or fragment.

    :param value: Value to validate.
    :returns: Original value if valid.
    :raises ValueError: If value is not a valid URI reference.
    """
    if not isinstance(value, str):
        raise ValueError(f"Expected string, got {type(value).__name__}")

    try:
        # URI reference can be relative, so we don't require scheme
        urlparse(value)
        return value
    except Exception as e:
        raise ValueError(f"Invalid URI reference format: {value}") from e
