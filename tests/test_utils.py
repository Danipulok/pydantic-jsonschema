"""Tests for utility functions."""

import pytest

from pydantic_jsonschema._utils import sanitize_identifier

__all__: list[str] = []


class TestSanitizeIdentifier:
    """Tests for sanitize_identifier function."""

    @pytest.mark.parametrize(
        ("input_value", "expected"),
        [
            # Valid identifiers preserved
            pytest.param("valid_name", "valid_name", id="valid-snake-case"),
            pytest.param("ValidName", "ValidName", id="valid-pascal-case"),
            pytest.param("_private", "_private", id="valid-underscore-prefix"),
            # Starts with invalid char
            pytest.param("123name", "name", id="leading-digits"),
            pytest.param("$name", "name", id="leading-dollar"),
            pytest.param("-name", "name", id="leading-hyphen"),
            # Contains invalid chars
            pytest.param("my-name", "myname", id="inner-hyphen"),
            pytest.param("my.name", "myname", id="inner-dot"),
            pytest.param("my name", "myname", id="inner-space"),
            pytest.param("my$name", "myname", id="inner-dollar"),
            # All invalid chars
            pytest.param("$$$", "", id="only-dollars"),
            pytest.param("123", "", id="only-digits"),
            pytest.param("...", "", id="only-dots"),
            # Mixed valid and invalid
            pytest.param("user-name_123", "username_123", id="mixed-hyphen"),
            pytest.param("_test.value-2", "_testvalue2", id="mixed-dot-hyphen"),
        ],
    )
    def test_sanitize_identifier(self, input_value: str, expected: str) -> None:
        """Test sanitize_identifier with various inputs."""
        assert sanitize_identifier(input_value) == expected
