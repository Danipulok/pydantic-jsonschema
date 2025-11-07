"""Tests for schema converters."""

import pytest
from openapi_pydantic import Schema
from pydantic import ValidationError

from pydantic_jsonschema import SchemaConverter, convert_schema


class TestBasicConversion:
    """Tests for basic schema conversion."""

    def test_simple_object_schema(self) -> None:
        """Test converting simple object schema."""
        schema = Schema(
            type="object",
            properties={
                "name": Schema(type="string"),
                "age": Schema(type="integer"),
            },
            required=["name"],
        )

        Model = convert_schema(schema)

        # Valid instance
        instance = Model(name="Alice", age=30)
        assert instance.name == "Alice"  # type: ignore[attr-defined]
        assert instance.age == 30  # type: ignore[attr-defined]

        # Missing optional field
        instance2 = Model(name="Bob")
        assert instance2.name == "Bob"  # type: ignore[attr-defined]
        assert instance2.age is None  # type: ignore[attr-defined]

        # Missing required field
        with pytest.raises(ValidationError):
            Model(age=25)

    def test_array_schema(self) -> None:
        """Test array schema conversion."""
        schema = Schema(
            type="object",
            properties={
                "tags": Schema(
                    type="array",
                    items=Schema(type="string"),
                ),
            },
        )

        Model = convert_schema(schema)
        instance = Model(tags=["python", "dev"])
        assert instance.tags == ["python", "dev"]  # type: ignore[attr-defined]

    def test_nested_objects(self) -> None:
        """Test nested object schemas."""
        schema = Schema(
            type="object",
            properties={
                "user": Schema(
                    type="object",
                    properties={
                        "name": Schema(type="string"),
                    },
                ),
            },
        )

        Model = convert_schema(schema)
        instance = Model(user={"name": "Alice"})
        assert instance.user.name == "Alice"  # type: ignore[attr-defined]


class TestReferences:
    """Tests for $defs and $ref support."""

    def test_nested_definition(self) -> None:
        """Test nested schema definitions."""
        schema = Schema(
            type="object",
            properties={
                "address": Schema(
                    type="object",
                    properties={
                        "street": Schema(type="string"),
                        "city": Schema(type="string"),
                    },
                ),
            },
        )

        Model = convert_schema(schema)
        instance = Model(address={"street": "Main St", "city": "NYC"})
        assert instance.address.street == "Main St"  # type: ignore[attr-defined]
        assert instance.address.city == "NYC"  # type: ignore[attr-defined]


class TestComposition:
    """Tests for allOf, anyOf, oneOf."""

    def test_allof_composition(self) -> None:
        """Test allOf composition."""
        schema = Schema(
            type="object",
            allOf=[
                Schema(
                    type="object",
                    properties={"name": Schema(type="string")},
                    required=["name"],
                ),
                Schema(
                    type="object",
                    properties={"age": Schema(type="integer")},
                ),
            ],
        )

        Model = convert_schema(schema)
        instance = Model(name="Alice", age=30)
        assert instance.name == "Alice"  # type: ignore[attr-defined]
        assert instance.age == 30  # type: ignore[attr-defined]

    def test_anyof_union(self) -> None:
        """Test anyOf creates Union types."""
        schema = Schema(
            type="object",
            properties={
                "value": Schema(
                    anyOf=[
                        Schema(type="string"),
                        Schema(type="integer"),
                    ],
                ),
            },
        )

        Model = convert_schema(schema)
        instance1 = Model(value="hello")
        assert instance1.value == "hello"  # type: ignore[attr-defined]

        instance2 = Model(value=42)
        assert instance2.value == 42  # type: ignore[attr-defined]


class TestBeforeValidators:
    """Tests for before_validators support."""

    def test_before_validator_coercion(self) -> None:
        """Test before validator coerces types."""

        def str_to_int(value: object) -> int:
            if isinstance(value, str):
                return int(value)
            return value  # type: ignore[return-value]

        converter = SchemaConverter(before_validators={"custom-int": str_to_int})

        schema = Schema(
            type="object",
            properties={
                "age": Schema(type="integer", format="custom-int"),
            },
        )

        Model = converter.convert_schema(schema)
        instance = Model(age="25")
        assert instance.age == 25  # type: ignore[attr-defined]
        assert isinstance(instance.age, int)  # type: ignore[attr-defined]
