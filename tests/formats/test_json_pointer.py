"""Tests for JSON Pointer format validators.

See: https://www.rfc-editor.org/rfc/rfc6901#section-3
See: https://datatracker.ietf.org/doc/html/draft-bhutton-relative-json-pointer-00#section-3

Test data derived from the JSON Schema Test Suite (MIT):
https://github.com/json-schema-org/JSON-Schema-Test-Suite/blob/fe8c2f0de2041943975932b6bf4bd882625b6cfb/tests/draft2020-12/optional/format/json-pointer.json
https://github.com/json-schema-org/JSON-Schema-Test-Suite/blob/fe8c2f0de2041943975932b6bf4bd882625b6cfb/tests/draft2020-12/optional/format/relative-json-pointer.json
"""

import pytest

from pydantic_jsonschema.formats._json_pointer import (
    validate_json_pointer,
    validate_relative_json_pointer,
)


class TestValidJsonPointer:
    """Valid JSON Pointers per RFC 6901."""

    @pytest.mark.parametrize(
        "value",
        [
            "",
            "/foo",
            "/foo/0",
            "/",
            "/a~1b",
            "/c%d",
            "/e^f",
            "/g|h",
            "/i\\j",
            '/k"l',
            "/ ",
            "/m~0n",
        ],
    )
    def test_rfc_examples(self, value: str) -> None:
        """RFC 6901 §5 example document pointers."""
        assert validate_json_pointer(value) == value

    @pytest.mark.parametrize(
        "value",
        [
            "/foo//bar",
            "/foo/bar/",
        ],
    )
    def test_empty_segments(self, value: str) -> None:
        """Empty reference tokens are valid."""
        assert validate_json_pointer(value) == value

    @pytest.mark.parametrize(
        "value",
        [
            "/foo/bar~0/baz~1/%a",
            "/~1~0~0~1~1",
            "/~1.1",
            "/~0.1",
        ],
    )
    def test_escaped_tokens(self, value: str) -> None:
        """`~0` and `~1` escape sequences are valid."""
        assert validate_json_pointer(value) == value

    @pytest.mark.parametrize(
        "value",
        [
            "/foo/-",
            "/foo/-/bar",
        ],
    )
    def test_dash_token(self, value: str) -> None:
        """`-` is a valid token (last array position / member name)."""
        assert validate_json_pointer(value) == value

    @pytest.mark.parametrize(
        "value",
        [
            "/foo/bar/\U0001f60e",
            "/foo\x00bar\n\tbaz",
        ],
    )
    def test_unicode_and_control_characters(self, value: str) -> None:
        """RFC 6901 allows any character except unescaped `/` and `~`."""
        assert validate_json_pointer(value) == value


class TestInvalidJsonPointer:
    """Invalid JSON Pointers per RFC 6901."""

    @pytest.mark.parametrize(
        "value",
        [
            "a",
            "0",
            "a/a",
        ],
    )
    def test_missing_leading_slash(self, value: str) -> None:
        """Non-empty pointer must start with `/`."""
        with pytest.raises(ValueError, match="Invalid JSON Pointer format"):
            validate_json_pointer(value)

    @pytest.mark.parametrize(
        "value",
        [
            "/foo/bar~",
            "/~0~",
            "/~0/~",
            "/~~",
            "/~2",
            "/~-1",
        ],
    )
    def test_invalid_escape(self, value: str) -> None:
        """`~` must be followed by `0` or `1`."""
        with pytest.raises(ValueError, match="Invalid JSON Pointer format"):
            validate_json_pointer(value)

    @pytest.mark.parametrize(
        "value",
        [
            "#",
            "#/",
            "#a",
        ],
    )
    def test_uri_fragment_form_rejected(self, value: str) -> None:
        """URI Fragment Identifier representation is not a JSON Pointer."""
        with pytest.raises(ValueError, match="Invalid JSON Pointer format"):
            validate_json_pointer(value)


class TestValidRelativeJsonPointer:
    """Valid Relative JSON Pointers per the draft."""

    @pytest.mark.parametrize(
        "value",
        [
            "0",
            "1",
            "0/foo/bar",
            "2/0/baz/1/zip",
            "120/foo/bar",
            "2/a~1b",
        ],
    )
    def test_prefix_with_pointer(self, value: str) -> None:
        """Non-negative integer prefix followed by a JSON Pointer."""
        assert validate_relative_json_pointer(value) == value

    @pytest.mark.parametrize(
        "value",
        [
            "0#",
            "1#",
            "10#",
        ],
    )
    def test_index_reference(self, value: str) -> None:
        """`#` suffix references the key/index itself."""
        assert validate_relative_json_pointer(value) == value


class TestInvalidRelativeJsonPointer:
    """Invalid Relative JSON Pointers per the draft."""

    @pytest.mark.parametrize(
        "value",
        [
            "-1/foo/bar",
            "+1/foo/bar",
            "01/a",
            "01#",
            "00",
            "1.5",
        ],
    )
    def test_invalid_prefix(self, value: str) -> None:
        """Prefix must be a non-negative integer without sign or leading zeros."""
        with pytest.raises(ValueError, match="Invalid Relative JSON Pointer format"):
            validate_relative_json_pointer(value)

    @pytest.mark.parametrize(
        "value",
        [
            "",
            "/foo/bar",
            "#",
            "0##",
            "1#/foo",
            "abc",
        ],
    )
    def test_invalid_structure(self, value: str) -> None:
        """Prefix is mandatory; `#` must be the final character."""
        with pytest.raises(ValueError, match="Invalid Relative JSON Pointer format"):
            validate_relative_json_pointer(value)
