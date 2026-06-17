"""Email format validators.

See: https://www.rfc-editor.org/rfc/rfc5321#section-4.1.2
See: https://www.rfc-editor.org/rfc/rfc5322#section-3.4.1
See: https://www.rfc-editor.org/rfc/rfc6531#section-3.3
"""

import re
from typing import Final

from pydantic_jsonschema.exceptions import FormatValidationError
from pydantic_jsonschema.formats._hostname import validate_hostname, validate_idn_hostname

__all__ = [
    "validate_email",
    "validate_idn_email",
]

# See: https://www.rfc-editor.org/rfc/rfc5321#section-4.1.2
# Local part: dot-separated atoms of atext characters (letters, digits, and specials).
_LOCAL_RE: Final[re.Pattern[str]] = re.compile(
    r"^[a-zA-Z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-zA-Z0-9!#$%&'*+/=?^_`{|}~-]+)*$",
)

# See: https://www.rfc-editor.org/rfc/rfc6531#section-3.3
# SMTPUTF8 extends atext with any non-ASCII character (`UTF8-non-ascii`).
_IDN_LOCAL_RE: Final[re.Pattern[str]] = re.compile(
    r"^[a-zA-Z0-9!#$%&'*+/=?^_`{|}~\u0080-\U0010FFFF-]+"
    r"(?:\.[a-zA-Z0-9!#$%&'*+/=?^_`{|}~\u0080-\U0010FFFF-]+)*$",
)

# See: https://www.rfc-editor.org/rfc/rfc5321#section-4.5.3.1
# RFC 6531 keeps the same octet limits, so IDN checks count UTF-8 bytes.
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


def validate_idn_email(value: str) -> str:
    """Validate internationalized email format per RFC 6531, section 3.3.

    The local part accepts non-ASCII characters (SMTPUTF8 `atext`),
    and the domain part is validated as an internationalized hostname.
    Octet limits are checked against the UTF-8 encoding per RFC 6531.

    :param value: Value to validate.
    :returns: Original value if valid.
    :raises FormatValidationError: If value is not a valid internationalized email.
    """
    if len(value.encode("utf-8")) > _MAX_EMAIL_LENGTH or value.count("@") != 1:
        msg = f"Invalid IDN email format: `{value!r}`"
        raise FormatValidationError(
            message=msg,
            value=value,
        )

    local: str
    domain: str
    local, domain = value.split("@")

    if (
        not local
        or len(local.encode("utf-8")) > _MAX_LOCAL_LENGTH
        or not _IDN_LOCAL_RE.match(local)
    ):
        msg = f"Invalid IDN email format: `{value!r}`"
        raise FormatValidationError(
            message=msg,
            value=value,
        )

    try:
        validate_idn_hostname(domain)
    # Domain part failed IDN hostname validation.
    except ValueError:
        msg = f"Invalid IDN email format: `{value!r}`"
        raise FormatValidationError(
            message=msg,
            value=value,
        ) from None

    return value
