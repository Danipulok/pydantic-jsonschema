"""Tests for exceptions."""

import pytest

from pydantic_jsonschema.exceptions import SchemaConvertionError, SchemaReferenceError


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
