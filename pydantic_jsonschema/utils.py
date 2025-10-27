from typing import Iterator


def sanitize_identifier(name: str) -> str:
    """
    Sanitize string to be a valid Python identifier.

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
