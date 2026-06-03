from typing import ClassVar

import pytest
from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema

from pydantic_jsonschema.formats._base import SchemaFormat
from pydantic_jsonschema.types import DataType, JsonType


class MockLanguageCode:
    """Mock Pydantic type that validates language codes (like LanguageAlpha2)."""

    LANGUAGE_CODE_LENGTH: ClassVar[int] = 2

    def __init__(self, value: str) -> None:
        if not isinstance(value, str):
            msg = "Must be a string"
            raise TypeError(msg)
        if len(value) != self.LANGUAGE_CODE_LENGTH or not value.isalpha():
            msg = f"Invalid language code: {value!r}. Must be 2 letters."
            raise ValueError(msg)
        self.value = value.lower()

    def __str__(self) -> str:
        return self.value

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source_type: type,
        handler: GetCoreSchemaHandler,
    ) -> CoreSchema:
        """Pydantic core schema for validation."""
        return core_schema.no_info_after_validator_function(cls, handler(str))


class MockCurrencyCode:
    """Mock Pydantic type that validates currency codes (like Currency)."""

    CURRENCY_CODE_LENGTH: ClassVar[int] = 3

    def __init__(self, value: str) -> None:
        if not isinstance(value, str):
            msg = "Must be a string"
            raise TypeError(msg)
        if len(value) != self.CURRENCY_CODE_LENGTH or not value.isalpha():
            msg = f"Invalid currency code: {value!r}. Must be 3 letters."
            raise ValueError(msg)
        self.value = value.upper()

    def __str__(self) -> str:
        return self.value

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source_type: type,
        handler: GetCoreSchemaHandler,
    ) -> CoreSchema:
        """Pydantic core schema for validation."""
        return core_schema.no_info_after_validator_function(cls, handler(str))


