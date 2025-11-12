from collections.abc import Callable
from typing import Any

import pytest

from pydantic_jsonschema.formats._validators import (
    validate_date,
    validate_datetime,
    validate_duration,
    validate_email,
    validate_hostname,
    validate_ipv4,
    validate_ipv6,
    validate_iri,
    validate_iri_reference,
    validate_time,
    validate_uri,
    validate_uri_reference,
    validate_uuid,
)
from pydantic_jsonschema.types import JsonType


class TestDateTimeValidators:
    """Tests for date/time format validators."""

    @pytest.mark.parametrize(
        "value",
        [
            "2018-11-13",
            "2000-01-01",
            "2024-12-31",
            "1999-12-31",
            "2025-01-01",
        ],
    )
    def test_validate_date_success(self, value: str) -> None:
        """Test valid date formats."""
        assert validate_date(value) == value

    @pytest.mark.parametrize(
        ("value", "error_match"),
        [
            ("2018-13-01", "Invalid date format"),  # Invalid month
            ("not-a-date", "Invalid date format"),
            ("2024-02-30", "Invalid date format"),  # Invalid day
            ("99-12-31", "Invalid date format"),  # Wrong year format
        ],
    )
    def test_validate_date_invalid_format(self, value: str, error_match: str) -> None:
        """Test invalid date formats."""
        with pytest.raises(ValueError, match=error_match):
            validate_date(value)

    @pytest.mark.parametrize(
        "value",
        [
            "20:20:39",
            "20:20:39+00:00",
            "12:30:45.123456",
        ],
    )
    def test_validate_time_success(self, value: str) -> None:
        """Test valid time formats."""
        assert validate_time(value) == value

    @pytest.mark.parametrize(
        ("value", "error_match"),
        [
            ("25:00:00", "Invalid time format"),  # Invalid hour
            ("not-a-time", "Invalid time format"),
        ],
    )
    def test_validate_time_failure(self, value: str, error_match: str) -> None:
        """Test invalid time formats."""
        with pytest.raises(ValueError, match=error_match):
            validate_time(value)

    @pytest.mark.parametrize(
        "value",
        [
            "2018-11-13T20:20:39+00:00",
            "2018-11-13T20:20:39Z",
            "2018-11-13T20:20:39",
        ],
    )
    def test_validate_datetime_success(self, value: str) -> None:
        """Test valid datetime formats."""
        assert validate_datetime(value) == value

    @pytest.mark.parametrize(
        ("value", "error_match"),
        [
            ("not-a-datetime", "Invalid datetime format"),
            ("2018-13-01T20:20:39", "Invalid datetime format"),
        ],
    )
    def test_validate_datetime_failure(self, value: str, error_match: str) -> None:
        """Test invalid datetime formats."""
        with pytest.raises(ValueError, match=error_match):
            validate_datetime(value)

    @pytest.mark.parametrize(
        "value",
        [
            "P3D",
            "P1Y2M3D",
            "PT1H30M",
            "P1DT12H",
        ],
    )
    def test_validate_duration_success(self, value: str) -> None:
        """Test valid duration formats."""
        assert validate_duration(value) == value

    @pytest.mark.parametrize(
        ("value", "error_match"),
        [
            ("P", "Duration must have at least one component"),  # Empty duration
            ("not-a-duration", "Invalid duration format"),
            ("PT", "Duration must have at least one component"),  # Empty time duration
        ],
    )
    def test_validate_duration_failure(self, value: str, error_match: str) -> None:
        """Test invalid duration formats."""
        with pytest.raises(ValueError, match=error_match):
            validate_duration(value)


