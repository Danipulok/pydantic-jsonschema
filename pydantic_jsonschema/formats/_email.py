"""Email format validator.

See: https://www.rfc-editor.org/rfc/rfc5321#section-4.1.2
See: https://www.rfc-editor.org/rfc/rfc5322#section-3.4.1
"""

import re
from typing import Final

from pydantic_jsonschema.exceptions import FormatValidationError
from pydantic_jsonschema.formats._hostname import validate_hostname

__all__ = ["validate_email"]

# See: https://www.rfc-editor.org/rfc/rfc5321#section-4.1.2
# Local part: dot-separated atoms of atext characters (letters, digits, and specials).
_LOCAL_RE: Final[re.Pattern[str]] = re.compile(
    r"^[a-zA-Z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-zA-Z0-9!#$%&'*+/=?^_`{|}~-]+)*$",
)

# See: https://www.rfc-editor.org/rfc/rfc5321#section-4.5.3.1
_MAX_LOCAL_LENGTH: Final[int] = 64
_MAX_EMAIL_LENGTH: Final[int] = 254


def validate_email(value: str) -> str:
    """Validate email format per RFC 5321, section 4.1.2.

    :param value: Value to validate.
    :returns: Original value if valid.
    :raises FormatValidationError: If value is not a valid email address.
    """
    if len(value) > _MAX_EMAIL_LENGTH or value.count("@") != 1:
        msg = f"Invalid email format: `{value!r}`"
        raise FormatValidationError(
            message=msg,
            value=value,
        )

    local: str
    domain: str
    local, domain = value.split("@")

    if not local or len(local) > _MAX_LOCAL_LENGTH or not _LOCAL_RE.match(local):
        msg = f"Invalid email format: `{value!r}`"
        raise FormatValidationError(
            message=msg,
            value=value,
        )

    try:
        validate_hostname(domain)
    # Domain part failed hostname validation.
    except ValueError:
        msg = f"Invalid email format: `{value!r}`"
        raise FormatValidationError(
            message=msg,
            value=value,
        ) from None

    return value
