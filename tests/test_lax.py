"""Tests for lax schema conversion."""

from openapi_pydantic import Schema
from pydantic import ValidationError

from pydantic_jsonschema import LaxSchemaConverter, convert_schema_lax


class TestLaxConversion:
    """Tests for lax conversion mode."""

    def test_all_fields_optional(self):
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

    def test_list_default(self):
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

    def test_dict_default(self):
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

    def test_explicit_defaults_preserved(self):
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

    def test_lax_accepts_full_data(self):
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
