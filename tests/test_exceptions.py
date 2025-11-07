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
        # Check that args tuple contains the message
        assert error.args == ("Test error",)
        assert len(error.args) == 1

    def test_exception_args_with_path(self) -> None:
        """Test that exception args contain all fields including path."""
        path = ["definitions", "User", "properties", "name"]
        error = SchemaReferenceError(message="Reference not found", path=path)
        # Check that args tuple contains both message and path
        assert error.args == ("Reference not found", path)
        assert len(error.args) == 2
        # Verify we can unpack args
        msg, error_path = error.args
        assert msg == "Reference not found"
        assert error_path == path

    def test_exception_args_with_value(self) -> None:
        """Test that exception args contain all fields including value."""
        test_value = {"invalid": "data"}
        error = FormatValidationError(message="Invalid format", value=test_value)
        # Check that args tuple contains both message and value
        assert error.args == ("Invalid format", test_value)
        assert len(error.args) == 2
        # Verify we can unpack args
        msg, val = error.args
        assert msg == "Invalid format"
        assert val == test_value

    def test_exception_args_with_default_value(self) -> None:
        """Test that exception args include default values."""
        error = FormatValidationError(message="Invalid format")
        # Check that args tuple contains message and default value (None)
        assert error.args == ("Invalid format", None)
        assert len(error.args) == 2
