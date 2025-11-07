"""Tests for format validators."""

import pytest

from pydantic_jsonschema.validators import (
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

    @pytest.mark.parametrize("value", [123, None, [], {}])
    def test_validate_date_wrong_type(self, value: object) -> None:
        """Test date validation with wrong types."""
        with pytest.raises(ValueError, match="Expected string"):
            validate_date(value)

    def test_validate_time_success(self):
        """Test valid time formats."""
        assert validate_time("20:20:39") == "20:20:39"
        assert validate_time("20:20:39+00:00") == "20:20:39+00:00"
        assert validate_time("12:30:45.123456") == "12:30:45.123456"

    def test_validate_time_failure(self):
        """Test invalid time formats."""
        with pytest.raises(ValueError, match="Invalid time format"):
            validate_time("25:00:00")  # Invalid hour
        with pytest.raises(ValueError, match="Invalid time format"):
            validate_time("not-a-time")

    def test_validate_datetime_success(self):
        """Test valid datetime formats."""
        assert validate_datetime("2018-11-13T20:20:39+00:00") == "2018-11-13T20:20:39+00:00"
        assert validate_datetime("2018-11-13T20:20:39Z") == "2018-11-13T20:20:39Z"
        assert validate_datetime("2018-11-13T20:20:39") == "2018-11-13T20:20:39"

    def test_validate_datetime_failure(self):
        """Test invalid datetime formats."""
        with pytest.raises(ValueError, match="Invalid datetime format"):
            validate_datetime("not-a-datetime")
        with pytest.raises(ValueError, match="Invalid datetime format"):
            validate_datetime("2018-13-01T20:20:39")

    def test_validate_duration_success(self):
        """Test valid duration formats."""
        assert validate_duration("P3D") == "P3D"
        assert validate_duration("P1Y2M3D") == "P1Y2M3D"
        assert validate_duration("PT1H30M") == "PT1H30M"
        assert validate_duration("P1DT12H") == "P1DT12H"

    def test_validate_duration_failure(self):
        """Test invalid duration formats."""
        with pytest.raises(ValueError, match="Duration must have at least one component"):
            validate_duration("P")  # Empty duration
        with pytest.raises(ValueError, match="Invalid duration format"):
            validate_duration("not-a-duration")


class TestNetworkValidators:
    """Tests for network format validators."""

    def test_validate_email_success(self):
        """Test valid email formats."""
        assert validate_email("test@example.com") == "test@example.com"
        assert validate_email("user.name+tag@example.co.uk") == "user.name+tag@example.co.uk"

    def test_validate_email_failure(self):
        """Test invalid email formats."""
        with pytest.raises(ValueError, match="Invalid email format"):
            validate_email("not-an-email")
        with pytest.raises(ValueError, match="Invalid email format"):
            validate_email("@example.com")
        with pytest.raises(ValueError, match="Invalid email format"):
            validate_email("user@")

    def test_validate_hostname_success(self):
        """Test valid hostname formats."""
        assert validate_hostname("example.com") == "example.com"
        assert validate_hostname("sub.example.com") == "sub.example.com"
        assert validate_hostname("localhost") == "localhost"

    def test_validate_hostname_failure(self):
        """Test invalid hostname formats."""
        with pytest.raises(ValueError, match="Invalid hostname format"):
            validate_hostname("-invalid.com")  # Starts with hyphen
        with pytest.raises(ValueError, match="Invalid hostname format"):
            validate_hostname("invalid-.com")  # Ends with hyphen

    def test_validate_ipv4_success(self):
        """Test valid IPv4 formats."""
        assert validate_ipv4("192.168.1.1") == "192.168.1.1"
        assert validate_ipv4("127.0.0.1") == "127.0.0.1"
        assert validate_ipv4("0.0.0.0") == "0.0.0.0"

    def test_validate_ipv4_failure(self):
        """Test invalid IPv4 formats."""
        with pytest.raises(ValueError, match="Invalid IPv4 address"):
            validate_ipv4("999.999.999.999")
        with pytest.raises(ValueError, match="Invalid IPv4 address"):
            validate_ipv4("not-an-ip")

    def test_validate_ipv6_success(self):
        """Test valid IPv6 formats."""
        assert (
            validate_ipv6("2001:0db8:85a3:0000:0000:8a2e:0370:7334")
            == "2001:0db8:85a3:0000:0000:8a2e:0370:7334"
        )
        assert validate_ipv6("::1") == "::1"
        assert validate_ipv6("fe80::1") == "fe80::1"

    def test_validate_ipv6_failure(self):
        """Test invalid IPv6 formats."""
        with pytest.raises(ValueError, match="Invalid IPv6 address"):
            validate_ipv6("not-an-ip")


class TestURIValidators:
    """Tests for URI/IRI format validators."""

    def test_validate_uuid_success(self):
        """Test valid UUID formats."""
        assert (
            validate_uuid("3e4666bf-d5e5-4aa7-b8ce-cefe41c7568a")
            == "3e4666bf-d5e5-4aa7-b8ce-cefe41c7568a"
        )
        assert (
            validate_uuid("00000000-0000-0000-0000-000000000000")
            == "00000000-0000-0000-0000-000000000000"
        )

    def test_validate_uuid_failure(self):
        """Test invalid UUID formats."""
        with pytest.raises(ValueError, match="Invalid UUID format"):
            validate_uuid("not-a-uuid")
        with pytest.raises(ValueError, match="Invalid UUID format"):
            validate_uuid("3e4666bf-d5e5-4aa7-b8ce")  # Too short

    def test_validate_uri_success(self):
        """Test valid URI formats."""
        assert (
            validate_uri("https://www.example.com/resource") == "https://www.example.com/resource"
        )
        assert validate_uri("http://example.com") == "http://example.com"
        assert validate_uri("ftp://files.example.com") == "ftp://files.example.com"

    def test_validate_uri_failure(self):
        """Test invalid URI formats."""
        with pytest.raises(ValueError, match="Invalid URI format"):
            validate_uri("www.example.com")  # Missing scheme
        with pytest.raises(ValueError, match="Invalid URI format"):
            validate_uri("/relative/path")  # Relative path

    def test_validate_uri_reference_success(self):
        """Test valid URI reference formats."""
        assert validate_uri_reference("/relative/path/to/resource") == "/relative/path/to/resource"
        assert validate_uri_reference("https://example.com") == "https://example.com"
        assert validate_uri_reference("#fragment") == "#fragment"

    def test_validate_iri_success(self):
        """Test valid IRI formats."""
        result = validate_iri("https://www.example.com/こんにちは")
        assert result == "https://www.example.com/こんにちは"

    def test_validate_iri_failure(self):
        """Test invalid IRI formats."""
        with pytest.raises(ValueError, match="Invalid IRI format"):
            validate_iri("www.example.com")  # Missing scheme

    def test_validate_iri_reference_success(self):
        """Test valid IRI reference formats."""
        result = validate_iri_reference("/relative/path/to/こんにちは")
        assert result == "/relative/path/to/こんにちは"
