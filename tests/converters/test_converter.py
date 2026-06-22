"""Tests for core JSON Schema to Pydantic model conversion."""

from typing import TYPE_CHECKING, Any

import pytest
from inline_snapshot import snapshot
from pydantic import BaseModel, ValidationError

from pydantic_jsonschema import (
    SchemaConverter,
    to_model,
)
from pydantic_jsonschema.exceptions import SchemaConversionError
from pydantic_jsonschema.types import Schema

if TYPE_CHECKING:
    from tests.conftest import SchemaRaw

__all__: list[str] = []


class TestBasicConversion:
    """Tests for basic schema conversion."""

    def test_simple_object_schema(self) -> None:
        """Test converting simple object schema."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
            },
            "required": ["name"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        instance = model(name="Alice", age=30)
        assert instance.model_dump() == snapshot(
            {
                "name": "Alice",
                "age": 30,
            }
        )

        instance = model(name="Bob")
        assert instance.model_dump() == snapshot({"name": "Bob"})

        with pytest.raises(ValidationError):
            model(age=25)

    def test_array_schema(self) -> None:
        """Test array schema conversion."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": ["tags"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        instance = model(tags=["python", "dev"])
        assert instance.model_dump() == snapshot(
            {
                "tags": ["python", "dev"],
            }
        )

    def test_nested_objects(self) -> None:
        """Test nested object schemas."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "user": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                    },
                    "required": ["name"],
                },
            },
            "required": ["user"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        instance = model(user={"name": "Alice"})
        assert instance.model_dump() == snapshot(
            {
                "user": {"name": "Alice"},
            }
        )

    def test_deeply_nested_objects(self) -> None:
        """Test deeply nested object structures."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "level1": {
                    "type": "object",
                    "properties": {
                        "level2": {
                            "type": "object",
                            "properties": {
                                "value": {"type": "integer"},
                            },
                            "required": ["value"],
                        },
                    },
                    "required": ["level2"],
                },
            },
            "required": ["level1"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        instance = model(level1={"level2": {"value": 42}})
        assert instance.model_dump() == snapshot(
            {
                "level1": {
                    "level2": {
                        "value": 42,
                    },
                },
            }
        )

    def test_schema_without_type(self) -> None:
        """Test schema without type accepts any value."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "anything": {},
            },
            "required": ["anything"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        instance = model(anything="string")
        assert instance.model_dump() == snapshot(
            {
                "anything": "string",
            }
        )

        instance = model(anything=123)
        assert instance.model_dump() == snapshot(
            {
                "anything": 123,
            }
        )

    def test_multiple_type_union(self) -> None:
        """Test schema with multiple types."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "value": {"type": ["string", "integer", "null"]},
            },
            "required": ["value"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        instance = model(value="text")
        assert instance.model_dump() == snapshot({"value": "text"})

        instance = model(value=42)
        assert instance.model_dump() == snapshot({"value": 42})

        instance = model(value=None)
        assert instance.model_dump() == snapshot({"value": None})

    def test_multiple_type_union_with_object(self) -> None:
        """Test multi-type union including `object` still rejects unlisted types."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "value": {"type": ["object", "string"]},
            },
            "required": ["value"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        instance = model(value={"key": 1})
        assert instance.model_dump() == snapshot({"value": {"key": 1}})

        instance = model(value="text")
        assert instance.model_dump() == snapshot({"value": "text"})

        with pytest.raises(ValidationError):
            model(value=42)

    def test_array_without_items_schema(self) -> None:
        """Test array without items schema accepts any element types."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "data": {"type": "array"},
            },
            "required": ["data"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        instance = model(data=[1, "two", 3.0, True, None])
        assert instance.model_dump() == snapshot(
            {
                "data": [1, "two", 3.0, True, None],
            }
        )


class TestRootModels:
    """Tests for `RootModel` creation from non-object root schemas."""

    def test_root_model_for_array_type(self) -> None:
        """Test RootModel creation for array type schemas."""
        schema_raw: SchemaRaw = {
            "type": "array",
            "items": {"type": "string"},
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        instance = model(["item1", "item2", "item3"])  # type: ignore[call-arg]
        assert instance.model_dump() == snapshot(["item1", "item2", "item3"])

    def test_root_model_for_string_type(self) -> None:
        """Test RootModel creation for string type schemas."""
        schema_raw: SchemaRaw = {
            "type": "string",
            "minLength": 5,
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        instance = model("hello world")  # type: ignore[call-arg]
        assert instance.model_dump() == snapshot("hello world")

        with pytest.raises(ValidationError):
            model("hi")  # type: ignore[call-arg]

        # Root value has no "absent" concept -> required.
        with pytest.raises(ValidationError):
            model()

    def test_root_model_for_integer_type(self) -> None:
        """Test RootModel creation for integer type schemas."""
        schema_raw: SchemaRaw = {
            "type": "integer",
            "minimum": 0,
            "maximum": 100,
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        valid_value = 42
        instance = model(valid_value)  # type: ignore[call-arg]
        assert instance.model_dump() == valid_value  # type: ignore[comparison-overlap]

        invalid_value = -1
        with pytest.raises(ValidationError):
            model(invalid_value)  # type: ignore[call-arg]

        invalid_value = 101
        with pytest.raises(ValidationError):
            model(invalid_value)  # type: ignore[call-arg]

    def test_root_model_with_allof(self) -> None:
        """Test RootModel with allOf."""
        schema_raw: SchemaRaw = {
            "allOf": [
                {"type": "string", "minLength": 5},
            ],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        instance = model("hello world")  # type: ignore[call-arg]
        assert instance.model_dump() == snapshot("hello world")

    def test_root_additional_properties_typed_validation(self) -> None:
        """Test root object with schema-valued `additionalProperties` validates value types."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "additionalProperties": {"type": "integer"},
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        instance = model({"count": 42, "total": 100})  # type: ignore[call-arg]
        assert instance.model_dump() == snapshot(
            {
                "count": 42,
                "total": 100,
            }
        )

        with pytest.raises(ValidationError):
            model({"count": "not-an-integer"})  # type: ignore[call-arg]

    def test_root_additional_properties_with_ref(self) -> None:
        """Test root object with `$ref`-valued `additionalProperties`."""
        schema_raw: SchemaRaw = {
            "$defs": {
                "Item": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                    },
                    "required": ["name"],
                },
            },
            "type": "object",
            "additionalProperties": {"$ref": "#/$defs/Item"},
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        instance = model({"first": {"name": "A"}, "second": {"name": "B"}})  # type: ignore[call-arg]
        assert instance.model_dump() == snapshot(
            {
                "first": {"name": "A"},
                "second": {"name": "B"},
            }
        )

        with pytest.raises(ValidationError):
            model({"first": "not-an-item"})  # type: ignore[call-arg]


class TestLiteralTypes:
    """Tests for `enum` / `const` conversion to `Literal`."""

    @pytest.mark.parametrize(
        ("schema_field", "valid_value", "invalid_value"),
        [
            pytest.param(
                {"enum": ["active", "inactive", "pending"]},
                "active",
                "invalid",
                id="enum",
            ),
            pytest.param(
                {"const": "fixed_value"},
                "fixed_value",
                "wrong_value",
                id="const",
            ),
            pytest.param(
                {"const": None},
                None,
                "not-null",
                id="const-null",
            ),
        ],
    )
    def test_literal_types(
        self,
        schema_field: dict[str, Any],
        valid_value: str | None,
        invalid_value: str,
    ) -> None:
        """Test enum and const conversion to Literal."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {"field": schema_field},
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        instance = model(field=valid_value)
        assert instance.model_dump() == {"field": valid_value}

        with pytest.raises(ValidationError):
            model(field=invalid_value)

    def test_empty_enum_raises_conversion_error(self) -> None:
        """An empty `enum` raises a clean `SchemaConversionError`, not a bare `AssertionError`."""
        with pytest.raises(SchemaConversionError) as exc_info:
            to_model(Schema.model_validate({"enum": []}))
        assert str(exc_info.value) == snapshot(
            "SchemaConversionError(message='`enum` must contain at least one value')"
        )


class TestAdditionalProperties:
    """Tests for `additionalProperties` handling."""

    def test_dict_with_additional_properties_schema(self) -> None:
        """Test dict with typed additionalProperties."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "metadata": {"type": "object", "additionalProperties": {"type": "integer"}},
            },
            "required": ["metadata"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        instance = model(metadata={"count": 42, "total": 100})
        assert instance.model_dump() == snapshot(
            {
                "metadata": {"count": 42, "total": 100},
            }
        )

    def test_dict_with_false_additional_properties(self) -> None:
        """Test object creation with additionalProperties: false."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "data": {"type": "object", "additionalProperties": False},
            },
            "required": ["data"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        instance = model(data={})
        assert instance.model_dump() == snapshot({"data": {}})

        with pytest.raises(ValidationError):
            model(data={"extra": "field"})

    def test_additional_properties_true(self) -> None:
        """Test additionalProperties: true allows any values."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "data": {
                    "type": "object",
                    "additionalProperties": True,
                },
            },
            "required": ["data"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        instance = model(data={"a": 1, "b": "text", "c": [1, 2, 3]})
        assert instance.model_dump() == snapshot(
            {
                "data": {"a": 1, "b": "text", "c": [1, 2, 3]},
            }
        )

    def test_additional_properties_forbid(self) -> None:
        """Test that additionalProperties: false forbids extra fields."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "additionalProperties": False,
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        instance = model(name="Alice")
        assert instance.model_dump() == snapshot({"name": "Alice"})

        with pytest.raises(ValidationError):
            model(name="Alice", extra="field")

    def test_additional_properties_allow(self) -> None:
        """Test that additionalProperties allows extra fields."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "additionalProperties": True,
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        instance = model(name="Alice", extra="allowed")
        assert instance.model_dump() == snapshot(
            {
                "name": "Alice",
                "extra": "allowed",
            }
        )

    def test_additional_properties_with_schema(self) -> None:
        """Test additionalProperties with schema definition."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
            },
            "required": ["name"],
            "additionalProperties": {
                "type": "integer",
            },
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        instance = model(name="test", extra1=10, extra2=20)
        assert instance.model_dump() == snapshot(
            {
                "name": "test",
                "extra1": 10,
                "extra2": 20,
            }
        )

    def test_property_names_pattern(self) -> None:
        """Test propertyNames with pattern."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "propertyNames": {
                "pattern": "^[a-z_]+$",
            },
            "additionalProperties": {"type": "string"},
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        instance = model({"valid_name": "test", "another_name": "value"})  # type: ignore[call-arg]
        assert instance.model_dump() == snapshot(
            {
                "valid_name": "test",
                "another_name": "value",
            }
        )


class TestConverterCaching:
    """Tests for model caching in converter."""

    def test_same_schema_returns_cached_model(self) -> None:
        """Test that converting the same schema twice returns cached model."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
            },
            "required": ["name"],
        }

        converter = SchemaConverter()
        schema1 = Schema.model_validate(schema_raw)
        schema2 = Schema.model_validate(schema_raw)

        model1 = converter.convert_schema(schema1)
        model2 = converter.convert_schema(schema2)

        assert model1 is model2

    def test_different_schemas_return_different_models(self) -> None:
        """Test that different schemas return different models."""
        schema_raw1 = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
            },
            "required": ["name"],
        }

        schema_raw2 = {
            "type": "object",
            "properties": {
                "age": {"type": "integer"},
            },
            "required": ["age"],
        }

        converter = SchemaConverter()
        schema1 = Schema.model_validate(schema_raw1)
        schema2 = Schema.model_validate(schema_raw2)

        model1 = converter.convert_schema(schema1)
        model2 = converter.convert_schema(schema2)

        assert model1 is not model2

    def test_ref_model_cached_in_get_model(self) -> None:
        """Test that `_get_model` properly caches resolved reference models."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "$defs": {
                "User": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "age": {"type": "integer"},
                    },
                    "required": ["name"],
                },
            },
            "properties": {
                "user1": {"$ref": "#/$defs/User"},
                "user2": {"$ref": "#/$defs/User"},
            },
            "required": ["user1", "user2"],
        }

        converter = SchemaConverter()
        schema = Schema.model_validate(schema_raw)
        model = converter.convert_schema(schema)

        # `required` keeps the bare model annotation: both fields share the `$ref`
        # cache, so the annotation is the same model object. Optional fields would
        # wrap it as `User | MISSING`, whose identity is not stable across Python
        # versions (`X | Y` is no longer interned on 3.15+), making `is` fail there.
        assert model.model_fields["user1"].annotation is model.model_fields["user2"].annotation

    def test_model_generation_with_uncached_ref(self) -> None:
        """Test model generation fallback when ref exists but model not yet cached.

        This tests the fallback path in _get_model through a controlled scenario
        using a custom converter subclass that simulates the uncached state.
        """

        class TestableConverter(SchemaConverter):
            """Converter that allows testing of model generation fallback."""

            def trigger_uncached_ref_scenario(self) -> type[BaseModel]:
                """Simulate scenario where ref exists in defs_cache but model not cached."""
                test_schema = Schema(type="object", properties={"value": Schema(type="string")})
                ref = "#/$defs/TestType"
                self._defs_cache[ref] = test_schema
                return self._get_model(ref)

        converter = TestableConverter()
        model = converter.trigger_uncached_ref_scenario()

        instance = model(value="test")
        assert instance.model_dump() == snapshot({"value": "test"})
