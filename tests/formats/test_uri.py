"""Tests for URI and IRI format validators.

See: https://www.rfc-editor.org/rfc/rfc3986
See: https://www.rfc-editor.org/rfc/rfc3987

Test data derived from the `rfc3986` library (Apache-2.0):
https://github.com/python-hyper/rfc3986/blob/7fc9af07b14f98c5270908c86a4cfe6715ae78c4/tests/test_validators.py
https://github.com/python-hyper/rfc3986/blob/0dc64f8de4327709e34e4a3039df01c46fa94a87/tests/conftest.py
"""

import pytest

from pydantic_jsonschema.formats._uri import (
    validate_iri,
    validate_iri_reference,
    validate_uri,
    validate_uri_reference,
)


class TestValidUri:
    """Valid URIs per RFC 3986 (scheme required)."""

    @pytest.mark.parametrize(
        "value",
        [
            "http://www.example.com",
            "http://example.com",
            "https://example.com",
            "ftp://files.example.com",
            "http://localhost/",
            "http://http-bin.org/",
        ],
    )
    def test_basic_uris(self, value: str) -> None:
        """Standard URIs with scheme and host."""
        assert validate_uri(value) == value

    @pytest.mark.parametrize(
        "value",
        [
            "ftp://www.example.com:21",
            "http://example.com:8080/path",
            "ssh://user:pass@localhost:22",
            "https://example.com:443/path",
        ],
    )
    def test_with_port(self, value: str) -> None:
        """URIs with explicit port numbers."""
        assert validate_uri(value) == value

    @pytest.mark.parametrize(
        "value",
        [
            "http://user:pass@host:80/path",
            "ssh://ssh@github.com:22/sigmavirus24",
            "https://user@github.com/path",
        ],
    )
    def test_with_userinfo(self, value: str) -> None:
        """URIs with userinfo component."""
        assert validate_uri(value) == value

    @pytest.mark.parametrize(
        "value",
        [
            "http://www.example.com/path/to/resource",
            "http://www.example.com/path?key=value",
            "http://example.com/path?q=1#frag",
            "https://user:pass@www.example.com:443/path?key=value#fragment",
        ],
    )
    def test_with_path_query_fragment(self, value: str) -> None:
        """URIs with path, query, and fragment components."""
        assert validate_uri(value) == value

    @pytest.mark.parametrize(
        "value",
        [
            "http://[::1]/path",
            "http://[::1]:8080/path",
            "http://[21DA:00D3:0000:2F3B:02AA:00FF:FE28:9C5A]/",
            "http://[FE80::2AA:FF:FE9A:4CA2]/",
            "http://[FF02::2]/",
            "http://[FF02:30:0:0:0:0:0:5]/",
            "http://[FFFF::]/",
        ],
    )
    def test_ipv6_hosts(self, value: str) -> None:
        """URIs with IPv6 literal addresses."""
        assert validate_uri(value) == value

    @pytest.mark.parametrize(
        "value",
        [
            "http://[::1%25lo]/path",
            "http://[FF02:0:0:0:0:0:0:2%25en01]/",
            "http://[FF02:30:0:0:0:0:0:5%25en1]/",
            "http://[FF02:30:0:0:0:0:0:5%25%26]/",
            "http://[FF02:30:0:0:0:0:0:5%2525]/",
        ],
    )
    def test_ipv6_with_zone_id(self, value: str) -> None:
        """RFC 4007 — IPv6 Zone IDs."""
        assert validate_uri(value) == value

    @pytest.mark.parametrize(
        "value",
        [
            "http://127.0.0.1",
            "http://1.2.3.4",
            "http://1.2.3.4:8080",
            "ftp://127.0.0.1",
            "http://0.0.0.0",
            "http://255.255.255.255",
        ],
    )
    def test_ipv4_hosts(self, value: str) -> None:
        """URIs with IPv4 addresses."""
        assert validate_uri(value) == value

    @pytest.mark.parametrize(
        "value",
        [
            "urn:isbn:0451450523",
            "mailto:user@example.com",
            "scheme:path",
        ],
    )
    def test_scheme_and_path_only(self, value: str) -> None:
        """URIs with scheme and path but no authority."""
        assert validate_uri(value) == value

    @pytest.mark.parametrize(
        "value",
        [
            "http:///path",
            "file:///etc/passwd",
        ],
    )
    def test_empty_authority(self, value: str) -> None:
        """URIs with empty authority (triple slash)."""
        assert validate_uri(value) == value

    @pytest.mark.parametrize(
        "value",
        [
            "a://b",
            "custom-scheme://host",
            "my+scheme.2://host",
        ],
    )
    def test_various_schemes(self, value: str) -> None:
        """URIs with different valid scheme formats."""
        assert validate_uri(value) == value


