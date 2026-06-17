"""Tests for URI Template format validator.

See: https://www.rfc-editor.org/rfc/rfc6570#section-2

Test data derived from RFC 6570 examples and the JSON Schema Test Suite (MIT):
https://github.com/json-schema-org/JSON-Schema-Test-Suite/blob/fe8c2f0de2041943975932b6bf4bd882625b6cfb/tests/draft2020-12/optional/format/uri-template.json
"""

import pytest

from pydantic_jsonschema.formats._uri_template import validate_uri_template


class TestValidUriTemplate:
    """Valid URI Templates per RFC 6570."""

    @pytest.mark.parametrize(
        "value",
        [
            r"http://example.com/~{username}/",
            r"http://example.com/dictionary/{term:1}/{term}",
            r"http://example.com/search{?q,lang}",
            r"http://www.example.com/foo{?query,number}",
            r"dictionary/{term:1}/{term}",
        ],
    )
    def test_rfc_examples(self, value: str) -> None:
        """Templates from RFC 6570 examples, absolute and relative."""
        assert validate_uri_template(value) == value

    @pytest.mark.parametrize(
        "value",
        [
            r"{var}",
            r"{+path}/here",
            r"{#fragment}",
            r"{.suffix}",
            r"{/path,to,resource}",
            r"{;params}",
            r"{&extra}",
            r"{=reserved}",
        ],
    )
    def test_operators(self, value: str) -> None:
        """All RFC 6570 operators are accepted."""
        assert validate_uri_template(value) == value

    @pytest.mark.parametrize(
        "value",
        [
            r"{list*}",
            r"{var:30}",
            r"{var:9999}",
            r"{a.b.c}",
            r"{%61}",
        ],
    )
    def test_varspec_modifiers(self, value: str) -> None:
        """Explode, prefix modifiers, dotted names, and pct-encoded varchars."""
        assert validate_uri_template(value) == value

    @pytest.mark.parametrize(
        "value",
        [
            r"",
            r"http://example.com/no/template",
            r"with%20encoding",
        ],
    )
    def test_plain_uris(self, value: str) -> None:
        """Templates without expressions are valid."""
        assert validate_uri_template(value) == value


class TestInvalidUriTemplate:
    """Invalid URI Templates per RFC 6570."""

    @pytest.mark.parametrize(
        "value",
        [
            r"{var",
            r"var}",
            r"{var}}extra{",
            r"http://example.com/dictionary/{term:1}/{term",
        ],
    )
    def test_unbalanced_braces(self, value: str) -> None:
        """Unbalanced braces are rejected."""
        with pytest.raises(ValueError, match="Invalid URI Template format"):
            validate_uri_template(value)

    @pytest.mark.parametrize(
        "value",
        [
            r"{}",
            r"{ var}",
            r"{a,}",
            r"{var:0}",
            r"{var:10000}",
            r"{-prefix|/|var}",
        ],
    )
    def test_invalid_expression(self, value: str) -> None:
        """Empty/malformed varspecs and pre-RFC operators are rejected."""
        with pytest.raises(ValueError, match="Invalid URI Template format"):
            validate_uri_template(value)

    @pytest.mark.parametrize(
        "value",
        [
            "100%",
            "with space",
            "back\\slash",
        ],
    )
    def test_invalid_literals(self, value: str) -> None:
        """Bare `%`, spaces, and forbidden literal characters are rejected."""
        with pytest.raises(ValueError, match="Invalid URI Template format"):
            validate_uri_template(value)
