"""Internal utilities for identifier sanitization and type validation."""

from collections.abc import Iterator
from typing import Any

from pydantic import TypeAdapter

__all__ = [
    "sanitize_identifier",
    "validate_with_type",
]


# TODO: refactor
def sanitize_identifier(name: str) -> str:
    """Sanitize string to be a valid Python identifier.

    :param name: String to sanitize.
    :returns: Valid Python identifier.
    """

    def _generate_valid_chars(seq: str) -> Iterator[str]:
        """Generate valid characters for Python identifier."""
        iterator = iter(seq)

        # First character must be letter or underscore
        for char in iterator:
            if char == "_" or char.isalpha():
                yield char
                break

        # Rest can be letters, digits, or underscore
        for char in iterator:
            if char == "_" or char.isalpha() or char.isdigit():
                yield char

    return "".join(_generate_valid_chars(name))


def validate_with_type(
    annotation: Any,  # noqa: ANN401
    value: Any,  # noqa: ANN401
) -> Any:  # noqa: ANN401
    """Validate value using Pydantic RootModel with given annotation.

    Creates a temporary RootModel with the given annotation and validates
    the value through Pydantic's validation system.

    :param annotation: Type annotation to validate against.
    :param value: Value to validate.
    :returns: Validated value (converted to annotation type).
    :raises ValidationError: If value doesn't match annotation.
    """
    type_adapter = TypeAdapter(annotation)
    return type_adapter.validate_python(value)
