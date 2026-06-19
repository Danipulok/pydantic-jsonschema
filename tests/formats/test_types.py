"""Tests for format type aliases exported from `pydantic_jsonschema.formats`."""

import datetime as dt

import pytest
from pydantic import BaseModel, JsonValue, ValidationError

from pydantic_jsonschema.formats import (
    UUID,
    Date,
    DateTime,
    Duration,
    Email,
    Hostname,
    IdnEmail,
    IdnHostname,
    IPv4,
    IPv6,
    Iri,
    IriReference,
    JsonPointer,
    Regex,
    RelativeJsonPointer,
    Time,
    Uri,
    UriReference,
    UriTemplate,
)


class TestDateTime:
    """Test `DateTime` format type."""

    @pytest.mark.parametrize(
        "value",
        [
            "2024-01-15T10:30:00Z",
            "2000-01-01T00:00:00+03:00",
        ],
    )
    def test_valid(self, value: str) -> None:
        """Valid ISO 8601 datetime string is parsed."""

        class Model(BaseModel):
            value: DateTime

        assert isinstance(Model(value=value).value, dt.datetime)

    @pytest.mark.parametrize(
        "value",
        [
            "not-a-datetime",
            "2024-13-01T00:00:00Z",
        ],
    )
    def test_invalid(self, value: str) -> None:
        """Non-datetime string is rejected."""

        class Model(BaseModel):
            value: DateTime

        with pytest.raises(ValidationError):
            Model(value=value)


class TestTime:
    """Test `Time` format type."""

    @pytest.mark.parametrize(
        "value",
        [
            "10:30:00",
            "00:00:00",
            "23:59:59.999999",
        ],
    )
    def test_valid(self, value: str) -> None:
        """Valid time string is parsed."""

        class Model(BaseModel):
            value: Time

        assert isinstance(Model(value=value).value, dt.time)

    @pytest.mark.parametrize(
        "value",
        [
            "not-a-time",
            "25:00:00",
        ],
    )
    def test_invalid(self, value: str) -> None:
        """Non-time string is rejected."""

        class Model(BaseModel):
            value: Time

        with pytest.raises(ValidationError):
            Model(value=value)


class TestDate:
    """Test `Date` format type."""

    @pytest.mark.parametrize(
        "value",
        [
            "2024-01-15",
            "2000-12-31",
        ],
    )
    def test_valid(self, value: str) -> None:
        """Valid ISO 8601 date string is parsed."""

        class Model(BaseModel):
            value: Date

        assert isinstance(Model(value=value).value, dt.date)

    @pytest.mark.parametrize(
        "value",
        [
            "not-a-date",
            "2024-13-01",
        ],
    )
    def test_invalid(self, value: str) -> None:
        """Non-date string is rejected."""

        class Model(BaseModel):
            value: Date

        with pytest.raises(ValidationError):
            Model(value=value)


class TestDuration:
    """Test `Duration` format type."""

    @pytest.mark.parametrize(
        "value",
        [
            "PT1H30M",
            "P1D",
            "PT0S",
        ],
    )
    def test_valid(self, value: str) -> None:
        """Valid ISO 8601 duration string is parsed."""

        class Model(BaseModel):
            value: Duration

        assert isinstance(Model(value=value).value, dt.timedelta)

    @pytest.mark.parametrize(
        "value",
        [
            "not-a-duration",
            "abc",
        ],
    )
    def test_invalid(self, value: str) -> None:
        """Non-duration string is rejected."""

        class Model(BaseModel):
            value: Duration

        with pytest.raises(ValidationError):
            Model(value=value)


class TestUuid:
    """Test `UUID` format type."""

    @pytest.mark.parametrize(
        "value",
        [
            "550e8400-e29b-41d4-a716-446655440000",
            "00000000-0000-0000-0000-000000000000",
        ],
    )
    def test_valid(self, value: str) -> None:
        """Valid UUID string is parsed."""

        class Model(BaseModel):
            value: UUID

        assert str(Model(value=value).value) == value

    @pytest.mark.parametrize(
        "value",
        [
            "not-a-uuid",
            "550e8400",
        ],
    )
    def test_invalid(self, value: str) -> None:
        """Non-UUID string is rejected."""

        class Model(BaseModel):
            value: UUID

        with pytest.raises(ValidationError):
            Model(value=value)


