"""Tests for `_schema.py` JSON Schema models."""

from typing import Any

import pytest
from inline_snapshot import snapshot

from pydantic_jsonschema._schema import DataType, Reference, Schema


class TestDataType:
    """Tests for `DataType` enum."""

    @pytest.mark.parametrize(
        ("member", "value"),
        [
            (DataType.NULL, "null"),
            (DataType.STRING, "string"),
            (DataType.NUMBER, "number"),
            (DataType.INTEGER, "integer"),
            (DataType.BOOLEAN, "boolean"),
            (DataType.ARRAY, "array"),
            (DataType.OBJECT, "object"),
        ],
    )
    def test_values(self, member: DataType, value: str) -> None:
        """Test enum members have correct string values."""
        assert member == value
        assert str(member) == value


class TestReference:
    """Tests for `Reference` model."""

    def test_model_validate(self) -> None:
        """Test parsing from JSON Schema `$ref` dict."""
        ref = Reference.model_validate({"$ref": "#/$defs/User"})
        assert ref.ref == "#/$defs/User"

    def test_serialize_by_alias(self) -> None:
        """Test serialization uses `$ref` key."""
        ref = Reference(ref="#/$defs/User")
        dumped: dict[str, Any] = ref.model_dump()
        assert dumped == snapshot({"$ref": "#/$defs/User"})

    def test_json_by_alias(self) -> None:
        """Test JSON output uses `$ref` key."""
        ref = Reference(ref="#/$defs/User")
        json_str: str = ref.model_dump_json()
        assert '"$ref"' in json_str


class TestSchema:
    """Tests for `Schema` model."""

    def test_empty_schema(self) -> None:
        """Test empty schema dumps to empty dict."""
        schema = Schema()
        dumped: dict[str, Any] = schema.model_dump()
        assert dumped == snapshot({})

    def test_simple_type(self) -> None:
        """Test single-type schema."""
        schema = Schema(type=DataType.STRING)
        dumped: dict[str, Any] = schema.model_dump()
        assert dumped == snapshot({"type": "string"})

    def test_alias_generator_camel_case(self) -> None:
        """Test that snake_case fields serialize to camelCase."""
        schema = Schema.model_validate({"allOf": [{"$ref": "#/$defs/Base"}]})
        assert len(schema.all_of) == 1
        dumped: dict[str, Any] = schema.model_dump()
        assert "allOf" in dumped

    def test_populate_by_name(self) -> None:
        """Test that fields can be set using Python names."""
        schema = Schema(min_length=5, max_length=10)
        dumped: dict[str, Any] = schema.model_dump()
        assert dumped == snapshot({"minLength": 5, "maxLength": 10})

    def test_defs_alias(self) -> None:
        """Test `$defs` field with explicit alias."""
        raw: dict[str, Any] = {
            "$defs": {"User": {"type": "object"}},
        }
        schema = Schema.model_validate(raw)
        assert "User" in schema.defs
        dumped: dict[str, Any] = schema.model_dump()
        assert "$defs" in dumped

    def test_numeric_constraints(self) -> None:
        """Test numeric validation fields serialize to camelCase."""
        schema = Schema(
            multiple_of=0.5,
            minimum=0,
            maximum=100,
            exclusive_minimum=0,
            exclusive_maximum=100,
        )
        dumped: dict[str, Any] = schema.model_dump()
        assert dumped == snapshot(
            {
                "multipleOf": 0.5,
                "minimum": 0,
                "maximum": 100,
                "exclusiveMinimum": 0,
                "exclusiveMaximum": 100,
            }
        )

    def test_array_constraints(self) -> None:
        """Test array validation fields serialize to camelCase."""
        schema = Schema(
            type=DataType.ARRAY,
            min_items=1,
            max_items=10,
        )
        dumped: dict[str, Any] = schema.model_dump()
        assert dumped == snapshot({"type": "array", "minItems": 1, "maxItems": 10})

    def test_nested_properties(self) -> None:
        """Test nested object with properties and required."""
        schema = Schema(
            type=DataType.OBJECT,
            properties={
                "name": Schema(type=DataType.STRING),
            },
            required=["name"],
        )
        dumped: dict[str, Any] = schema.model_dump()
        assert dumped == snapshot(
            {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            }
        )

    def test_additional_properties(self) -> None:
        """Test `additionalProperties` parsed from camelCase."""
        schema = Schema.model_validate(
            {
                "type": "object",
                "additionalProperties": False,
            }
        )
        assert schema.additional_properties is False

    def test_composition_any_of(self) -> None:
        """Test `anyOf` composition."""
        schema = Schema.model_validate(
            {
                "anyOf": [{"type": "string"}, {"type": "integer"}],
            }
        )
        assert len(schema.any_of) == len(["string", "integer"])

    def test_composition_one_of(self) -> None:
        """Test `oneOf` composition."""
        schema = Schema.model_validate(
            {
                "oneOf": [{"type": "string"}, {"type": "null"}],
            }
        )
        assert len(schema.one_of) == len(["string", "null"])

    def test_metadata_fields(self) -> None:
        """Test metadata fields: `title`, `description`, `default`, `examples`."""
        schema = Schema(
            title="User",
            description="A user object",
            default="test",
            examples=["example1"],
        )
        dumped: dict[str, Any] = schema.model_dump()
        assert dumped == snapshot(
            {
                "title": "User",
                "description": "A user object",
                "default": "test",
                "examples": ["example1"],
            }
        )

    def test_enum_field(self) -> None:
        """Test `enum` field."""
        schema = Schema(enum=["a", "b", "c"])
        dumped: dict[str, Any] = schema.model_dump()
        assert dumped == snapshot({"enum": ["a", "b", "c"]})

    def test_const_field(self) -> None:
        """Test `const` field."""
        schema = Schema(const="fixed")
        dumped: dict[str, Any] = schema.model_dump()
        assert dumped == snapshot({"const": "fixed"})

    def test_format_field(self) -> None:
        """Test `format` field."""
        schema = Schema(type=DataType.STRING, format="email")
        dumped: dict[str, Any] = schema.model_dump()
        assert dumped == snapshot({"type": "string", "format": "email"})

    def test_extra_fields_pass_through(self) -> None:
        """Test that unknown keywords are preserved via `extra="allow"`."""
        schema = Schema.model_validate({"type": "string", "x-custom": True})
        dumped: dict[str, Any] = schema.model_dump()
        assert dumped["x-custom"] is True

    def test_items_field(self) -> None:
        """Test `items` parsed as nested `Schema`."""
        schema = Schema.model_validate(
            {
                "type": "array",
                "items": {"type": "string"},
            }
        )
        assert isinstance(schema.items, Schema)

    def test_multi_type(self) -> None:
        """Test `type` as a list of types."""
        schema = Schema.model_validate({"type": ["string", "null"]})
        assert isinstance(schema.type, list)
        assert len(schema.type) == len(["string", "null"])
