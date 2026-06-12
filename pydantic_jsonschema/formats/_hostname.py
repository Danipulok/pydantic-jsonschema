"""Hostname format validator.

See: https://www.rfc-editor.org/rfc/rfc1123#section-2.1
See: https://www.rfc-editor.org/rfc/rfc1035#section-2.3.4
"""

import re
from typing import Final

from pydantic_jsonschema.exceptions import FormatValidationError

__all__ = ["validate_hostname"]

# See: https://www.rfc-editor.org/rfc/rfc1123#section-2.1
# Each label: 1-63 alphanumeric/hyphen chars, no leading/trailing hyphen.
# Trailing dot allowed (absolute FQDN).
# Case-insensitive.
_HOSTNAME_RE: Final[re.Pattern[str]] = re.compile(
    r"^(?![-])[-A-Z\d]{1,63}(?<!-)(?:\.(?![-])[-A-Z\d]{1,63}(?<!-))*\.?$",
    re.IGNORECASE,
)

# See: https://www.rfc-editor.org/rfc/rfc1035#section-2.3.4
# RFC 1035 specifies 255 octets in wire format (length-prefixed labels + null terminator).
# Text representation replaces those 2 overhead bytes with dot separators: 255 - 2 = 253.
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
