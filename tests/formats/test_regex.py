"""Tests for regular expression format validator.

See: https://json-schema.org/draft/2020-12/json-schema-validation#section-7.3.8

Test data derived from the JSON Schema Test Suite (MIT):
https://github.com/json-schema-org/JSON-Schema-Test-Suite/blob/fe8c2f0de2041943975932b6bf4bd882625b6cfb/tests/draft2020-12/optional/format/regex.json
"""

import pytest

from pydantic_jsonschema.formats._regex import validate_regex


class TestValidRegex:
    """Valid regular expressions."""

    @pytest.mark.parametrize(
        "value",
        [
            "^[a-z]+$",
            "(a|b)*",
            r"\d{2,4}",
            ".*",
            "",
            "(?P<name>x)",
            r"([abc])+\s+$",
        ],
    )
    def test_valid_patterns(self, value: str) -> None:
        """Compilable patterns are accepted."""
        assert validate_regex(value) == value


class TestInvalidRegex:
    """Invalid regular expressions."""

    @pytest.mark.parametrize(
        "value",
        [
            "[a-z",
            "(unclosed",
            "*invalid",
            "(?P<dup>x)(?P<dup>y)",
            "^(abc]",
        ],
    )
    def test_invalid_patterns(self, value: str) -> None:
        """Non-compilable patterns are rejected."""
        with pytest.raises(ValueError, match="Invalid regular expression format"):
            validate_regex(value)
