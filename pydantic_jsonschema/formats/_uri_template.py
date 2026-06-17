"""URI Template format validator.

See: https://www.rfc-editor.org/rfc/rfc6570#section-2
"""

import re
from typing import Final

from pydantic_jsonschema.exceptions import FormatValidationError

__all__ = ["validate_uri_template"]

# See: https://www.rfc-editor.org/rfc/rfc6570#section-2.3
_VARCHAR: Final[str] = r"(?:[A-Za-z0-9_]|%[0-9A-Fa-f]{2})"
_VARNAME: Final[str] = rf"{_VARCHAR}(?:\.?{_VARCHAR})*"
# Varspec = varname with an optional prefix (`:1`-`:9999`) or explode (`*`) modifier.
_VARSPEC: Final[str] = rf"{_VARNAME}(?::[1-9][0-9]{{0,3}}|\*)?"

# See: https://www.rfc-editor.org/rfc/rfc6570#section-2.2
# Expression = `{` + optional operator + comma-separated varspec list + `}`.
_EXPRESSION: Final[str] = rf"\{{[+#./;?&=,!@|]?{_VARSPEC}(?:,{_VARSPEC})*\}}"

# See: https://www.rfc-editor.org/rfc/rfc6570#section-2.1
# Literals: any character except controls, space, and `" ' % < > \ ^ ` { | }`;
# `%` is only allowed as a percent-encoded triplet.
_LITERAL: Final[str] = r"(?:[^\x00-\x20\x7f\"'%<>\\^`{|}]|%[0-9A-Fa-f]{2})"

_URI_TEMPLATE_RE: Final[re.Pattern[str]] = re.compile(rf"^(?:{_LITERAL}|{_EXPRESSION})*$")


def validate_uri_template(value: str) -> str:
    """Validate URI Template format per RFC 6570, section 2.

    :param value: Value to validate.
    :returns: Original value if valid.
    :raises FormatValidationError: If value is not a valid URI Template.
    """
    if not _URI_TEMPLATE_RE.match(value):
        msg = f"Invalid URI Template format: `{value!r}`"
        raise FormatValidationError(
            message=msg,
            value=value,
        )

    return value
