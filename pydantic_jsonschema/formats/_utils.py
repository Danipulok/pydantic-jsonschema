"""Shared utilities for format validators."""

from pydantic_jsonschema.exceptions import FormatValidationError
from pydantic_jsonschema.types import JsonType

__all__ = ["check_str"]


def check_str(value: JsonType) -> str:
    """Validate that a value is a string.

    :param value: Value to check.
    :returns: The value if it is a string.
    :raises FormatValidationError: If value is not a string.
    """
    if not isinstance(value, str):
        msg = f"Expected string, got: `{value!r}`"
        raise FormatValidationError(
            message=msg,
            value=value,
        )
    return value
