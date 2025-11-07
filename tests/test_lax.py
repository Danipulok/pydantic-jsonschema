import pytest

from pydantic_jsonschema._lax import (
    COERCE_FUNCTIONS,
    coerce_to_float,
    coerce_to_int,
    coerce_to_list,
    coerce_to_str,
    load_json_simple,
)


class TestCoerceFunctions:
    """Tests for coerce functions."""

    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            ('{"key": "value", "number": 42}', {"key": "value", "number": 42}),
            ('["item1", "item2", 123]', ["item1", "item2", 123]),
            ("{}", {}),
            ("[]", []),
            ('  {"key": "value"}  \n', {"key": "value"}),
            (
                '{"list": [1, 2, 3], "dict": {"nested": true}}',
                {"list": [1, 2, 3], "dict": {"nested": True}},
            ),
        ],
    )
    def test_load_valid_json(self, data: str, expected) -> None:
        """Test loading valid JSON."""
        result = load_json_simple(data)
        assert result == expected

    @pytest.mark.parametrize(
        "data",
        [
            "{invalid json}",
            "just a string",
            "null",
            "",
            '{"key": "value"',
        ],
    )
    def test_load_invalid_json(self, data: str) -> None:
        """Test loading invalid JSON returns None."""
        result = load_json_simple(data)
        assert result is None

    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            ("123", 123),
            ("true", True),
            ("false", False),
        ],
    )
    def test_load_valid_primitives(self, data: str, expected) -> None:
        """Test loading valid JSON primitives returns the parsed value."""
        result = load_json_simple(data)
        assert result == expected

    @pytest.mark.parametrize(
        ("coerce_func", "value", "expected"),
        [
            # String coercion
            (coerce_to_str, None, ""),
            (coerce_to_str, 123, "123"),
            (coerce_to_str, 0, "0"),
            (coerce_to_str, -42, "-42"),
            (coerce_to_str, 3.14, "3.14"),
            (coerce_to_str, 0.0, "0.0"),
            (coerce_to_str, -2.5, "-2.5"),
            (coerce_to_str, "hello", "hello"),
            (coerce_to_str, "", ""),
            (coerce_to_str, True, "True"),
            (coerce_to_str, False, "False"),
            # Int coercion
            (coerce_to_int, "123", 123),
            (coerce_to_int, "-42", -42),
            (coerce_to_int, "0", 0),
            (coerce_to_int, 3.14, 3),
            (coerce_to_int, 3.99, 3),
            (coerce_to_int, -2.5, -2),
            (coerce_to_int, 123, 123),
            (coerce_to_int, 0, 0),
            (coerce_to_int, -42, -42),
            (coerce_to_int, True, 1),
            (coerce_to_int, False, 0),
            # Float coercion
            (coerce_to_float, "3.14", 3.14),
            (coerce_to_float, "123", 123.0),
            (coerce_to_float, "-2.5", -2.5),
            (coerce_to_float, 123, 123.0),
            (coerce_to_float, 0, 0.0),
            (coerce_to_float, -42, -42.0),
            (coerce_to_float, 3.14, 3.14),
            (coerce_to_float, 0.0, 0.0),
            (coerce_to_float, True, 1.0),
            (coerce_to_float, False, 0.0),
            # List coercion
            (coerce_to_list, None, []),
            (coerce_to_list, "a, b, c", ["a", "b", "c"]),
            (coerce_to_list, "item1, item2", ["item1", "item2"]),
            (coerce_to_list, "a,b,c", ["a", "b", "c"]),
            (coerce_to_list, "a  ,  b  ,  c", ["a", "b", "c"]),
            (coerce_to_list, "[]", []),
            (coerce_to_list, "single", "single"),
            (coerce_to_list, "just a string", "just a string"),
            (coerce_to_list, "", ""),
            (coerce_to_list, "a,,c", ["a", "", "c"]),
        ],
    )
    def test_coerce_functions(self, coerce_func, value, expected) -> None:
        """Test all coerce functions with various inputs."""
        result = coerce_func(value)
        assert result == expected

    @pytest.mark.parametrize(
        ("coerce_func", "value"),
        [
            (coerce_to_int, "not a number"),
            (coerce_to_int, "12.34"),
            (coerce_to_int, ""),
            (coerce_to_int, None),
            (coerce_to_float, "not a number"),
            (coerce_to_float, ""),
            (coerce_to_float, None),
        ],
    )
    def test_coerce_unchanged(self, coerce_func, value) -> None:
        """Test coerce functions return unchanged for invalid values."""
        result = coerce_func(value)
        assert result == value

    """Tests for edge cases and complex scenarios."""

    def test_coerce_chain_str_to_int_to_float(self) -> None:
        """Test chaining coercions."""
        value = "123"
        value = coerce_to_int(value)
        assert value == 123
        value = coerce_to_float(value)
        assert value == 123.0

    @pytest.mark.parametrize(
        "value",
        [
            999999999999999999999,
            -999999999999999999999,
        ],
    )
    def test_coerce_large_numbers(self, value) -> None:
        """Test coercion with large numbers."""
        assert coerce_to_str(value) == str(value)
        assert coerce_to_float(value) == float(value)

    @pytest.mark.parametrize(
        ("special_value", "expected"),
        [
            (float("inf"), "inf"),
            (float("-inf"), "-inf"),
            (float("nan"), "nan"),
        ],
    )
    def test_coerce_special_floats(self, special_value, expected) -> None:
        """Test coercion with special float values."""
        result = coerce_to_str(special_value)
        assert result == expected

    def test_json_with_various_types(self) -> None:
        """Test JSON loading with mixed types."""
        data = (
            '{"str": "value", "int": 123, "float": 3.14, "bool": true, '
            '"null": null, "list": [1, 2], "dict": {}}'
        )
        result = load_json_simple(data)
        assert result["str"] == "value"
        assert result["int"] == 123
        assert result["float"] == 3.14
        assert result["bool"] is True
        assert result["null"] is None
        assert result["list"] == [1, 2]
        assert result["dict"] == {}

    def test_csv_with_empty_values(self) -> None:
        """Test CSV parsing with empty values."""
        result = coerce_to_list("a,,c")
        assert result == ["a", "", "c"]

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("こんにちは", "こんにちは"),
            ("café", "café"),
            ("🚀", "🚀"),
        ],
    )
    def test_unicode_handling(self, value, expected) -> None:
        """Test handling of Unicode characters."""
        assert coerce_to_str(value) == expected
        result = load_json_simple(f'{{"greeting": "{value}"}}')
        assert result == {"greeting": expected}