class TestEmail:
    """Test `Email` format type."""

    @pytest.mark.parametrize(
        "value",
        [
            "alice@example.com",
            "user+tag@domain.org",
        ],
    )
    def test_valid(self, value: str) -> None:
        """Valid email address is accepted."""

        class Model(BaseModel):
            value: Email

        assert Model(value=value).value == value

    @pytest.mark.parametrize(
        "value",
        [
            "not-an-email",
            "@missing-local",
        ],
    )
    def test_invalid(self, value: str) -> None:
        """Non-email string is rejected."""

        class Model(BaseModel):
            value: Email

        with pytest.raises(ValidationError):
            Model(value=value)

    @pytest.mark.parametrize(
        "value",
        [
            123,
            None,
            [],
            {},
        ],
    )
    def test_non_string_rejected(self, value: JsonValue) -> None:
        """Non-string input is rejected by the base `str` type."""

        class Model(BaseModel):
            value: Email

        with pytest.raises(ValidationError):
            Model(value=value)


class TestHostname:
    """Test `Hostname` format type."""

    @pytest.mark.parametrize(
        "value",
        [
            "example.com",
            "localhost",
            "sub.example.com",
        ],
    )
    def test_valid(self, value: str) -> None:
        """Valid hostname is accepted."""

        class Model(BaseModel):
            value: Hostname

        assert Model(value=value).value == value

    @pytest.mark.parametrize(
        "value",
        [
            "-invalid.com",
            "a_b.com",
        ],
    )
    def test_invalid(self, value: str) -> None:
        """Invalid hostname is rejected."""

        class Model(BaseModel):
            value: Hostname

        with pytest.raises(ValidationError):
            Model(value=value)

    @pytest.mark.parametrize(
        "value",
        [
            123,
            None,
            [],
            {},
        ],
    )
    def test_non_string_rejected(self, value: JsonValue) -> None:
        """Non-string input is rejected by the base `str` type."""

        class Model(BaseModel):
            value: Hostname

        with pytest.raises(ValidationError):
            Model(value=value)


class TestIPv4:
    """Test `IPv4` format type."""

    @pytest.mark.parametrize(
        "value",
        [
            "192.168.1.1",
            "10.0.0.1",
            "255.255.255.255",
        ],
    )
    def test_valid(self, value: str) -> None:
        """Valid IPv4 address is parsed."""

        class Model(BaseModel):
            value: IPv4

        assert str(Model(value=value).value) == value

    @pytest.mark.parametrize(
        "value",
        [
            "not-an-ip",
            "999.999.999.999",
        ],
    )
    def test_invalid(self, value: str) -> None:
        """Non-IPv4 string is rejected."""

        class Model(BaseModel):
            value: IPv4

        with pytest.raises(ValidationError):
            Model(value=value)


class TestIPv6:
    """Test `IPv6` format type."""

    @pytest.mark.parametrize(
        "value",
        [
            "::1",
            "fe80::1",
            "2001:db8::1",
        ],
    )
    def test_valid(self, value: str) -> None:
        """Valid IPv6 address is parsed."""

        class Model(BaseModel):
            value: IPv6

        assert str(Model(value=value).value) == value

    @pytest.mark.parametrize(
        "value",
        [
            "not-an-ipv6",
            ":::invalid",
        ],
    )
    def test_invalid(self, value: str) -> None:
        """Non-IPv6 string is rejected."""

        class Model(BaseModel):
            value: IPv6

        with pytest.raises(ValidationError):
            Model(value=value)


