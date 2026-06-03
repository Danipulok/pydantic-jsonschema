"""Internal utilities for identifier sanitization."""

import re

__all__ = [
    "sanitize_identifier",
]

_LEADING_NON_ALPHA: re.Pattern[str] = re.compile(r"^[^a-zA-Z_]+")
_INVALID_CHARS: re.Pattern[str] = re.compile(r"[^a-zA-Z0-9_]")


def sanitize_identifier(name: str) -> str:
    """Sanitize string to be a valid Python identifier.

    :param name: String to sanitize.
    :returns: Valid Python identifier.
    """
    name = _LEADING_NON_ALPHA.sub("", name)
    return _INVALID_CHARS.sub("", name)
