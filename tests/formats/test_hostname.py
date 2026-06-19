"""Tests for hostname format validators.

See: https://www.rfc-editor.org/rfc/rfc1123#section-2.1
See: https://www.rfc-editor.org/rfc/rfc1035#section-2.3.4
See: https://www.rfc-editor.org/rfc/rfc5890#section-2.3.2.3

Test data derived from the `fqdn` library (MPL-2.0):
https://github.com/ypcrts/fqdn/blob/e893170fb465f928e41605946b2258646ba70d04/tests/test_fqdn.py

IDN test data derived from the JSON Schema Test Suite (MIT):
https://github.com/json-schema-org/JSON-Schema-Test-Suite/blob/fe8c2f0de2041943975932b6bf4bd882625b6cfb/tests/draft2020-12/optional/format/idn-hostname.json

NOTE: Suite cases that exercise IDNA 2008 contextual rules (CONTEXTO middle dot /
      keraia / geresh, ZWJ-virama checks, leading combining marks, punycode
      well-formedness) are excluded: `validate_idn_hostname` uses the stdlib
      IDNA 2003 codec, which accepts them (documented difference from the spec).
"""

import pytest

from pydantic_jsonschema.formats._hostname import validate_hostname, validate_idn_hostname

__all__: list[str] = []


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


class TestValidIdnHostnames:
    """Valid internationalized hostnames per RFC 5890."""

    @pytest.mark.parametrize(
        "value",
        [
            "münchen.de",
            "bücher.example",
            "ПРИМЕР.испытание",
            "例え.jp",
            "실례.테스트",
            "ßς་〇",
        ],
    )
    def test_unicode_hostnames(self, value: str) -> None:
        """Non-ASCII hostnames convertible to punycode are accepted."""
        assert validate_idn_hostname(value) == value

    @pytest.mark.parametrize(
        "value",
        [
            "example.com",
            "localhost",
            "sub.example.com",
            "hostname",
            "host-name",
            "h0stn4me",
            "1host",
            "hostnam3",
            "xn--ihqwcrb4cv8a8dqg056pqjye",
        ],
    )
    def test_ascii_hostnames_also_valid(self, value: str) -> None:
        """Plain ASCII hostnames (including punycode) are valid IDN hostnames."""
        assert validate_idn_hostname(value) == value

    @pytest.mark.parametrize(
        "value",
        [
            "l·l",
            "α͵β",
            "א׳ב",
            "א״ב",
            "・ぁ",
            "・ァ",
            "・丈",
            "क्‍ष",
            "क्‌ष",
        ],
    )
    def test_contextual_characters_with_valid_context(self, value: str) -> None:
        """CONTEXTO/CONTEXTJ characters in their valid context are accepted."""
        assert validate_idn_hostname(value) == value

    @pytest.mark.parametrize(
        "value",
        [
            "a.b",
            "a。b",
            "a．b",
            "a｡b",
        ],
    )
    def test_unicode_label_separators(self, value: str) -> None:
        """Ideographic/fullwidth/halfwidth full stops separate labels."""
        assert validate_idn_hostname(value) == value

    @pytest.mark.parametrize(
        "value",
        [
            "ب٠ب",
            "۰0",
        ],
    )
    def test_unmixed_digit_scripts(self, value: str) -> None:
        """Arabic-Indic digits unmixed with Extended Arabic-Indic digits."""
        assert validate_idn_hostname(value) == value


class TestInvalidIdnHostnames:
    """Invalid internationalized hostnames per RFC 5890."""

    @pytest.mark.parametrize(
        "value",
        [
            "",
            "a..b.com",
            ".",
            "。",
            "．",
            "｡",
            ".example",
            "。example",
            "．example",
            "｡example",
        ],
    )
    def test_empty_labels_rejected(self, value: str) -> None:
        """Empty hostnames, lone separators, and leading separators are rejected."""
        with pytest.raises(ValueError, match="Invalid IDN hostname format"):
            validate_idn_hostname(value)

    @pytest.mark.parametrize(
        "value",
        [
            "ü" * 64 + ".com",
            (
                "실실실실실실실실실실실실실실실실실실실실실실실실실실실실실실실실실실실실실"
                "실실실실실실실실실실실실실실실례례테스트례례례례례례례례례례례례례례례례례"
                "테스트례례례례례례례례례례례례례례례례례례례테스트례례례례례례례례례례례례"
                "테스트례례실례.테스트"
            ),
        ],
    )
    def test_label_too_long_after_encoding(self, value: str) -> None:
        """Label exceeding 63 octets after punycode conversion is rejected."""
        with pytest.raises(ValueError, match="Invalid IDN hostname format"):
            validate_idn_hostname(value)

    @pytest.mark.parametrize(
        "value",
        [
            "a_b.com",
            "-leading.com",
            "trailing-.com",
            "-hello",
            "hello-",
            "-hello-",
            "-> $1.00 <--",
        ],
    )
    def test_std3_rules_rejected(self, value: str) -> None:
        """ASCII form must satisfy regular hostname rules."""
        with pytest.raises(ValueError, match="Invalid IDN hostname format"):
            validate_idn_hostname(value)

    @pytest.mark.parametrize(
        "value",
        [
            "ـߺ",
            "A׳ב",
            "A״ב",
            "ب٠۰",
        ],
    )
    def test_nameprep_prohibited_rejected(self, value: str) -> None:
        """Characters and mixes rejected by nameprep/bidi checks."""
        with pytest.raises(ValueError, match="Invalid IDN hostname format"):
            validate_idn_hostname(value)