class TestInvalidUri:
    """Invalid URIs per RFC 3986."""

    @pytest.mark.parametrize(
        "value",
        [
            "www.example.com",
            "/relative/path",
            "just-a-path",
            "",
            "//example.com/path",
        ],
    )
    def test_missing_scheme(self, value: str) -> None:
        """URIs without a scheme are rejected."""
        with pytest.raises(ValueError, match=r"scheme was required but missing"):
            validate_uri(value)

    @pytest.mark.parametrize(
        "value",
        [
            "1http://example.com",
            "123://example.com",
            "+scheme://host",
            ".scheme://host",
            "-scheme://host",
        ],
    )
    def test_invalid_scheme(self, value: str) -> None:
        """RFC 3986 §3.1 — scheme must start with a letter."""
        with pytest.raises(ValueError, match=r"scheme was found to be invalid"):
            validate_uri(value)

    @pytest.mark.parametrize(
        "value",
        [
            "http://[invalid",
            "http://[",
            "https://[unclosed",
        ],
    )
    def test_unclosed_ipv6_bracket(self, value: str) -> None:
        """Unclosed IPv6 bracket in authority is rejected."""
        with pytest.raises(ValueError, match=r"host was found to be invalid"):
            validate_uri(value)

    @pytest.mark.parametrize(
        "value",
        [
            "http://example.com:abc",
            "http://example.com:80a",
            "http://host:not-a-port/path",
        ],
    )
    def test_non_numeric_port(self, value: str) -> None:
        """Non-numeric port in authority is rejected."""
        with pytest.raises(ValueError, match=r"host was found to be invalid"):
            validate_uri(value)

    @pytest.mark.parametrize(
        "value",
        [
            "http://999.999.999.999",
            "http://256.256.256.256",
            "http://256.0.0.1",
            "http://0.0.0.256",
        ],
    )
    def test_invalid_ipv4(self, value: str) -> None:
        """IPv4 addresses with octets > 255 are rejected."""
        with pytest.raises(ValueError, match=r"host was found to be invalid"):
            validate_uri(value)

    def test_multiline_fragment(self) -> None:
        """Fragment containing a newline fails the Appendix B regex entirely."""
        with pytest.raises(ValueError, match=r"Invalid URI"):
            validate_uri("http://host#frag\nmore")


class TestValidUriReference:
    """Valid URI references per RFC 3986 (scheme optional)."""

    @pytest.mark.parametrize(
        "value",
        [
            "/relative/path/to/resource",
            "../relative/path",
            "./current/path",
            "just-a-path",
            "",
            "www.example.com",
        ],
    )
    def test_relative_references(self, value: str) -> None:
        """Relative references without a scheme."""
        assert validate_uri_reference(value) == value

    @pytest.mark.parametrize(
        "value",
        [
            "//example.com/path",
            "//user@example.com/path",
            "//example.com:8080/path",
        ],
    )
    def test_authority_without_scheme(self, value: str) -> None:
        """References with authority but no scheme."""
        assert validate_uri_reference(value) == value

    def test_absolute_uri_also_valid(self) -> None:
        """Absolute URIs are valid URI references."""
        assert validate_uri_reference("https://www.example.com/resource") == (
            "https://www.example.com/resource"
        )

    def test_scheme_like_prefix(self) -> None:
        """A colon without valid scheme prefix is still a valid reference."""
        assert validate_uri_reference("://missing-scheme") == "://missing-scheme"


class TestInvalidUriReference:
    """Invalid URI references per RFC 3986."""

    @pytest.mark.parametrize(
        "value",
        [
            "http://[invalid",
            "http://example.com:abc",
            "http://999.999.999.999",
            "http://256.256.256.256",
        ],
    )
    def test_invalid_authority(self, value: str) -> None:
        """References with invalid authority are rejected."""
        with pytest.raises(ValueError, match=r"host was found to be invalid"):
            validate_uri_reference(value)


class TestValidIri:
    """Valid IRIs per RFC 3987 (scheme required, non-ASCII allowed)."""

    @pytest.mark.parametrize(
        "value",
        [
            "https://www.example.com/こんにちは",
            "https://example.com/données",
            "https://example.com",
            "http://example.com/β/ό?λ#ος",
            "http://example.com/path/Ünïcödé",
            "http://example.com/путь/к/ресурсу",
        ],
    )
    def test_unicode_paths(self, value: str) -> None:
        """IRIs with non-ASCII characters in path, query, and fragment."""
        assert validate_iri(value) == value

    def test_ascii_uri_also_valid(self) -> None:
        """Every valid URI is also a valid IRI."""
        assert validate_iri("http://example.com/path?q=1#frag") == (
            "http://example.com/path?q=1#frag"
        )


class TestInvalidIri:
    """Invalid IRIs per RFC 3987."""

    def test_missing_scheme(self) -> None:
        """IRI without scheme is rejected."""
        with pytest.raises(ValueError, match=r"scheme was required but missing"):
            validate_iri("www.example.com")

    def test_invalid_scheme(self) -> None:
        """IRI with invalid scheme is rejected."""
        with pytest.raises(ValueError, match=r"scheme was found to be invalid"):
            validate_iri("1http://example.com")

    def test_unclosed_ipv6(self) -> None:
        """IRI with unclosed IPv6 bracket is rejected."""
        with pytest.raises(ValueError, match=r"host was found to be invalid"):
            validate_iri("http://[invalid")

    def test_non_numeric_port(self) -> None:
        """IRI with non-numeric port is rejected."""
        with pytest.raises(ValueError, match=r"host was found to be invalid"):
            validate_iri("http://example.com:abc")


class TestValidIriReference:
    """Valid IRI references per RFC 3987 (scheme optional, non-ASCII allowed)."""

    @pytest.mark.parametrize(
        "value",
        [
            "/relative/path/to/こんにちは",
            "../relative/こんにちは",
            "//example.com/こんにちは",
            "https://www.example.com/こんにちは",
            "/путь/к/ресурсу",
            "",
        ],
    )
    def test_unicode_references(self, value: str) -> None:
        """IRI references with non-ASCII characters."""
        assert validate_iri_reference(value) == value

    def test_ascii_uri_reference_also_valid(self) -> None:
        """ASCII URI references are also valid IRI references."""
        assert validate_iri_reference("/relative/path") == "/relative/path"


class TestInvalidIriReference:
    """Invalid IRI references per RFC 3987."""

    @pytest.mark.parametrize(
        "value",
        [
            "http://[invalid",
            "http://example.com:abc",
            "http://999.999.999.999",
        ],
    )
    def test_invalid_authority(self, value: str) -> None:
        """IRI references with invalid authority are rejected."""
        with pytest.raises(ValueError, match=r"host was found to be invalid"):
            validate_iri_reference(value)
