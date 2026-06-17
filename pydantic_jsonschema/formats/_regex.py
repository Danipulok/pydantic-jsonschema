"""Regular expression format validator.

See: https://json-schema.org/draft/2020-12/json-schema-validation#section-7.3.8
"""

import re

from pydantic_jsonschema.exceptions import FormatValidationError

__all__ = ["validate_regex"]


def validate_regex(value: str) -> str:
    """Validate regular expression format per JSON Schema validation, section 7.3.8.

    The spec requires the ECMA-262 dialect; this validator compiles with Python `re`,
    which is a close superset for common patterns (see details in `docs/formats.md`).

    :param value: Value to validate.
    :returns: Original value if valid.
    :raises FormatValidationError: If value is not a valid regular expression.
    """
    try:
        re.compile(value)
    # Invalid regular expression syntax.
    except re.error:
        msg = f"Invalid regular expression format: `{value!r}`"
        raise FormatValidationError(
            message=msg,
            value=value,
        ) from None

    return value
