"""Tests for `_schema.py` JSON Schema models."""

from typing import TYPE_CHECKING, Any

import pytest
from inline_snapshot import snapshot

from pydantic_jsonschema._schema import DataType, Reference, Schema

if TYPE_CHECKING:
    from tests.conftest import SchemaRaw

__all__: list[str] = []


class TestDataType:
    """Tests for `DataType` enum."""

    @pytest.mark.parametrize(
        ("member", "value"),
        [
            pytest.param(DataType.NULL, "null", id="null"),
            pytest.param(DataType.STRING, "string", id="string"),
            pytest.param(DataType.NUMBER, "number", id="number"),
            pytest.param(DataType.INTEGER, "integer", id="integer"),
            pytest.param(DataType.BOOLEAN, "boolean", id="boolean"),
            pytest.param(DataType.ARRAY, "array", id="array"),
            pytest.param(DataType.OBJECT, "object", id="object"),
        ],
    )
    def test_values(self, member: DataType, value: str) -> None:
        """Test enum members have correct string values."""
        assert member == value
        assert str(member) == value


class TestReference:
    """Tests for `Reference` parsing and serialization."""

    def test_model_validate(self) -> None:
        """Test parsing from JSON Schema `$ref` dict."""
        ref = Reference.model_validate({"$ref": "#/$defs/User"})
        assert ref == snapshot(Reference(ref="#/$defs/User"))

    def test_serialize_by_alias(self) -> None:
        """Test serialization uses `$ref` key."""
        ref = Reference(ref="#/$defs/User")
        dumped: dict[str, Any] = ref.model_dump()
        assert dumped == snapshot({"$ref": "#/$defs/User"})

    def test_json_by_alias(self) -> None:
        """Test JSON output uses `$ref` key."""
        ref = Reference(ref="#/$defs/User")
        json_str: str = ref.model_dump_json()
        assert json_str == snapshot('{"$ref":"#/$defs/User"}')


class TestSchemaTypes:
    """Tests for the `type` keyword parsing."""

    def test_simple_type(self) -> None:
        """Test single-type schema."""
        schema = Schema(type=DataType.STRING)
        dumped: dict[str, Any] = schema.model_dump()
        assert dumped == snapshot({"type": "string"})

    def test_multi_type(self) -> None:
        """Test `type` as a list of types."""
        schema = Schema.model_validate({"type": ["string", "null"]})
        assert schema.model_dump() == snapshot({"type": [DataType.STRING, DataType.NULL]})

    def test_items_field(self) -> None:
        """Test `items` parsed as nested `Schema`."""
        schema = Schema.model_validate(
            {
                "type": "array",
                "items": {"type": "string"},
            }
        )
        assert isinstance(schema.items, Schema)
        assert schema.model_dump() == snapshot(
            {
                "type": DataType.ARRAY,
                "items": {"type": DataType.STRING},
            }
        )


class TestSchemaObjects:
    """Tests for object-related keywords."""

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
        assert schema.model_dump() == snapshot(
            {
                "type": DataType.OBJECT,
                "additionalProperties": False,
            }
        )

    def test_defs_alias(self) -> None:
        """Test `$defs` field with explicit alias."""
        raw: dict[str, Any] = {
            "$defs": {"User": {"type": "object"}},
        }
        schema = Schema.model_validate(raw)
        dumped: dict[str, Any] = schema.model_dump()
        assert dumped == snapshot(
            {
                "$defs": {
                    "User": {"type": DataType.OBJECT},
                },
            }
        )


