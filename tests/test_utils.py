"""Tests for utility functions."""

from pydantic_jsonschema._utils import sanitize_identifier


class TestSanitizeIdentifier:
    """Tests for sanitize_identifier function."""

    def test_valid_identifier(self) -> None:
        """Test that valid identifiers are preserved."""
        assert sanitize_identifier("valid_name") == "valid_name"
        assert sanitize_identifier("ValidName") == "ValidName"
        assert sanitize_identifier("_private") == "_private"

    def test_starts_with_invalid_char(self) -> None:
        """Test sanitization when first char is invalid."""
        assert sanitize_identifier("123name") == "name"
        assert sanitize_identifier("$name") == "name"
        assert sanitize_identifier("-name") == "name"

    def test_contains_invalid_chars(self) -> None:
        """Test sanitization of invalid characters."""
        assert sanitize_identifier("my-name") == "myname"
        assert sanitize_identifier("my.name") == "myname"
        assert sanitize_identifier("my name") == "myname"
        assert sanitize_identifier("my$name") == "myname"

    def test_all_invalid_chars(self) -> None:
        """Test when all characters are invalid."""
        assert sanitize_identifier("$$$") == ""
        assert sanitize_identifier("123") == ""
        assert sanitize_identifier("...") == ""

    def test_mixed_valid_invalid(self) -> None:
        """Test mixed valid and invalid characters."""
        assert sanitize_identifier("user-name_123") == "username_123"
        assert sanitize_identifier("_test.value-2") == "_testvalue2"