class TestNetworkValidators:
    """Tests for network format validators."""

    @pytest.mark.parametrize(
        "value",
        [
            "test@example.com",
            "user.name+tag@example.co.uk",
        ],
    )
    def test_validate_email_success(self, value: str) -> None:
        """Test valid email formats."""
        assert validate_email(value) == value

    @pytest.mark.parametrize(
        ("value", "error_match"),
        [
            ("not-an-email", "Invalid email format"),
            ("@example.com", "Invalid email format"),
            ("user@", "Invalid email format"),
        ],
    )
    def test_validate_email_failure(self, value: str, error_match: str) -> None:
        """Test invalid email formats."""
        with pytest.raises(ValueError, match=error_match):
            validate_email(value)

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

    @pytest.mark.parametrize(
        "value",
        [
            "192.168.1.1",
            "127.0.0.1",
            "0.0.0.0",  # noqa: S104
        ],
    )
    def test_validate_ipv4_success(self, value: str) -> None:
        """Test valid IPv4 formats."""
        assert validate_ipv4(value) == value

    @pytest.mark.parametrize(
        ("value", "error_match"),
        [
            ("999.999.999.999", "Invalid IPv4 address"),
            ("not-an-ip", "Invalid IPv4 address"),
        ],
    )
    def test_validate_ipv4_failure(self, value: str, error_match: str) -> None:
        """Test invalid IPv4 formats."""
        with pytest.raises(ValueError, match=error_match):
            validate_ipv4(value)

    @pytest.mark.parametrize(
        "value",
        [
            "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
            "::1",
            "fe80::1",
        ],
    )
    def test_validate_ipv6_success(self, value: str) -> None:
        """Test valid IPv6 formats."""
        assert validate_ipv6(value) == value

    @pytest.mark.parametrize(
        ("value", "error_match"),
        [
            ("not-an-ip", "Invalid IPv6 address"),
        ],
    )
    def test_validate_ipv6_failure(self, value: str, error_match: str) -> None:
        """Test invalid IPv6 formats."""
        with pytest.raises(ValueError, match=error_match):
            validate_ipv6(value)


class TestURIValidators:
    """Tests for URI/IRI format validators."""

    @pytest.mark.parametrize(
        "value",
        [
            "3e4666bf-d5e5-4aa7-b8ce-cefe41c7568a",
            "00000000-0000-0000-0000-000000000000",
        ],
    )
    def test_validate_uuid_success(self, value: str) -> None:
        """Test valid UUID formats."""
        assert validate_uuid(value) == value

    @pytest.mark.parametrize(
        ("value", "error_match"),
        [
            ("not-a-uuid", "Invalid UUID format"),
            ("3e4666bf-d5e5-4aa7-b8ce", "Invalid UUID format"),  # Too short
        ],
    )
    def test_validate_uuid_failure(self, value: str, error_match: str) -> None:
        """Test invalid UUID formats."""
        with pytest.raises(ValueError, match=error_match):
            validate_uuid(value)

    def test_validate_uuid_non_canonical(self) -> None:
        """Test UUID with non-canonical format."""
        # Uppercase UUID should be rejected (not canonical)
        with pytest.raises(ValueError, match="Invalid UUID format"):
            validate_uuid("3E4666BF-D5E5-4AA7-B8CE-CEFE41C7568A")

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
            ("www.example.com", r"URI must have scheme"),  # Missing scheme
            ("/relative/path", r"URI must have scheme"),  # Relative path
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
            "https://example.com",
            "#fragment",
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
            ("www.example.com", r"IRI must have scheme"),  # Missing scheme
        ],
    )
    def test_validate_iri_failure(self, value: str, error_match: str) -> None:
        """Test invalid IRI formats."""
        with pytest.raises(ValueError, match=error_match):
            validate_iri(value)

    def test_validate_iri_reference_success(self) -> None:
        """Test valid IRI reference formats."""
        result = validate_iri_reference("/relative/path/to/こんにちは")
        assert result == "/relative/path/to/こんにちは"


# Unified wrong type tests for all validators
@pytest.mark.parametrize(
    "validator",
    [
        validate_date,
        validate_time,
        validate_datetime,
        validate_duration,
        validate_email,
        validate_hostname,
        validate_ipv4,
        validate_ipv6,
        validate_uuid,
        validate_uri,
        validate_uri_reference,
        validate_iri,
        validate_iri_reference,
    ],
)
@pytest.mark.parametrize("invalid_value", [123, None, [], {}])
def test_all_validators_reject_wrong_types(
    validator: Callable[[Any], str],
    invalid_value: JsonType,
) -> None:
    """Test that all validators reject non-string types."""
    with pytest.raises(ValueError, match="Expected string"):
        validator(invalid_value)
