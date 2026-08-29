"""Hostname format validators.

See: https://www.rfc-editor.org/rfc/rfc1123#section-2.1
See: https://www.rfc-editor.org/rfc/rfc1035#section-2.3.4
See: https://www.rfc-editor.org/rfc/rfc5890#section-2.3.2.3
"""

import re
from typing import Final

from pydantic_jsonschema.exceptions import FormatValidationError

__all__ = [
    "validate_hostname",
    "validate_idn_hostname",
]

# See: https://www.rfc-editor.org/rfc/rfc1123#section-2.1
#  Each label: 1-63 alphanumeric/hyphen chars, no leading/trailing hyphen.
#  Trailing dot allowed (absolute FQDN).
#  Case-insensitive.
_HOSTNAME_RE: Final[re.Pattern[str]] = re.compile(
    r"^(?!-)[-A-Z\d]{1,63}(?<!-)(?:\.(?!-)[-A-Z\d]{1,63}(?<!-))*\.?$",
    re.IGNORECASE,
)

# See: https://www.rfc-editor.org/rfc/rfc1035#section-2.3.4
#  RFC 1035 specifies 255 octets in wire format (length-prefixed labels + null terminator).
#  Text representation replaces those 2 overhead bytes with dot separators: 255 - 2 = 253.
_MAX_HOSTNAME_LENGTH: Final[int] = 253


def validate_hostname(value: str) -> str:
    """Validate hostname format per RFC 1123, section 2.1.

    :param value: Value to validate.
    :returns: Original value if valid.
    :raises FormatValidationError: If value is not a valid hostname.
    """
    length: int = len(value.rstrip("."))
    if length == 0 or length > _MAX_HOSTNAME_LENGTH or not _HOSTNAME_RE.match(value):
        msg = f"Invalid hostname format: `{value!r}`"
        raise FormatValidationError(
            message=msg,
            value=value,
        )

    return value


def validate_idn_hostname(value: str) -> str:
    """Validate internationalized hostname format per RFC 5890, section 2.3.2.3.

    The hostname is converted to its ASCII (punycode) form via the stdlib `idna`
    codec and then validated as a regular hostname.
    The stdlib codec implements IDNA 2003, which is slightly more permissive than
    the IDNA 2008 tables required by the spec (see details in `docs/formats.md`)

    :param value: Value to validate.
    :returns: Original value if valid.
    :raises FormatValidationError: If value is not a valid internationalized hostname.
    """
    try:
        ascii_hostname: str = value.encode("idna").decode("ascii")
    # Empty/oversized labels and characters are rejected by nameprep.
    except UnicodeError:
        msg = f"Invalid IDN hostname format: `{value!r}`"
        raise FormatValidationError(
            message=msg,
            value=value,
        ) from None

    try:
        validate_hostname(ascii_hostname)
    # The ASCII form must satisfy the regular hostname rules (STD3, total length).
    except FormatValidationError:
        msg = f"Invalid IDN hostname format: `{value!r}`"
        raise FormatValidationError(
            message=msg,
            value=value,
        ) from None

    return value
