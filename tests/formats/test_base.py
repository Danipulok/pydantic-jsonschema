import pytest
from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema

from pydantic_jsonschema.formats import SchemaFormat
from pydantic_jsonschema.types import DataType


class MockLanguageCode:
    """Mock Pydantic type that validates language codes (like LanguageAlpha2)."""

    def __init__(self, value: str) -> None:
        if not isinstance(value, str):
            msg = "Must be a string"
            raise TypeError(msg)
        if len(value) != 2 or not value.isalpha():
            msg = f"Invalid language code: {value!r}. Must be 2 letters."
            raise ValueError(msg)
        self.value = value.lower()

    def __str__(self) -> str:
        return self.value

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: type, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        """Pydantic core schema for validation."""
        return core_schema.no_info_after_validator_function(cls, handler(str))


class MockCurrencyCode:
    """Mock Pydantic type that validates currency codes (like Currency)."""

    def __init__(self, value: str) -> None:
        if not isinstance(value, str):
            msg = "Must be a string"
            raise TypeError(msg)
        if len(value) != 3 or not value.isalpha():
            msg = f"Invalid currency code: {value!r}. Must be 3 letters."
            raise ValueError(msg)
        self.value = value.upper()

    def __str__(self) -> str:
        return self.value

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: type, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        """Pydantic core schema for validation."""
        return core_schema.no_info_after_validator_function(cls, handler(str))


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

        def string_validator(value: object) -> str:
            if not isinstance(value, str):
                msg = "Must be string"
                raise ValueError(msg)
            return value

        fmt = SchemaFormat(
            key="string-only",
            title="String Only",
            examples=["hello"],
            types=[DataType.STRING],
            validator=string_validator,
        )

        # Validator runs for validation, but original value is returned
        assert fmt("test") == "test"
        assert fmt("hello") == "hello"

        # Validator rejects invalid input
        with pytest.raises(ValueError, match="Must be string"):
            fmt(123)

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

    def test_format_with_pydantic_type_validator(self) -> None:
        """Test SchemaFormat with Pydantic type class as validator."""
        fmt = SchemaFormat(
            key="language-code",
            title="Language Code",
            examples=["en", "fr"],
            types=[DataType.STRING],
            validator=MockLanguageCode,
        )

        # Validator runs for validation, but original value is returned
        result = fmt("en")
        assert result == "en"
        assert isinstance(result, str)

        result = fmt("FR")
        assert result == "FR"
        assert isinstance(result, str)

    def test_format_with_pydantic_type_validator_invalid(self) -> None:
        """Test SchemaFormat with Pydantic type validator rejects invalid input."""
        fmt = SchemaFormat(
            key="language-code",
            title="Language Code",
            examples=["en", "fr"],
            types=[DataType.STRING],
            validator=MockLanguageCode,
        )

        # Should raise on invalid input
        with pytest.raises(ValueError, match="Invalid language code"):
            fmt("invalid")

        with pytest.raises(ValueError, match="Invalid language code"):
            fmt("e")  # Too short

        with pytest.raises(ValueError, match="Invalid language code"):
            fmt("eng")  # Too long

    def test_format_with_pydantic_type_invalid_example(self) -> None:
        """Test SchemaFormat with Pydantic type validator and invalid example."""
        # Should raise during creation because example is invalid
        with pytest.raises(ValueError, match="Invalid example"):
            SchemaFormat(
                key="language-code",
                title="Language Code",
                examples=["en", "invalid-code"],  # Second example is invalid
                types=[DataType.STRING],
                validator=MockLanguageCode,
            )

    def test_format_with_currency_type_validator(self) -> None:
        """Test SchemaFormat with currency type validator."""
        fmt = SchemaFormat(
            key="currency-code",
            title="Currency Code",
            examples=["USD", "EUR"],
            types=[DataType.STRING],
            validator=MockCurrencyCode,
        )

        # Validator runs for validation, but original value is returned
        result = fmt("USD")
        assert result == "USD"
        assert isinstance(result, str)

        result = fmt("eur")
        assert result == "eur"
        assert isinstance(result, str)

        # Should raise on invalid input
        with pytest.raises(ValueError, match="Invalid currency code"):
            fmt("US")  # Too short
