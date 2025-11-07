import ipaddress
import re
from datetime import date, datetime, time
from typing import Any
from urllib.parse import urlparse
from uuid import UUID

from pydantic_jsonschema.exceptions import FormatValidationError

__all__ = [
    "validate_date",
    "validate_datetime",
    "validate_duration",
    "validate_email",
    "validate_hostname",
    "validate_ipv4",
    "validate_ipv6",
    "validate_iri",
    "validate_iri_reference",
    "validate_time",
    "validate_uri",
    "validate_uri_reference",
    "validate_uuid",
]


# Date/Time validators
def validate_date(value: Any) -> str:
    """
    Validate ISO 8601 date format (YYYY-MM-DD).

    :param value: Value to validate.
    :returns: Original value if valid.
    :raises FormatValidationError: If value is not a valid date.
    """
    if not isinstance(value, str):
        msg = f"Expected string, got: `{value!r}`"
        raise FormatValidationError(
            message=msg,
            value=value,
        )

    try:
        date.fromisoformat(value)
    except ValueError:
        msg = f"Invalid date format: `{value!r}`"
        raise FormatValidationError(
            message=msg,
            value=value,
        ) from None

    return value


def validate_time(value: Any) -> str:
    """
    Validate ISO 8601 time format (HH:MM:SS or HH:MM:SS.ffffff with optional timezone).

    :param value: Value to validate.
    :returns: Original value if valid.
    :raises FormatValidationError: If value is not a valid time.
    """
    if not isinstance(value, str):
        msg = f"Expected string, got: `{value!r}`"
        raise FormatValidationError(
            message=msg,
            value=value,
        )

    try:
        time.fromisoformat(value)
    except ValueError:
        msg = f"Invalid time format: `{value!r}`"
        raise FormatValidationError(
            message=msg,
            value=value,
        ) from None

    return value