class TestSchemaFormat:
    """Tests for SchemaFormat class."""

    def test_format_auto_generate_title(self) -> None:
        """Test SchemaFormat auto-generates title from key when title is None."""
        fmt = SchemaFormat(
            key="date-time",
            title=None,
            examples=["2024-01-01T00:00:00Z"],
            types=[DataType.STRING],
        )
        assert fmt.title == "Date Time"

        fmt = SchemaFormat(
            key="",
            title=None,
            examples=["example"],
            types=[DataType.STRING],
        )
        assert fmt.title == ""

    def test_format_without_validator(self) -> None:
        """Test SchemaFormat without validator."""
        fmt = SchemaFormat(
            key="custom",
            title="Custom",
            examples=["example"],
            types=[DataType.STRING],
            validator=None,
        )

        values: list[JsonType] = ["test", 123, 45.6, True, None, {"key": "value"}, [1, 2, 3]]
        for val in values:
            assert fmt(val) == val

    def test_format_with_validator(self) -> None:
        """Test SchemaFormat with validator."""

        def string_validator(value: object) -> str:
            if not isinstance(value, str):
                msg = "Must be string"
                # Pydantic expects only `ValueError` and `AssertionError`, not `TypeError`
                raise ValueError(msg)  # noqa: TRY004
            return value

        fmt = SchemaFormat(
            key="string-only",
            title="String Only",
            examples=["hello"],
            types=[DataType.STRING],
            validator=string_validator,
        )

        assert fmt("test") == "test"
        assert fmt("hello") == "hello"

        with pytest.raises(ValueError, match="Must be string"):
            fmt(123)

    def test_format_invalid_example(self) -> None:
        """Test SchemaFormat with invalid example raises error."""

        def int_validator(value: object) -> int:
            if not isinstance(value, (int, str)):
                msg = "Must be int or string"
                # Pydantic expects only `ValueError` and `AssertionError`, not `TypeError`
                raise ValueError(msg)  # noqa: TRY004
            return int(value) if isinstance(value, str) else value

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

        result = fmt("en")
        assert isinstance(result, MockLanguageCode)
        assert str(result) == "en"

        result = fmt("FR")
        assert isinstance(result, MockLanguageCode)
        assert str(result) == "fr"  # MockLanguageCode lowercases the value

    def test_format_with_pydantic_type_validator_invalid(self) -> None:
        """Test SchemaFormat with Pydantic type validator rejects invalid input."""
        fmt = SchemaFormat(
            key="language-code",
            title="Language Code",
            examples=["en", "fr"],
            types=[DataType.STRING],
            validator=MockLanguageCode,
        )

        with pytest.raises(ValueError, match="Invalid language code"):
            fmt("invalid")

        with pytest.raises(ValueError, match="Invalid language code"):
            fmt("e")  # Too short

        with pytest.raises(ValueError, match="Invalid language code"):
            fmt("eng")  # Too long

    def test_format_with_pydantic_type_invalid_example(self) -> None:
        """Test SchemaFormat with Pydantic type validator and invalid example."""
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

        result = fmt("USD")
        assert isinstance(result, MockCurrencyCode)
        assert str(result) == "USD"

        result = fmt("eur")
        assert isinstance(result, MockCurrencyCode)
        assert str(result) == "EUR"  # MockCurrencyCode uppercases the value

        with pytest.raises(ValueError, match="Invalid currency code"):
            fmt("US")  # Too short

    def test_call_without_validator(self) -> None:
        """Test __call__ without validator returns original value."""
        fmt = SchemaFormat(
            key="test",
            examples=["example"],
            types=["string"],
            validator=None,
        )

        values: list[JsonType] = ["hello", 123, None]
        for val in values:
            assert fmt(val) == val

    def test_call_with_validating_validator(self) -> None:
        """Test __call__ with validator that validates and returns value."""

        def validate_positive(v: int) -> int:
            if v <= 0:
                msg = "Must be positive"
                raise ValueError(msg)
            return v

        fmt = SchemaFormat(
            key="positive",
            examples=[1, 42],
            types=["integer"],
            validator=validate_positive,
        )

        for value in [1, 42, 999]:
            assert fmt(value) == value

        with pytest.raises(ValueError, match="Must be positive"):
            fmt(-1)

    def test_call_with_transforming_validator(self) -> None:
        """Test __call__ with validator that transforms the value."""

        def uppercase(v: str) -> str:
            return v.upper()

        fmt = SchemaFormat(
            key="uppercase",
            examples=["HELLO", "WORLD"],
            types=["string"],
            validator=uppercase,
        )

        assert fmt("hello") == "HELLO"
        assert fmt("world") == "WORLD"
        assert fmt("TeSt") == "TEST"

    def test_call_with_transforming_validator_lowercase(self) -> None:
        """Test __call__ with lowercase transformer."""

        def lowercase(v: str) -> str:
            return v.lower()

        fmt = SchemaFormat(
            key="lowercase",
            examples=["hello", "world"],
            types=["string"],
            validator=lowercase,
        )

        assert fmt("HELLO") == "hello"
        assert fmt("WoRlD") == "world"
        assert fmt("TEST") == "test"

    def test_call_with_type_converting_validator(self) -> None:
        """Test __call__ with validator that converts types."""

        def to_int(v: str) -> int:
            return int(v)

        fmt = SchemaFormat(
            key="string-to-int",
            examples=["123", "456"],
            types=["string"],
            validator=to_int,
        )

        for value in ["0", "1", "99"]:
            assert fmt(value) == int(value)
            assert isinstance(fmt(value), int)

    def test_call_with_validator_raising_error(self) -> None:
        """Test __call__ with validator that raises error."""

        def validate_email(v: str) -> str:
            if "@" not in v:
                msg = "Invalid email"
                raise ValueError(msg)
            return v

        fmt = SchemaFormat(
            key="email",
            examples=["test@example.com"],
            types=["string"],
            validator=validate_email,
        )

        assert fmt("test@example.com") == "test@example.com"

        with pytest.raises(ValueError, match="Invalid email"):
            fmt("invalid")

    def test_examples_validation_with_transforming_validator(self) -> None:
        """Test that examples are validated during SchemaFormat creation."""

        def uppercase(v: str) -> str:
            return v.upper()

        fmt = SchemaFormat(
            key="uppercase",
            examples=["hello", "world"],
            types=["string"],
            validator=uppercase,
        )
        assert fmt.examples == ["hello", "world"]

        with pytest.raises(ValueError, match="Invalid example"):
            SchemaFormat(
                key="uppercase",
                examples=["hello", 123],
                types=["string"],
                validator=uppercase,
            )

    def test_call_preserves_validator_return_value(self) -> None:
        """Test that __call__ returns exactly what validator returns."""

        def add_prefix(v: str) -> str:
            return f"prefix_{v}"

        fmt = SchemaFormat(
            key="prefixed",
            examples=["prefix_test"],
            types=["string"],
            validator=add_prefix,
        )

        result = fmt("hello")
        assert result == "prefix_hello"
        assert result != "hello"  # Ensure it's not the original value

    def test_default_factory_for_examples_and_types(self) -> None:
        """Test that examples and types have default_factory (empty lists)."""
        fmt = SchemaFormat(key="test-format")

        assert fmt.examples == []
        assert fmt.types == []
        assert isinstance(fmt.examples, list)
        assert isinstance(fmt.types, list)

        assert fmt.title == "Test Format"

    def test_default_factory_creates_independent_lists(self) -> None:
        """Test that default_factory creates independent list instances."""
        fmt1 = SchemaFormat(key="format1")
        fmt2 = SchemaFormat(key="format2")

        fmt1.examples.append("example1")
        fmt1.types.append(DataType.STRING)

        assert fmt2.examples == []
        assert fmt2.types == []

        assert fmt1.examples == ["example1"]
        assert fmt1.types == [DataType.STRING]
