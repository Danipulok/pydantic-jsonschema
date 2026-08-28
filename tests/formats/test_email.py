"""Tests for email format validators.

See: https://www.rfc-editor.org/rfc/rfc5321#section-4.1.2
See: https://www.rfc-editor.org/rfc/rfc5322#section-3.4.1
See: https://www.rfc-editor.org/rfc/rfc6531#section-3.3

Test data derived from the `email-validator` library (Unlicense):
https://github.com/JoshData/python-email-validator/blob/7394682aa73a2fb3eff9a53061d6db8340b9e964/tests/test_syntax.py

IDN test data derived from the JSON Schema Test Suite (MIT):
https://github.com/json-schema-org/JSON-Schema-Test-Suite/blob/fe8c2f0de2041943975932b6bf4bd882625b6cfb/tests/draft2020-12/optional/format/idn-email.json
"""

import pytest

from pydantic_jsonschema.formats._email import validate_email, validate_idn_email

__all__: list[str] = []


class TestValidEmails:
    """Valid email addresses per RFC 5321."""

    @pytest.mark.parametrize(
        "value",
        [
            "alice@example.com",
            "user@domain.org",
            "a@b.com",
        ],
    )
    def test_basic_addresses(self, value: str) -> None:
        """Standard email addresses with alphanumeric local parts."""
        assert validate_email(value) == value

    @pytest.mark.parametrize(
        "value",
        [
            "user.name@example.com",
            "first.last@example.com",
            "a.b.c@example.com",
        ],
    )
    def test_dots_in_local(self, value: str) -> None:
        """Dots are allowed between atoms in the local part."""
        assert validate_email(value) == value

    @pytest.mark.parametrize(
        "value",
        [
            "user+tag@example.com",
            "user+foo+bar@example.com",
        ],
    )
    def test_plus_addressing(self, value: str) -> None:
        """Plus sign is a valid atext character."""
        assert validate_email(value) == value

    @pytest.mark.parametrize(
        "value",
        [
            "user-name@example.com",
            "user_name@example.com",
            "user!name@example.com",
            "user#name@example.com",
            "user$name@example.com",
            "user%name@example.com",
            "user&name@example.com",
            "user'name@example.com",
            "user*name@example.com",
            "user/name@example.com",
            "user=name@example.com",
            "user?name@example.com",
            "user^name@example.com",
            "user`name@example.com",
            "user{name@example.com",
            "user|name@example.com",
            "user}name@example.com",
            "user~name@example.com",
        ],
    )
    def test_special_atext_characters(self, value: str) -> None:
        """All atext special characters are accepted in the local part."""
        assert validate_email(value) == value

    @pytest.mark.parametrize(
        "value",
        [
            "123@example.com",
            "0@example.com",
        ],
    )
    def test_numeric_local(self, value: str) -> None:
        """All-numeric local parts are valid."""
        assert validate_email(value) == value

    @pytest.mark.parametrize(
        "value",
        [
            "user@sub.example.com",
            "user@deep.sub.example.com",
        ],
    )
    def test_subdomain(self, value: str) -> None:
        """Domain part with subdomains."""
        assert validate_email(value) == value

    def test_max_local_length_64(self) -> None:
        """RFC 5321 §4.5.3.1 — local part may be up to 64 characters."""
        local: str = "a" * 64
        value: str = f"{local}@example.com"
        assert validate_email(value) == value

    def test_single_char_local(self) -> None:
        """Single character local part is valid."""
        assert validate_email("a@example.com") == "a@example.com"

    def test_case_preserved(self) -> None:
        """Email case is preserved as-is (no normalization)."""
        assert validate_email("Alice@Example.COM") == "Alice@Example.COM"


