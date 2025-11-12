"""Tests for exceptions."""

import pytest

from pydantic_jsonschema.exceptions import (
    FormatValidationError,
    SchemaConvertionError,
    SchemaReferenceError,
)


class TestExceptions:
    """Tests for schema exceptions."""

    def test_parsing_error(self) -> None:
        """Test SchemaConvertionError exception."""
        error = SchemaConvertionError(message="Invalid schema format")
        assert str(error)  # Triggers __str__
        assert "Invalid schema format" in repr(error)

        # Test that it can be raised and caught
        with pytest.raises(SchemaConvertionError) as exc_info:
            raise error
        assert exc_info.value.message == "Invalid schema format"

    def test_schema_reference_error(self) -> None:
        """Test SchemaReferenceError exception."""
        error = SchemaReferenceError(message="Reference not found", path=["definitions", "User"])
        assert str(error)  # Triggers __str__
        assert "Reference not found" in repr(error)
        assert error.path == ["definitions", "User"]

        # Test that it can be raised and caught
        with pytest.raises(SchemaReferenceError) as exc_info:
            raise error
        assert exc_info.value.message == "Reference not found"
        assert exc_info.value.path == ["definitions", "User"]

    def test_exception_args_base(self) -> None:
        """Test that exception args contain all fields for base exception."""
        error = SchemaConvertionError(message="Test error")
        assert error.args == ("Test error",)

    def test_exception_args_with_path(self) -> None:
        """Test that exception args contain all fields including path."""
        path = ["definitions", "User", "properties", "name"]
        error = SchemaReferenceError(message="Reference not found", path=path)
        assert error.args == ("Reference not found", path)

    def test_exception_args_with_value(self) -> None:
        """Test that exception args contain all fields including value."""
        test_value = {"invalid": "data"}
        error = FormatValidationError(message="Invalid format", value=test_value)
        assert error.args == ("Invalid format", test_value)

    def test_exception_args_with_default_value(self) -> None:
        """Test that exception args include default values."""
        error = FormatValidationError(message="Invalid format")
        assert error.args == ("Invalid format", None)