class TestCoerceFunctionsMapping:
    """Tests for COERCE_FUNCTIONS mapping."""

    def test_coerce_functions_dict_structure(self) -> None:
        """Test COERCE_FUNCTIONS dict has expected structure."""
        assert isinstance(COERCE_FUNCTIONS, dict)
        assert str in COERCE_FUNCTIONS
        assert int in COERCE_FUNCTIONS
        assert float in COERCE_FUNCTIONS
        assert list in COERCE_FUNCTIONS

    def test_coerce_functions_are_callable(self) -> None:
        """Test all coerce functions are callable."""
        for coerce_func in COERCE_FUNCTIONS.values():
            assert callable(coerce_func)

    @pytest.mark.parametrize(
        ("func_type", "value", "expected"),
        [
            (str, None, ""),
            (str, 123, "123"),
            (int, "123", 123),
            (int, 3.14, 3),
            (float, "3.14", 3.14),
            (float, 123, 123.0),
            (list, None, []),
            (list, "a, b", ["a", "b"]),
        ],
    )
    def test_coerce_function_from_dict(self, func_type, value, expected) -> None:
        """Test coerce functions in COERCE_FUNCTIONS dict."""
        result = COERCE_FUNCTIONS[func_type](value)
        assert result == expected

    def test_list_stays_list(self) -> None:
        """Test list stays as list."""
        original = [1, 2, 3]
        assert coerce_to_list(original) == original
