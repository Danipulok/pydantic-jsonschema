"""Tests for schema converters."""

import pytest
from openapi_pydantic import Schema
from pydantic import ValidationError

from pydantic_jsonschema import to_model


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

        Model = to_model(schema)

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

        Model = to_model(schema)
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

        Model = to_model(schema)
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

        Model = to_model(schema)
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

        Model = to_model(schema)
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

        Model = to_model(schema)
        instance1 = Model(value="hello")
        assert instance1.value == "hello"  # type: ignore[attr-defined]

        instance2 = Model(value=42)
        assert instance2.value == 42  # type: ignore[attr-defined]


class TestLaxConversion:
    """Tests for lax conversion mode."""

    def test_all_fields_optional(self) -> None:
        """Test that all fields become optional in lax mode."""
        schema = Schema(
            type="object",
            properties={
                "name": Schema(type="string"),
                "age": Schema(type="integer"),
            },
            required=["name", "age"],
        )

        Model = convert_schema_lax(schema)

        # Can create with no fields
        instance = Model()
        assert instance.name is None
        assert instance.age is None

        # Can create with partial fields
        instance2 = Model(name="Alice")
        assert instance2.name == "Alice"
        assert instance2.age is None

    def test_list_default(self) -> None:
        """Test that lists get [] as default when no minItems."""
        schema = Schema(
            type="object",
            properties={
                "tags": Schema(type="array", items=Schema(type="string")),
            },
            required=["tags"],
        )

        Model = convert_schema_lax(schema)
        instance = Model()
        assert instance.tags == []

    def test_dict_default(self) -> None:
        """Test that objects get {} as default when no minProperties."""
        schema = Schema(
            type="object",
            properties={
                "metadata": Schema(type="object"),
            },
            required=["metadata"],
        )

        Model = convert_schema_lax(schema)
        instance = Model()
        assert instance.metadata == {}

    def test_explicit_defaults_preserved(self) -> None:
        """Test that explicit defaults are preserved."""
        schema = Schema(
            type="object",
            properties={
                "status": Schema(type="string", default="pending"),
            },
        )

        Model = convert_schema_lax(schema)
        instance = Model()
        assert instance.status == "pending"

    def test_lax_accepts_full_data(self) -> None:
        """Test that lax mode still accepts complete data."""
        schema = Schema(
            type="object",
            properties={
                "name": Schema(type="string"),
                "age": Schema(type="integer"),
                "tags": Schema(type="array", items=Schema(type="string")),
            },
            required=["name", "age"],
        )

        Model = convert_schema_lax(schema)
        instance = Model(name="Alice", age=30, tags=["dev", "python"])
        assert instance.name == "Alice"
        assert instance.age == 30
        assert instance.tags == ["dev", "python"]
