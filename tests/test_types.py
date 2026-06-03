"""Tests for `Schema` and `Reference` serialization."""

from typing import TYPE_CHECKING

from pydantic_jsonschema.types import DataType, Reference, Schema

if TYPE_CHECKING:
    from tests.conftest import SchemaRaw


class TestSchemaSerialization:
    """Tests for Schema serialization with None-stripping."""

    def test_undefined_fields_not_dumped(self) -> None:
        """Test that fields not explicitly set are stripped from dump output."""
        schema = Schema(type=DataType.STRING)
        dumped: dict[str, object] = schema.model_dump()

        assert dumped == {"type": DataType.STRING}
        assert "description" not in dumped
        assert "title" not in dumped
        assert "properties" not in dumped
        assert "items" not in dumped
        assert "minimum" not in dumped

    def test_only_set_fields_dumped(self) -> None:
        """Test that only explicitly provided fields appear in dump."""
        schema = Schema(
            type=DataType.OBJECT,
            description="A user object",
        )
        dumped: dict[str, object] = schema.model_dump()

        assert dumped == {
            "type": DataType.OBJECT,
            "description": "A user object",
        }

    def test_nested_none_stripping(self) -> None:
        """Test that None values are stripped recursively in nested schemas."""
        schema = Schema(
            type=DataType.OBJECT,
            properties={
                "name": Schema(type=DataType.STRING),
                "age": Schema(type=DataType.INTEGER, minimum=0),
            },
        )
        dumped: dict[str, object] = schema.model_dump()

        assert dumped == {
            "type": DataType.OBJECT,
            "properties": {
                "name": {"type": DataType.STRING},
                "age": {"type": DataType.INTEGER, "minimum": 0},
            },
        }

    def test_model_validate_roundtrip(self) -> None:
        """Test that Schema roundtrips through model_validate without adding None fields."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
            },
            "required": ["name"],
        }
        schema = Schema.model_validate(schema_raw)
        dumped: dict[str, object] = schema.model_dump()

        assert "title" not in dumped
        assert "description" not in dumped
        assert "items" not in dumped
        assert "minimum" not in dumped

    def test_empty_schema_dumps_empty(self) -> None:
        """Test that a Schema with no fields set dumps to empty dict."""
        schema = Schema()
        dumped: dict[str, object] = schema.model_dump()

        assert dumped == {}


class TestReferenceSerialization:
    """Tests for Reference serialization."""

    def test_ref_key_is_dollar_ref(self) -> None:
        """Test that Reference serializes with `$ref` key (not `ref`)."""
        ref = Reference.model_validate({"$ref": "#/$defs/User"})
        dumped: dict[str, object] = ref.model_dump()

        assert "$ref" in dumped
        assert "ref" not in dumped
        assert dumped["$ref"] == "#/$defs/User"

    def test_ref_json_key_is_dollar_ref(self) -> None:
        """Test that Reference JSON output uses `$ref` key."""
        ref = Reference.model_validate({"$ref": "#/$defs/Address"})
        json_str: str = ref.model_dump_json()

        assert '"$ref"' in json_str
        assert '"ref"' not in json_str
        assert "#/$defs/Address" in json_str

    def test_ref_none_fields_stripped(self) -> None:
        """Test that Reference strips None fields on serialization."""
        ref = Reference.model_validate({"$ref": "#/$defs/Item"})
        dumped: dict[str, object] = ref.model_dump()

        assert dumped == {"$ref": "#/$defs/Item"}
        assert "summary" not in dumped
        assert "description" not in dumped