class TestSchemaComposition:
    """Tests for `allOf` / `anyOf` / `oneOf` composition keywords."""

    def test_all_of(self) -> None:
        """Test `allOf` parsed and serialized back to camelCase."""
        schema = Schema.model_validate({"allOf": [{"$ref": "#/$defs/Base"}]})
        dumped: dict[str, Any] = schema.model_dump()
        assert dumped == snapshot({"allOf": [{"$ref": "#/$defs/Base"}]})

    def test_any_of(self) -> None:
        """Test `anyOf` composition."""
        schema = Schema.model_validate(
            {
                "anyOf": [{"type": "string"}, {"type": "integer"}],
            }
        )
        assert schema.model_dump() == snapshot(
            {
                "anyOf": [
                    {"type": DataType.STRING},
                    {"type": DataType.INTEGER},
                ],
            }
        )

    def test_one_of(self) -> None:
        """Test `oneOf` composition."""
        schema = Schema.model_validate(
            {
                "oneOf": [{"type": "string"}, {"type": "null"}],
            }
        )
        assert schema.model_dump() == snapshot(
            {
                "oneOf": [
                    {"type": DataType.STRING},
                    {"type": DataType.NULL},
                ],
            }
        )


class TestSchemaConstraints:
    """Tests for numeric / array constraint keywords."""

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

    def test_string_constraints(self) -> None:
        """Test string validation fields, including `pattern`."""
        schema = Schema(
            type=DataType.STRING,
            min_length=1,
            max_length=20,
            pattern="^[a-z]+$",
        )
        dumped: dict[str, Any] = schema.model_dump()
        assert dumped == snapshot(
            {
                "type": "string",
                "minLength": 1,
                "maxLength": 20,
                "pattern": "^[a-z]+$",
            }
        )


class TestSchemaMetadata:
    """Tests for metadata and annotation keywords."""

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
        assert dumped == snapshot({"type": DataType.STRING, "x-custom": True})