class TestUri:
    """Test `Uri` format type."""

    @pytest.mark.parametrize(
        "value",
        [
            "https://example.com/path",
            "ftp://host",
            "urn:isbn:123",
        ],
    )
    def test_valid(self, value: str) -> None:
        """Valid URI with scheme is accepted."""

        class Model(BaseModel):
            value: Uri

        assert Model(value=value).value == value

    @pytest.mark.parametrize(
        "value",
        [
            "/relative/path",
            "www.example.com",
        ],
    )
    def test_invalid(self, value: str) -> None:
        """URI without scheme is rejected."""

        class Model(BaseModel):
            value: Uri

        with pytest.raises(ValidationError):
            Model(value=value)

    @pytest.mark.parametrize(
        "value",
        [
            123,
            None,
            [],
            {},
        ],
    )
    def test_non_string_rejected(self, value: JsonValue) -> None:
        """Non-string input is rejected by the base `str` type."""

        class Model(BaseModel):
            value: Uri

        with pytest.raises(ValidationError):
            Model(value=value)


class TestUriReference:
    """Test `UriReference` format type."""

    @pytest.mark.parametrize(
        "value",
        [
            "/relative/path",
            "https://example.com",
            "../up",
        ],
    )
    def test_valid(self, value: str) -> None:
        """Relative URI reference is accepted."""

        class Model(BaseModel):
            value: UriReference

        assert Model(value=value).value == value

    @pytest.mark.parametrize(
        "value",
        [
            "http://[invalid",
            "http://host:abc",
        ],
    )
    def test_invalid(self, value: str) -> None:
        """URI reference with invalid authority is rejected."""

        class Model(BaseModel):
            value: UriReference

        with pytest.raises(ValidationError):
            Model(value=value)

    @pytest.mark.parametrize(
        "value",
        [
            123,
            None,
            [],
            {},
        ],
    )
    def test_non_string_rejected(self, value: JsonValue) -> None:
        """Non-string input is rejected by the base `str` type."""

        class Model(BaseModel):
            value: UriReference

        with pytest.raises(ValidationError):
            Model(value=value)


class TestIri:
    """Test `Iri` format type."""

    @pytest.mark.parametrize(
        "value",
        [
            "https://example.com/données",
            "http://example.com/こんにちは",
        ],
    )
    def test_valid(self, value: str) -> None:
        """Valid IRI with non-ASCII path is accepted."""

        class Model(BaseModel):
            value: Iri

        assert Model(value=value).value == value

    @pytest.mark.parametrize(
        "value",
        [
            "/relative/path",
            "http://[invalid",
        ],
    )
    def test_invalid(self, value: str) -> None:
        """IRI without scheme or with invalid authority is rejected."""

        class Model(BaseModel):
            value: Iri

        with pytest.raises(ValidationError):
            Model(value=value)

    @pytest.mark.parametrize(
        "value",
        [
            123,
            None,
            [],
            {},
        ],
    )
    def test_non_string_rejected(self, value: JsonValue) -> None:
        """Non-string input is rejected by the base `str` type."""

        class Model(BaseModel):
            value: Iri

        with pytest.raises(ValidationError):
            Model(value=value)


class TestIriReference:
    """Test `IriReference` format type."""

    @pytest.mark.parametrize(
        "value",
        [
            "/relative/こんにちは",
            "https://example.com/données",
        ],
    )
    def test_valid(self, value: str) -> None:
        """Relative IRI reference with non-ASCII is accepted."""

        class Model(BaseModel):
            value: IriReference

        assert Model(value=value).value == value

    @pytest.mark.parametrize(
        "value",
        [
            "http://[invalid",
            "http://host:abc",
        ],
    )
    def test_invalid(self, value: str) -> None:
        """IRI reference with invalid authority is rejected."""

        class Model(BaseModel):
            value: IriReference

        with pytest.raises(ValidationError):
            Model(value=value)

    @pytest.mark.parametrize(
        "value",
        [
            123,
            None,
            [],
            {},
        ],
    )
    def test_non_string_rejected(self, value: JsonValue) -> None:
        """Non-string input is rejected by the base `str` type."""

        class Model(BaseModel):
            value: IriReference

        with pytest.raises(ValidationError):
            Model(value=value)


