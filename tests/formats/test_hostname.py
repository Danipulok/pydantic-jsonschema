"""Tests for hostname format validator.

See: https://www.rfc-editor.org/rfc/rfc1123#section-2.1
See: https://www.rfc-editor.org/rfc/rfc1035#section-2.3.4

Test data derived from the `fqdn` library (MPL-2.0):
https://github.com/ypcrts/fqdn/blob/e893170fb465f928e41605946b2258646ba70d04/tests/test_fqdn.py
"""

import pytest

from pydantic_jsonschema.formats._hostname import validate_hostname


class TestValidHostnames:
    """Valid hostnames per RFC 1123."""

    @pytest.mark.parametrize(
        "value",
        [
            "localhost",
            "net",
            "who.is",
            "bbc.co.uk",
            "example.com",
            "sub.example.com",
            "deep.sub.example.com",
        ],
    )
    def test_standard_domains(self, value: str) -> None:
        """Standard domain names with various label counts."""
        assert validate_hostname(value) == value

    @pytest.mark.parametrize(
        "value",
        [
            "www.1",
            "1w.1",
            "1w.a",
            "1w1.d",
            "111.a",
            "www.1a",
            "123.456",
        ],
    )
    def test_labels_starting_with_digits(self, value: str) -> None:
        """RFC 1035 §2.3.1 — labels may start with a digit."""
        assert validate_hostname(value) == value

    @pytest.mark.parametrize(
        "value",
        [
            "www1.a",
            "ww1a.c",
            "w2w.c",
            "a111.a",
            "a1c1.a",
        ],
    )
    def test_labels_with_medial_and_terminal_digits(self, value: str) -> None:
        """RFC 1123 — digits allowed anywhere in a label."""
        assert validate_hostname(value) == value

    def test_hyphens_in_labels(self) -> None:
        """Hyphens are allowed in the middle of a label."""
        assert validate_hostname("sh4d05-7357.c00-mm") == "sh4d05-7357.c00-mm"
        assert validate_hostname("my-host.example.com") == "my-host.example.com"

    def test_trailing_dot(self) -> None:
        """Trailing dot marks an absolute FQDN."""
        assert validate_hostname("example.com.") == "example.com."
        assert validate_hostname("trainwreck.com.") == "trainwreck.com."

    def test_max_label_length_63(self) -> None:
        """RFC 1035 §2.3.4 — each label may be up to 63 octets."""
        label: str = "a" * 63
        assert validate_hostname(label) == label
        assert validate_hostname(f"{label}.com") == f"{label}.com"

    def test_two_max_labels(self) -> None:
        """Two labels at maximum length (63 each)."""
        value: str = "a" * 63 + "." + "b" * 63
        assert validate_hostname(value) == value

    def test_max_total_length_253(self) -> None:
        """RFC 1035 §2.3.4 — total name ≤ 253 octets (excluding trailing dot)."""
        value: str = "a" * 61 + "." + "b" * 63 + "." + "c" * 63 + "." + "d" * 63
        assert validate_hostname(value) == value

    def test_max_total_length_253_with_trailing_dot(self) -> None:
        """254 total chars is valid when the trailing dot makes effective length 253."""
        value: str = "a" * 61 + "." + "b" * 63 + "." + "c" * 63 + "." + "d" * 63 + "."
        assert validate_hostname(value) == value

    def test_case_insensitive(self) -> None:
        """Hostnames are case-insensitive."""
        assert validate_hostname("EXAMPLE.COM") == "EXAMPLE.COM"
        assert validate_hostname("Example.Com") == "Example.Com"


class TestInvalidHostnames:
    """Invalid hostnames per RFC 1123."""

    def test_empty_string(self) -> None:
        """Empty string is not a valid hostname."""
        with pytest.raises(ValueError, match="Invalid hostname format"):
            validate_hostname("")

    @pytest.mark.parametrize(
        "value",
        [
            "-a.com",
            "a-.com",
            "-a-.com",
            "com.-a",
            "com.a-",
        ],
    )
    def test_leading_or_trailing_hyphen(self, value: str) -> None:
        """RFC 3696 §2 — labels must not start or end with a hyphen."""
        with pytest.raises(ValueError, match="Invalid hostname format"):
            validate_hostname(value)

    def test_label_too_long_64(self) -> None:
        """RFC 1035 §2.3.4 — label > 63 octets is invalid."""
        with pytest.raises(ValueError, match="Invalid hostname format"):
            validate_hostname("a" * 64)

    def test_label_too_long_in_multi_label(self) -> None:
        """First label exceeds 63 octets in a multi-label hostname."""
        with pytest.raises(ValueError, match="Invalid hostname format"):
            validate_hostname("a" * 64 + ".com")

    def test_second_label_too_long(self) -> None:
        """Second label exceeds 63 octets."""
        with pytest.raises(ValueError, match="Invalid hostname format"):
            validate_hostname("b" * 63 + "." + "a" * 64 + ".com")

    def test_total_length_254_without_trailing_dot(self) -> None:
        """RFC 1035 §2.3.4 — total > 253 octets is invalid."""
        value: str = "a" * 62 + "." + "b" * 63 + "." + "c" * 63 + "." + "d" * 63
        with pytest.raises(ValueError, match="Invalid hostname format"):
            validate_hostname(value)

    @pytest.mark.parametrize(
        "value",
        [
            "a_b.com",
            "_.dog",
            "i_.dog",
            "o_o.dog",
        ],
    )
    def test_underscores_rejected(self, value: str) -> None:
        """Underscores are not valid in hostnames."""
        with pytest.raises(ValueError, match="Invalid hostname format"):
            validate_hostname(value)

    @pytest.mark.parametrize(
        "value",
        [
            "є.com",
            "le-tour-est-joué.com",
            "invalid.cóm",
            "ich-hätte-gern-ein-Umlaut.de",
        ],
    )
    def test_non_ascii_rejected(self, value: str) -> None:
        """RFC 3696 §2 — non-ASCII chars require punycode encoding."""
        with pytest.raises(ValueError, match="Invalid hostname format"):
            validate_hostname(value)

    @pytest.mark.parametrize(
        "value",
        [
            "\x01.com",
            "x.\x01\x02\x01",
        ],
    )
    def test_control_characters_rejected(self, value: str) -> None:
        """Control characters are not valid in hostnames."""
        with pytest.raises(ValueError, match="Invalid hostname format"):
            validate_hostname(value)
