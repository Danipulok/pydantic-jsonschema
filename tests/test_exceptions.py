"""Tests for exceptions."""

import pytest

from pydantic_jsonschema.exceptions import (
    FormatValidationError,
    SchemaConversionError,
    SchemaReferenceError,
)


class TestExceptions:
    """Tests for schema exceptions."""

    def test_schema_conversion_error(self) -> None:
        """Test `SchemaConversionError` stores message and renders in `repr()`."""
        error = SchemaConversionError(message="Invalid schema format")
        assert str(error)
        assert "Invalid schema format" in repr(error)

        with pytest.raises(SchemaConversionError) as exc_info:
            raise error
        assert exc_info.value.message == "Invalid schema format"

    def test_schema_reference_error(self) -> None:
        """Test `SchemaReferenceError` stores message and path."""
        error = SchemaReferenceError(message="Reference not found", path=["definitions", "User"])
        assert str(error)
        assert "Reference not found" in repr(error)
        assert error.path == ["definitions", "User"]

        with pytest.raises(SchemaReferenceError) as exc_info:
            raise error
        assert exc_info.value.message == "Reference not found"
        assert exc_info.value.path == ["definitions", "User"]

    def test_exception_args_base(self) -> None:
        """Test that `args` contains message for base exception."""
        error = SchemaConversionError(message="Test error")
        assert error.args == ("Test error",)

    def test_exception_args_with_path(self) -> None:
        """Test that `args` contains message and path."""
        path = ["definitions", "User", "properties", "name"]
        error = SchemaReferenceError(message="Reference not found", path=path)
        assert error.args == ("Reference not found", path)

    def test_exception_args_with_value(self) -> None:
        """Test that `args` contains message and value."""
        test_value = {"invalid": "data"}
        error = FormatValidationError(message="Invalid format", value=test_value)
        assert error.args == ("Invalid format", test_value)

    def test_exception_args_with_default_value(self) -> None:
        """Test that `args` includes `None` default for value."""
        error = FormatValidationError(message="Invalid format")
        assert error.args == ("Invalid format", None)