class TestIdnHostname:
    """Test `IdnHostname` format type."""

    @pytest.mark.parametrize(
        "value",
        [
            "münchen.de",
            "example.com",
        ],
    )
    def test_valid(self, value: str) -> None:
        """Valid internationalized hostname is accepted."""

        class Model(BaseModel):
            value: IdnHostname

        assert Model(value=value).value == value

    @pytest.mark.parametrize(
        "value",
        [
            "a..b.com",
            "a_b.com",
        ],
    )
    def test_invalid(self, value: str) -> None:
        """Invalid internationalized hostname is rejected."""

        class Model(BaseModel):
            value: IdnHostname

        with pytest.raises(ValidationError):
            Model(value=value)


class TestIdnEmail:
    """Test `IdnEmail` format type."""

    @pytest.mark.parametrize(
        "value",
        [
            "user@münchen.de",
            "alice@example.com",
        ],
    )
    def test_valid(self, value: str) -> None:
        """Valid internationalized email is accepted."""

        class Model(BaseModel):
            value: IdnEmail

        assert Model(value=value).value == value

    @pytest.mark.parametrize(
        "value",
        [
            "no-at-sign",
            "user@a..b.com",
        ],
    )
    def test_invalid(self, value: str) -> None:
        """Invalid internationalized email is rejected."""

        class Model(BaseModel):
            value: IdnEmail

        with pytest.raises(ValidationError):
            Model(value=value)


class TestJsonPointer:
    """Test `JsonPointer` format type."""

    @pytest.mark.parametrize(
        "value",
        [
            "",
            "/foo/0",
        ],
    )
    def test_valid(self, value: str) -> None:
        """Valid JSON Pointer is accepted."""

        class Model(BaseModel):
            value: JsonPointer

        assert Model(value=value).value == value

    @pytest.mark.parametrize(
        "value",
        [
            "foo",
            "/~2",
        ],
    )
    def test_invalid(self, value: str) -> None:
        """Invalid JSON Pointer is rejected."""

        class Model(BaseModel):
            value: JsonPointer

        with pytest.raises(ValidationError):
            Model(value=value)


class TestRelativeJsonPointer:
    """Test `RelativeJsonPointer` format type."""

    @pytest.mark.parametrize(
        "value",
        [
            "0",
            "1/foo",
            "0#",
        ],
    )
    def test_valid(self, value: str) -> None:
        """Valid Relative JSON Pointer is accepted."""

        class Model(BaseModel):
            value: RelativeJsonPointer

        assert Model(value=value).value == value

    @pytest.mark.parametrize(
        "value",
        [
            "01",
            "#",
        ],
    )
    def test_invalid(self, value: str) -> None:
        """Invalid Relative JSON Pointer is rejected."""

        class Model(BaseModel):
            value: RelativeJsonPointer

        with pytest.raises(ValidationError):
            Model(value=value)


class TestUriTemplate:
    """Test `UriTemplate` format type."""

    @pytest.mark.parametrize(
        "value",
        [
            r"http://example.com/~{username}/",
            r"{?q,lang}",
        ],
    )
    def test_valid(self, value: str) -> None:
        """Valid URI Template is accepted."""

        class Model(BaseModel):
            value: UriTemplate

        assert Model(value=value).value == value

    @pytest.mark.parametrize(
        "value",
        [
            r"{var",
            r"{}",
        ],
    )
    def test_invalid(self, value: str) -> None:
        """Invalid URI Template is rejected."""

        class Model(BaseModel):
            value: UriTemplate

        with pytest.raises(ValidationError):
            Model(value=value)


class TestRegex:
    """Test `Regex` format type."""

    @pytest.mark.parametrize(
        "value",
        [
            "^[a-z]+$",
            "(a|b)*",
        ],
    )
    def test_valid(self, value: str) -> None:
        """Valid regular expression is accepted."""

        class Model(BaseModel):
            value: Regex

        assert Model(value=value).value == value

    @pytest.mark.parametrize(
        "value",
        [
            "[a-z",
            "*invalid",
        ],
    )
    def test_invalid(self, value: str) -> None:
        """Invalid regular expression is rejected."""

        class Model(BaseModel):
            value: Regex

        with pytest.raises(ValidationError):
            Model(value=value)
