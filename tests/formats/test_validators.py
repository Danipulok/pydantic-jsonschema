from collections.abc import Callable

import pytest

from pydantic_jsonschema.formats._validators import (
    validate_hostname,
    validate_iri,
    validate_iri_reference,
    validate_uri,
    validate_uri_reference,
)
from pydantic_jsonschema.types import JsonType


class TestHostnameValidator:
    """Tests for hostname format validator."""

    @pytest.mark.parametrize(
        "value",
        [
            "example.com",
            "sub.example.com",
            "localhost",
        ],
    )
    def test_validate_hostname_success(self, value: str) -> None:
        """Test valid hostname formats."""
        assert validate_hostname(value) == value

    @pytest.mark.parametrize(
        ("value", "error_match"),
        [
            ("-invalid.com", "Invalid hostname format"),  # Starts with hyphen
            ("invalid-.com", "Invalid hostname format"),  # Ends with hyphen
        ],
    )
    def test_validate_hostname_failure(self, value: str, error_match: str) -> None:
        """Test invalid hostname formats."""
        with pytest.raises(ValueError, match=error_match):
            validate_hostname(value)


class TestURIValidators:
    """Tests for URI/IRI format validators."""

    @pytest.mark.parametrize(
        "value",
        [
            "https://www.example.com/resource",
            "http://example.com",
            "ftp://files.example.com",
        ],
    )
    def test_validate_uri_success(self, value: str) -> None:
        """Test valid URI formats."""
        assert validate_uri(value) == value

    @pytest.mark.parametrize(
        ("value", "error_match"),
        [
            ("www.example.com", r"scheme was required but missing"),  # Missing scheme
            ("/relative/path", r"scheme was required but missing"),  # Relative path
        ],
    )
    def test_validate_uri_failure(self, value: str, error_match: str) -> None:
        """Test invalid URI formats."""
        with pytest.raises(ValueError, match=error_match):
            validate_uri(value)

    @pytest.mark.parametrize(
        "value",
        [
            "/relative/path/to/resource",
            "../relative/path",
            "//example.com/path",
            "https://www.example.com/resource",  # Absolute URI is valid URI reference
        ],
    )
    def test_validate_uri_reference_success(self, value: str) -> None:
        """Test valid URI reference formats."""
        assert validate_uri_reference(value) == value

    def test_validate_iri_success(self) -> None:
        """Test valid IRI formats."""
        result = validate_iri("https://www.example.com/こんにちは")
        assert result == "https://www.example.com/こんにちは"

    @pytest.mark.parametrize(
        ("value", "error_match"),
        [
            ("www.example.com", r"scheme was required but missing"),  # Missing scheme
        ],
    )
    def test_validate_iri_failure(self, value: str, error_match: str) -> None:
        """Test invalid IRI formats."""
        with pytest.raises(ValueError, match=error_match):
            validate_iri(value)

    @pytest.mark.parametrize(
        "value",
        [
            "/relative/path/to/こんにちは",
            "../relative/こんにちは",
            "//example.com/こんにちは",
            "https://www.example.com/こんにちは",  # Absolute IRI is valid IRI reference
        ],
    )
    def test_validate_iri_reference_success(self, value: str) -> None:
        """Test valid IRI reference formats."""
        assert validate_iri_reference(value) == value


# Unified wrong type tests for all validators
@pytest.mark.parametrize(
    "validator",
    [
        validate_hostname,
        validate_uri,
        validate_uri_reference,
        validate_iri,
        validate_iri_reference,
    ],
)
@pytest.mark.parametrize("invalid_value", [123, None, [], {}])
def test_all_validators_reject_wrong_types(
    validator: Callable[[JsonType], str],
    invalid_value: JsonType,
) -> None:
    """Test that all validators reject non-string types."""
    with pytest.raises(ValueError, match="Expected string"):
        validator(invalid_value)
