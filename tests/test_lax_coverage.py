"""Coverage tests for LaxSchemaConverter edge cases."""

from pydantic_jsonschema import LaxSchemaConverter, Schema


def test_lax_root_model() -> None:
    """Test lax converter with RootModel (non-object type)."""
    schema = Schema.model_validate({"type": "string"})
    converter = LaxSchemaConverter()
    Model = converter.convert_schema(schema)
    instance = Model.model_validate(123)  # int -> str coercion
    assert instance.root == "123"


def test_lax_model_cache() -> None:
    """Test that lax converter caches models correctly."""
    schema = Schema.model_validate({
        "type": "object",
        "properties": {"value": {"type": "string"}},
    })
    converter = LaxSchemaConverter()
    Model1 = converter.convert_schema(schema)
    Model2 = converter.convert_schema(schema)
    assert Model1 is Model2  # Same schema should return cached model