def validate_datetime(value: Any) -> str:
    """
    Validate ISO 8601 datetime format (RFC 3339).

    :param value: Value to validate.
    :returns: Original value if valid.
    :raises FormatValidationError: If value is not a valid datetime.
    """
    if not isinstance(value, str):
        msg = f"Expected string, got: `{value!r}`"
        raise FormatValidationError(
            message=msg,
            value=value,
        )

    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        msg = f"Invalid datetime format: `{value!r}`"
        raise FormatValidationError(
            message=msg,
            value=value,
        ) from None

    return value


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
    :raises FormatValidationError: If value is not a valid duration.
    """
    if not isinstance(value, str):
        msg = f"Expected string, got: `{value!r}`"
        raise FormatValidationError(
            message=msg,
            value=value,
        )

    if not _DURATION_PATTERN.match(value):
        msg = f"Invalid duration format: `{value!r}`"
        raise FormatValidationError(
            message=msg,
            value=value,
        )

    # Must have at least one time component
    if value in {"P", "PT"}:
        msg = f"Duration must have at least one component: `{value!r}`"
        raise FormatValidationError(
            message=msg,
            value=value,
        )

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
    :raises FormatValidationError: If value is not a valid email.
    """
    if not isinstance(value, str):
        msg = f"Expected string, got: `{value!r}`"
        raise FormatValidationError(
            message=msg,
            value=value,
        )

    if not _EMAIL_PATTERN.match(value):
        msg = f"Invalid email format: `{value!r}`"
        raise FormatValidationError(
            message=msg,
            value=value,
        )

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
    :raises FormatValidationError: If value is not a valid hostname.
    """
    if not isinstance(value, str):
        msg = f"Expected string, got: `{value!r}`"
        raise FormatValidationError(
            message=msg,
            value=value,
        )

    if not _HOSTNAME_PATTERN.match(value):
        msg = f"Invalid hostname format: `{value!r}`"
        raise FormatValidationError(
            message=msg,
            value=value,
        )

    return value


# IP address validators
def validate_ipv4(value: Any) -> str:
    """
    Validate IPv4 address format.

    :param value: Value to validate.
    :returns: Original value if valid.
    :raises FormatValidationError: If value is not a valid IPv4 address.
    """
    if not isinstance(value, str):
        msg = f"Expected string, got: `{value!r}`"
        raise FormatValidationError(
            message=msg,
            value=value,
        )

    try:
        ipaddress.IPv4Address(value)
    except ipaddress.AddressValueError:
        msg = f"Invalid IPv4 address: `{value!r}`"
        raise FormatValidationError(
            message=msg,
            value=value,
        ) from None

    return value


def validate_ipv6(value: Any) -> str:
    """
    Validate IPv6 address format.

    :param value: Value to validate.
    :returns: Original value if valid.
    :raises FormatValidationError: If value is not a valid IPv6 address.
    """
    if not isinstance(value, str):
        msg = f"Expected string, got: `{value!r}`"
        raise FormatValidationError(
            message=msg,
            value=value,
        )

    try:
        ipaddress.IPv6Address(value)
    except ipaddress.AddressValueError:
        msg = f"Invalid IPv6 address: `{value!r}`"
        raise FormatValidationError(
            message=msg,
            value=value,
        ) from None

    return value


# UUID validator
def validate_uuid(value: Any) -> str:
    """
    Validate UUID format (RFC 4122).

    :param value: Value to validate.
    :returns: Original value if valid.
    :raises FormatValidationError: If value is not a valid UUID.
    """
    if not isinstance(value, str):
        msg = f"Expected string, got: `{value!r}`"
        raise FormatValidationError(
            message=msg,
            value=value,
        )

    try:
        uuid_obj = UUID(value)
        # Ensure canonical format with hyphens
        if value != str(uuid_obj):
            msg = f"UUID must be in canonical format: `{value!r}`"
            raise FormatValidationError(
                message=msg,
                value=value,
            )
    except (ValueError, AttributeError):
        msg = f"Invalid UUID format: `{value!r}`"
        raise FormatValidationError(
            message=msg,
            value=value,
        ) from None

    return value


# URI validators
def validate_uri(value: Any) -> str:
    """
    Validate URI format (RFC 3986).

    :param value: Value to validate.
    :returns: Original value if valid.
    :raises FormatValidationError: If value is not a valid URI.
    """
    if not isinstance(value, str):
        msg = f"Expected string, got: `{value!r}`"
        raise FormatValidationError(
            message=msg,
            value=value,
        )

    try:
        result = urlparse(value)
    except Exception:  # noqa: BLE001
        msg = f"Invalid URI format: `{value!r}`"
        raise FormatValidationError(
            message=msg,
            value=value,
        ) from None

    # URI must have scheme
    if not result.scheme:
        msg = f"URI must have scheme: `{value!r}`"
        raise FormatValidationError(
            message=msg,
            value=value,
        )

    return value


def validate_uri_reference(value: Any) -> str:
    """
    Validate URI reference format (RFC 3986).
    Can be absolute URI, relative reference, or fragment.

    :param value: Value to validate.
    :returns: Original value if valid.
    :raises FormatValidationError: If value is not a valid URI reference.
    """
    if not isinstance(value, str):
        msg = f"Expected string, got: `{value!r}`"
        raise FormatValidationError(
            message=msg,
            value=value,
        )

    try:
        urlparse(value)
    except Exception:  # noqa: BLE001
        msg = f"Invalid URI reference format: `{value!r}`"
        raise FormatValidationError(
            message=msg,
            value=value,
        ) from None

    return value


# IRI validators (Internationalized Resource Identifier)
def validate_iri(value: Any) -> str:
    """
    Validate IRI format (RFC 3987).
    Similar to URI but allows international characters.

    Note: This is a basic validation. For full RFC 3987 compliance,
    consider using a dedicated library like rfc3987.

    :param value: Value to validate.
    :returns: Original value if valid.
    :raises FormatValidationError: If value is not a valid IRI.
    """
    if not isinstance(value, str):
        msg = f"Expected string, got: `{value!r}`"
        raise FormatValidationError(
            message=msg,
            value=value,
        )

    try:
        result = urlparse(value)
    except Exception:  # noqa: BLE001
        msg = f"Invalid IRI format: `{value!r}`"
        raise FormatValidationError(
            message=msg,
            value=value,
        ) from None

    # IRI must have scheme
    if not result.scheme:
        msg = f"IRI must have scheme: `{value!r}`"
        raise FormatValidationError(
            message=msg,
            value=value,
        )

    return value


def validate_iri_reference(value: Any) -> str:
    """
    Validate IRI reference format (RFC 3987).
    Similar to URI reference but allows international characters.

    Note: This is a basic validation. For full RFC 3987 compliance,
    consider using a dedicated library like rfc3987.

    :param value: Value to validate.
    :returns: Original value if valid.
    :raises FormatValidationError: If value is not a valid IRI reference.
    """
    if not isinstance(value, str):
        msg = f"Expected string, got: `{value!r}`"
        raise FormatValidationError(
            message=msg,
            value=value,
        )

    try:
        urlparse(value)
    except Exception:  # noqa: BLE001
        msg = f"Invalid IRI reference format: `{value!r}`"
        raise FormatValidationError(
            message=msg,
            value=value,
        ) from None

    return value