class TestInvalidEmails:
    """Invalid email addresses per RFC 5321."""

    def test_empty_string(self) -> None:
        """Empty string is not a valid email."""
        with pytest.raises(ValueError, match="Invalid email format"):
            validate_email("")

    def test_no_at_sign(self) -> None:
        """Missing `@` is rejected."""
        with pytest.raises(ValueError, match="Invalid email format"):
            validate_email("not-an-email")

    def test_multiple_at_signs(self) -> None:
        """Multiple `@` signs in unquoted local part is rejected."""
        with pytest.raises(ValueError, match="Invalid email format"):
            validate_email("user@@example.com")

    def test_missing_local(self) -> None:
        """Empty local part is rejected."""
        with pytest.raises(ValueError, match="Invalid email format"):
            validate_email("@example.com")

    def test_missing_domain(self) -> None:
        """Empty domain part is rejected."""
        with pytest.raises(ValueError, match="Invalid email format"):
            validate_email("user@")

    @pytest.mark.parametrize(
        "value",
        [
            ".user@example.com",
            "user.@example.com",
            "user..name@example.com",
        ],
    )
    def test_invalid_dots_in_local(self, value: str) -> None:
        """Leading dot, trailing dot, or consecutive dots in local part are rejected."""
        with pytest.raises(ValueError, match="Invalid email format"):
            validate_email(value)

    def test_local_too_long(self) -> None:
        """RFC 5321 §4.5.3.1 — local part > 64 characters is rejected."""
        local: str = "a" * 65
        with pytest.raises(ValueError, match="Invalid email format"):
            validate_email(f"{local}@example.com")

    def test_total_too_long(self) -> None:
        """RFC 5321 §4.5.3.1 — total address > 254 characters is rejected."""
        local: str = "a" * 64
        domain: str = "b" * 63 + "." + "c" * 63 + "." + "d" * 63
        with pytest.raises(ValueError, match="Invalid email format"):
            validate_email(f"{local}@{domain}")

    @pytest.mark.parametrize(
        "value",
        [
            "user@-invalid.com",
            "user@invalid-.com",
        ],
    )
    def test_invalid_domain(self, value: str) -> None:
        """Domain part must be a valid hostname."""
        with pytest.raises(ValueError, match="Invalid email format"):
            validate_email(value)

    @pytest.mark.parametrize(
        "value",
        [
            'user"name@example.com',
            "user name@example.com",
            "user(name@example.com",
            "user)name@example.com",
            "user,name@example.com",
            "user:name@example.com",
            "user;name@example.com",
            "user<name@example.com",
            "user>name@example.com",
            "user[name@example.com",
            "user\\name@example.com",
            "user]name@example.com",
        ],
    )
    def test_forbidden_characters_in_local(self, value: str) -> None:
        """Characters outside atext set are rejected in unquoted local part."""
        with pytest.raises(ValueError, match="Invalid email format"):
            validate_email(value)


class TestValidIdnEmails:
    """Valid internationalized email addresses per RFC 6531."""

    @pytest.mark.parametrize(
        "value",
        [
            "user@münchen.de",
            "δοκιμή@example.com",
            "用户@例え.jp",
            "пользователь@пример.испытание",
            "실례@실례.테스트",
        ],
    )
    def test_unicode_addresses(self, value: str) -> None:
        """Non-ASCII local parts and domains are accepted."""
        assert validate_idn_email(value) == value

    @pytest.mark.parametrize(
        "value",
        [
            "alice@example.com",
            "user+tag@domain.org",
            "joe.bloggs@example.com",
        ],
    )
    def test_ascii_addresses_also_valid(self, value: str) -> None:
        """Plain ASCII addresses are valid IDN emails."""
        assert validate_idn_email(value) == value


class TestInvalidIdnEmails:
    """Invalid internationalized email addresses per RFC 6531."""

    @pytest.mark.parametrize(
        "value",
        [
            "no-at-sign",
            "2962",
            "user@@example.com",
            "@example.com",
            "user@",
        ],
    )
    def test_structure_rejected(self, value: str) -> None:
        """Missing/duplicated `@` and empty parts are rejected."""
        with pytest.raises(ValueError, match="Invalid IDN email format"):
            validate_idn_email(value)

    @pytest.mark.parametrize(
        "value",
        [
            ".user@example.com",
            "user.@example.com",
            "user..name@example.com",
            "user name@münchen.de",
        ],
    )
    def test_invalid_local_rejected(self, value: str) -> None:
        """Dots rules and forbidden ASCII characters still apply to the local part."""
        with pytest.raises(ValueError, match="Invalid IDN email format"):
            validate_idn_email(value)

    def test_local_too_long_in_octets(self) -> None:
        """RFC 6531 keeps the 64-octet limit, counted in UTF-8 bytes."""
        # 33 two-byte characters = 66 octets > 64.
        with pytest.raises(ValueError, match="Invalid IDN email format"):
            validate_idn_email("ю" * 33 + "@example.com")

    def test_total_too_long_in_octets(self) -> None:
        """RFC 6531 keeps the 254-octet total limit, counted in UTF-8 bytes."""
        # Local: 64 octets (valid alone); domain: 253 chars (valid alone);
        #  total: 64 + 1 + 253 = 318 octets > 254.
        local: str = "ю" * 32
        domain: str = "b" * 63 + "." + "c" * 63 + "." + "d" * 63 + "." + "e" * 61
        with pytest.raises(ValueError, match="Invalid IDN email format"):
            validate_idn_email(f"{local}@{domain}")

    @pytest.mark.parametrize(
        "value",
        [
            "user@a..b.com",
            "user@a_b.com",
        ],
    )
    def test_invalid_domain_rejected(self, value: str) -> None:
        """Domain part must be a valid IDN hostname."""
        with pytest.raises(ValueError, match="Invalid IDN email format"):
            validate_idn_email(value)
