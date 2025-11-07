"""Tests for format validators."""

import pytest
from openapi_pydantic.v3 import DataType

from pydantic_jsonschema.formats import SchemaFormat


class TestSchemaFormat:
    """Tests for SchemaFormat class."""

    def test_format_without_validator(self) -> None:
        """Test SchemaFormat without validator."""
        fmt = SchemaFormat(
            key="custom",
            title="Custom",
            examples=["example"],
            types=[DataType.STRING],
            validator=None,
        )

        # Should return value as-is when validator is None
        assert fmt("test") == "test"
        assert fmt(123) == 123

    def test_format_with_validator(self) -> None:
        """Test SchemaFormat with validator."""

        def uppercase_validator(value: object) -> str:
            if not isinstance(value, str):
                msg = "Must be string"
                raise ValueError(msg)
            return value.upper()

        fmt = SchemaFormat(
            key="uppercase",
            title="Uppercase",
            examples=["hello"],
            types=[DataType.STRING],
            validator=uppercase_validator,
        )

        assert fmt("test") == "TEST"
        assert fmt("hello") == "HELLO"

    def test_format_invalid_example(self) -> None:
        """Test SchemaFormat with invalid example raises error."""

        def int_validator(value: object) -> int:
            if not isinstance(value, (int, str)):
                msg = "Must be int or string"
                raise ValueError(msg)
            return int(value) if isinstance(value, str) else value

        # This should raise during creation because example is invalid
        with pytest.raises(ValueError, match="Invalid example"):
            SchemaFormat(
                key="int-only",
                title="Integer Only",
                examples=["not-a-number"],  # Invalid example
                types=[DataType.INTEGER],
                validator=int_validator,
            )