class TestSchemaSerialization:
    """Tests for dump behavior: aliases and unset-field stripping."""

    def test_empty_schema(self) -> None:
        """Test empty schema dumps to empty dict."""
        schema = Schema()
        dumped: dict[str, Any] = schema.model_dump()
        assert dumped == snapshot({})

    def test_populate_by_name(self) -> None:
        """Test that fields can be set using Python names."""
        schema = Schema(min_length=5, max_length=10)
        dumped: dict[str, Any] = schema.model_dump()
        assert dumped == snapshot({"minLength": 5, "maxLength": 10})

    def test_only_set_fields_dumped(self) -> None:
        """Test that only explicitly provided fields appear in dump."""
        schema = Schema(
            type=DataType.OBJECT,
            description="A user object",
        )
        dumped: dict[str, Any] = schema.model_dump()
        assert dumped == snapshot(
            {
                "type": DataType.OBJECT,
                "description": "A user object",
            }
        )

    def test_nested_unset_stripping(self) -> None:
        """Test that unset fields are stripped recursively in nested schemas."""
        schema = Schema(
            type=DataType.OBJECT,
            properties={
                "name": Schema(type=DataType.STRING),
                "age": Schema(type=DataType.INTEGER, minimum=0),
            },
        )
        dumped: dict[str, Any] = schema.model_dump()
        assert dumped == snapshot(
            {
                "type": DataType.OBJECT,
                "properties": {
                    "name": {"type": DataType.STRING},
                    "age": {"type": DataType.INTEGER, "minimum": 0.0},
                },
            }
        )

    def test_model_validate_roundtrip(self) -> None:
        """Test that `Schema` roundtrips through `model_validate` without adding unset fields."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
            },
            "required": ["name"],
        }
        schema = Schema.model_validate(schema_raw)
        dumped: dict[str, Any] = schema.model_dump()
        assert dumped == snapshot(
            {
                "type": DataType.OBJECT,
                "properties": {"name": {"type": DataType.STRING}},
                "required": ["name"],
            }
        )


class TestSchemaArrayKeywords:
    """Tests for array applicator / constraint keywords."""

    def test_prefix_items(self) -> None:
        """Test `prefixItems` parsed as a list of nested `Schema`."""
        schema = Schema.model_validate(
            {
                "type": "array",
                "prefixItems": [{"type": "string"}, {"type": "integer"}],
            }
        )
        assert all(isinstance(item, Schema) for item in schema.prefix_items)
        assert schema.model_dump() == snapshot(
            {
                "type": DataType.ARRAY,
                "prefixItems": [{"type": DataType.STRING}, {"type": DataType.INTEGER}],
            }
        )

    def test_contains(self) -> None:
        """Test `contains` parsed as a nested `Schema`."""
        schema = Schema.model_validate({"type": "array", "contains": {"type": "integer"}})
        assert isinstance(schema.contains, Schema)
        assert schema.model_dump() == snapshot(
            {
                "type": DataType.ARRAY,
                "contains": {"type": DataType.INTEGER},
            }
        )

    def test_unique_items(self) -> None:
        """Test `uniqueItems` parsed from camelCase."""
        schema = Schema.model_validate({"type": "array", "uniqueItems": True})
        assert schema.model_dump() == snapshot({"type": DataType.ARRAY, "uniqueItems": True})


class TestSchemaObjectKeywords:
    """Tests for object applicator / constraint keywords."""

    def test_pattern_properties(self) -> None:
        """Test `patternProperties` parsed as nested schemas keyed by regex."""
        schema = Schema.model_validate(
            {
                "type": "object",
                "patternProperties": {"^x-": {"type": "string"}},
            }
        )
        assert isinstance(schema.pattern_properties["^x-"], Schema)
        assert schema.model_dump() == snapshot(
            {
                "type": DataType.OBJECT,
                "patternProperties": {"^x-": {"type": DataType.STRING}},
            }
        )

    def test_min_max_properties(self) -> None:
        """Test `minProperties` / `maxProperties` parsed from camelCase."""
        schema = Schema.model_validate(
            {
                "type": "object",
                "minProperties": 1,
                "maxProperties": 5,
            }
        )
        assert schema.model_dump() == snapshot(
            {
                "type": DataType.OBJECT,
                "minProperties": 1,
                "maxProperties": 5,
            }
        )

    def test_dependent_required(self) -> None:
        """Test `dependentRequired` parsed as a property-to-names mapping."""
        schema = Schema.model_validate(
            {
                "type": "object",
                "dependentRequired": {"credit_card": ["billing_address"]},
            }
        )
        assert schema.model_dump() == snapshot(
            {
                "type": DataType.OBJECT,
                "dependentRequired": {"credit_card": ["billing_address"]},
            }
        )

    def test_dependent_schemas(self) -> None:
        """Test `dependentSchemas` parsed as nested schemas keyed by property name."""
        schema = Schema.model_validate(
            {
                "type": "object",
                "dependentSchemas": {"credit_card": {"required": ["billing_address"]}},
            }
        )
        assert isinstance(schema.dependent_schemas["credit_card"], Schema)
        assert schema.model_dump() == snapshot(
            {
                "type": DataType.OBJECT,
                "dependentSchemas": {"credit_card": {"required": ["billing_address"]}},
            }
        )


class TestSchemaConditionalKeywords:
    """Tests for the conditional / negation keywords with reserved-word aliases."""

    def test_if_then_else_and_not_by_alias(self) -> None:
        """Test `if` / `then` / `else` / `not` parsed as typed nested schemas via aliases."""
        schema = Schema.model_validate(
            {
                "type": "integer",
                "if": {"minimum": 0},
                "then": {"maximum": 9},
                "else": {"maximum": -1},
                "not": {"const": 5},
            }
        )
        assert isinstance(schema.if_, Schema)
        assert isinstance(schema.then, Schema)
        assert isinstance(schema.else_, Schema)
        assert isinstance(schema.not_, Schema)
        assert schema.model_dump() == snapshot(
            {
                "type": DataType.INTEGER,
                "not": {"const": 5},
                "if": {"minimum": 0.0},
                "then": {"maximum": 9.0},
                "else": {"maximum": -1.0},
            }
        )

    def test_populate_by_python_name(self) -> None:
        """Test the reserved-word fields also load by their Python names (`populate_by_name`)."""
        schema = Schema(
            if_=Schema(minimum=0),
            then=Schema(maximum=9),
            else_=Schema(maximum=-1),
            not_=Schema(const=5),
        )
        assert schema.model_dump() == snapshot(
            {
                "not": {"const": 5},
                "if": {"minimum": 0.0},
                "then": {"maximum": 9.0},
                "else": {"maximum": -1.0},
            }
        )
