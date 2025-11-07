"""Tests for utility functions."""

import pytest

from pydantic_jsonschema._utils import sanitize_identifier


class TestSanitizeIdentifier:
    """Tests for sanitize_identifier function."""

    @pytest.mark.parametrize(
        ("input_value", "expected"),
        [
            # Valid identifiers preserved
            ("valid_name", "valid_name"),
            ("ValidName", "ValidName"),
            ("_private", "_private"),
            # Starts with invalid char
            ("123name", "name"),
            ("$name", "name"),
            ("-name", "name"),
            # Contains invalid chars
            ("my-name", "myname"),
            ("my.name", "myname"),
            ("my name", "myname"),
            ("my$name", "myname"),
            # All invalid chars
            ("$$$", ""),
            ("123", ""),
            ("...", ""),
            # Mixed valid and invalid
            ("user-name_123", "username_123"),
            ("_test.value-2", "_testvalue2"),
        ],
    )
    def test_sanitize_identifier(self, input_value: str, expected: str) -> None:
        """Test sanitize_identifier with various inputs."""
        assert sanitize_identifier(input_value) == expected
