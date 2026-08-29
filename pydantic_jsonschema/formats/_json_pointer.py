"""JSON Pointer format validators.

See: https://www.rfc-editor.org/rfc/rfc6901#section-3
See: https://datatracker.ietf.org/doc/html/draft-bhutton-relative-json-pointer-00#section-3
"""

import re
from typing import Final

from pydantic_jsonschema.exceptions import FormatValidationError

__all__ = [
    "validate_json_pointer",
    "validate_relative_json_pointer",
]

# See: https://www.rfc-editor.org/rfc/rfc6901#section-3
#  Zero or more `/`-prefixed reference tokens; `~` is only valid as `~0` / `~1`.
#  The empty string is a valid pointer (it references the whole document).
#  NOTE: `S105` is a false positive: "reference-token" is the RFC 6901 ABNF rule
#  name for a pointer segment, not a credential.
_REFERENCE_TOKEN: Final[str] = r"(?:[^/~]|~[01])*"  # noqa: S105
_JSON_POINTER_RE: Final[re.Pattern[str]] = re.compile(rf"^(?:/{_REFERENCE_TOKEN})*$")

# See: https://datatracker.ietf.org/doc/html/draft-bhutton-relative-json-pointer-00#section-3
#  Non-negative integer without leading zeros, followed by `#` or a JSON Pointer.
_RELATIVE_JSON_POINTER_RE: Final[re.Pattern[str]] = re.compile(
    rf"^(?:0|[1-9][0-9]*)(?:#|(?:/{_REFERENCE_TOKEN})*)$",
)


def validate_json_pointer(value: str) -> str:
    """Validate JSON Pointer format per RFC 6901, section 3.

    :param value: Value to validate.
    :returns: Original value if valid.
    :raises FormatValidationError: If value is not a valid JSON Pointer.
    """
    if not _JSON_POINTER_RE.match(value):
        msg = f"Invalid JSON Pointer format: `{value!r}`"
        raise FormatValidationError(
            message=msg,
            value=value,
        )

    return value


def validate_relative_json_pointer(value: str) -> str:
    """Validate Relative JSON Pointer format per the Relative JSON Pointer draft.

    :param value: Value to validate.
    :returns: Original value if valid.
    :raises FormatValidationError: If value is not a valid Relative JSON Pointer.
    """
    if not _RELATIVE_JSON_POINTER_RE.match(value):
        msg = f"Invalid Relative JSON Pointer format: `{value!r}`"
        raise FormatValidationError(
            message=msg,
            value=value,
        )

    return value
