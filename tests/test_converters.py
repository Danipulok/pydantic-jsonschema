from typing import Annotated, Any

import pytest
from pydantic import BaseModel, ValidationError
from pydantic.functional_validators import AfterValidator, BeforeValidator

from pydantic_jsonschema import SchemaConverter, to_lax_model, to_model
from pydantic_jsonschema.exceptions import SchemaConvertionError, SchemaReferenceError
from pydantic_jsonschema.types import Schema
from tests.conftest import SchemaRaw


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
        Model = to_model(schema)

        # Valid instance
        instance = Model(name="Alice", age=30)
        assert instance.model_dump() == {
            "name": "Alice",
            "age": 30,
        }

        # Missing optional field
        instance = Model(name="Bob")
        assert instance.model_dump() == {
            "name": "Bob",
            "age": None,
        }

        # Missing required field
        with pytest.raises(ValidationError):
            Model(age=25)

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
        }
        schema = Schema.model_validate(schema_raw)
        Model = to_model(schema)

        instance = Model(tags=["python", "dev"])
        assert instance.model_dump() == {
            "tags": ["python", "dev"],
        }

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
                },
            },
        }
        schema = Schema.model_validate(schema_raw)
        Model = to_model(schema)

        instance = Model(user={"name": "Alice"})
        assert instance.model_dump() == {
            "user": {"name": "Alice"},
        }

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
                        },
                    },
                },
            },
        }
        schema = Schema.model_validate(schema_raw)
        Model = to_model(schema)

        instance = Model(level1={"level2": {"value": 42}})
        assert instance.model_dump() == {
            "level1": {
                "level2": {
                    "value": 42,
                },
            },
        }

    def test_schema_without_type(self) -> None:
        """Test schema without type accepts any value."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "anything": {},
            },
        }
        schema = Schema.model_validate(schema_raw)
        Model = to_model(schema)

        instance = Model(anything="string")
        assert instance.model_dump() == {
            "anything": "string",
        }

        instance = Model(anything=123)
        assert instance.model_dump() == {
            "anything": 123,
        }


class TestReferences:
    """Tests for $defs and $ref support."""

    def test_nested_definition(self) -> None:
        """Test nested schema definitions."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "address": {
                    "type": "object",
                    "properties": {
                        "street": {"type": "string"},
                        "city": {"type": "string"},
                    },
                },
            },
        }
        schema = Schema.model_validate(schema_raw)
        Model = to_model(schema)

        instance = Model(address={"street": "Main St", "city": "NYC"})
        assert instance.model_dump() == {
            "address": {
                "street": "Main St",
                "city": "NYC",
            },
        }

    def test_defs_with_single_reference(self) -> None:
        """Test schema with $defs containing one definition."""
        schema_raw: SchemaRaw = {
            "$defs": {
                "Address": {
                    "type": "object",
                    "properties": {
                        "street": {"type": "string"},
                        "city": {"type": "string"},
                    },
                    "required": ["street"],
                },
            },
            "type": "object",
            "properties": {
                "home": {"$ref": "#/$defs/Address"},
            },
        }
        schema = Schema.model_validate(schema_raw)
        Model = to_model(schema)

        instance = Model(home={"street": "Main St", "city": "NYC"})
        assert instance.model_dump() == {
            "home": {
                "street": "Main St",
                "city": "NYC",
            },
        }

    def test_defs_with_multiple_references(self) -> None:
        """Test schema with multiple $defs."""
        schema_raw: SchemaRaw = {
            "$defs": {
                "Person": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "age": {"type": "integer"},
                    },
                },
                "Address": {
                    "type": "object",
                    "properties": {
                        "street": {"type": "string"},
                    },
                },
                "Company": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                    },
                },
            },
            "type": "object",
            "properties": {
                "owner": {"$ref": "#/$defs/Person"},
                "address": {"$ref": "#/$defs/Address"},
                "employer": {"$ref": "#/$defs/Company"},
            },
        }
        schema = Schema.model_validate(schema_raw)
        Model = to_model(schema)

        instance = Model(
            owner={"name": "Alice", "age": 30},
            address={"street": "Main St"},
            employer={"name": "ACME Corp"},
        )
        assert instance.model_dump() == {
            "owner": {"name": "Alice", "age": 30},
            "address": {"street": "Main St"},
            "employer": {"name": "ACME Corp"},
        }

    def test_nested_ref_resolution(self) -> None:
        """Test nested reference resolution."""
        schema_raw: SchemaRaw = {
            "$defs": {
                "City": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                    },
                },
                "Address": {
                    "type": "object",
                    "properties": {
                        "street": {"type": "string"},
                        "city": {"$ref": "#/$defs/City"},
                    },
                },
            },
            "type": "object",
            "properties": {
                "home": {"$ref": "#/$defs/Address"},
            },
        }
        schema = Schema.model_validate(schema_raw)
        Model = to_model(schema)

        instance = Model(home={"street": "Main St", "city": {"name": "NYC"}})
        assert instance.model_dump() == {
            "home": {
                "street": "Main St",
                "city": {"name": "NYC"},
            },
        }

    def test_invalid_reference_error(self) -> None:
        """Test invalid reference raises error."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "field": {"$ref": "#/$defs/DoesNotExist"},
            },
        }
        schema = Schema.model_validate(schema_raw)

        with pytest.raises(
            SchemaReferenceError,
            match=r"Cannot resolve reference.*DoesNotExist",
        ):
            to_model(schema)

    def test_property_with_reference(self) -> None:
        """Test property using $ref."""
        schema_raw: SchemaRaw = {
            "$defs": {
                "ContactInfo": {
                    "type": "object",
                    "properties": {
                        "email": {"type": "string", "format": "email"},
                        "phone": {"type": "string"},
                    },
                },
            },
            "type": "object",
            "properties": {
                "contact": {"$ref": "#/$defs/ContactInfo"},
            },
            "required": ["contact"],
        }
        schema = Schema.model_validate(schema_raw)
        Model = to_model(schema)

        instance = Model(contact={"email": "test@example.com", "phone": "123-456"})
        assert instance.model_dump() == {
            "contact": {
                "email": "test@example.com",
                "phone": "123-456",
            },
        }

    def test_reference_in_array(self) -> None:
        """Test reference in array items."""
        schema_raw: SchemaRaw = {
            "$defs": {
                "Item": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "value": {"type": "integer"},
                    },
                },
            },
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/Item"},
                },
            },
        }
        schema = Schema.model_validate(schema_raw)
        Model = to_model(schema)

        instance = Model(items=[{"name": "A", "value": 1}, {"name": "B", "value": 2}])
        assert instance.model_dump() == {
            "items": [
                {"name": "A", "value": 1},
                {"name": "B", "value": 2},
            ],
        }

    def test_forward_ref_namespace(self) -> None:
        """Test forward reference namespace building."""
        schema_raw: SchemaRaw = {
            "$defs": {
                "Author": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                    },
                },
                "Article": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "author": {"$ref": "#/$defs/Author"},
                    },
                },
            },
            "type": "object",
            "properties": {
                "featured": {"$ref": "#/$defs/Article"},
            },
        }
        schema = Schema.model_validate(schema_raw)
        Model = to_model(schema)

        instance = Model(featured={"title": "Test", "author": {"name": "Alice"}})
        assert instance.model_dump() == {
            "featured": {"title": "Test", "author": {"name": "Alice"}},
        }

    def test_pre_built_refs(self) -> None:
        """Test pre-built refs in converter."""

        class CustomAddress(BaseModel):
            street: str
            city: str

        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "address": {"$ref": "#/$defs/CustomAddress"},
            },
        }
        schema = Schema.model_validate(schema_raw)

        converter = SchemaConverter(
            refs={
                "#/$defs/CustomAddress": CustomAddress,
            }
        )
        Model = converter.convert_schema(schema)

        instance = Model(address={"street": "Main St", "city": "NYC"})
        assert instance.model_dump() == {
            "address": {"street": "Main St", "city": "NYC"},
        }

    def test_model_generation_with_multiple_same_refs(self) -> None:
        """Test model generation with multiple references to same type."""
        schema_raw: SchemaRaw = {
            "$defs": {
                "CustomType": {
                    "type": "object",
                    "properties": {
                        "value": {"type": "string"},
                    },
                },
            },
            "type": "object",
            "properties": {
                "field1": {"$ref": "#/$defs/CustomType"},
                "field2": {"$ref": "#/$defs/CustomType"},
            },
        }
        schema = Schema.model_validate(schema_raw)
        Model = to_model(schema)

        instance = Model(
            field1={"value": "test1"},
            field2={"value": "test2"},
        )
        assert instance.model_dump() == {
            "field1": {"value": "test1"},
            "field2": {"value": "test2"},
        }

    def test_direct_ref_access_in_array(self) -> None:
        """Test direct reference access in array items."""
        schema_raw: SchemaRaw = {
            "$defs": {
                "Item": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                    },
                },
            },
            "type": "array",
            "items": {"$ref": "#/$defs/Item"},
        }
        schema = Schema.model_validate(schema_raw)
        Model = to_model(schema)

        instance = Model([{"name": "item1"}, {"name": "item2"}])
        assert instance.model_dump() == [{"name": "item1"}, {"name": "item2"}]

    def test_forward_ref_unresolved(self) -> None:
        """Test ForwardRef creation when reference isn't resolved yet."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "anyOf": [
                            {"type": "string"},
                            {
                                "type": "object",
                                "properties": {
                                    "nested": {"type": "string"},
                                },
                            },
                        ],
                    },
                },
            },
        }
        schema = Schema.model_validate(schema_raw)
        Model = to_model(schema)

        instance = Model(items=["text", {"nested": "value"}])
        assert instance.model_dump() == {
            "items": ["text", {"nested": "value"}],
        }


class TestComposition:
    """Tests for allOf, anyOf, oneOf."""

    def test_allof_composition(self) -> None:
        """Test allOf composition."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "allOf": [
                {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                    "required": ["name"],
                },
                {
                    "type": "object",
                    "properties": {"age": {"type": "integer"}},
                },
            ],
        }
        schema = Schema.model_validate(schema_raw)
        Model = to_model(schema)

        instance = Model(name="Alice", age=30)
        assert instance.model_dump() == {
            "name": "Alice",
            "age": 30,
        }

    def test_anyof_union(self) -> None:
        """Test anyOf creates Union types."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "value": {
                    "anyOf": [
                        {"type": "string"},
                        {"type": "integer"},
                    ],
                },
            },
        }
        schema = Schema.model_validate(schema_raw)
        Model = to_model(schema)

        instance = Model(value="hello")
        assert instance.model_dump() == {"value": "hello"}

        instance = Model(value=42)
        assert instance.model_dump() == {"value": 42}

    def test_oneof_union(self) -> None:
        """Test oneOf creates Union types."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "value": {
                    "oneOf": [
                        {"type": "string"},
                        {"type": "boolean"},
                    ],
                },
            },
        }
        schema = Schema.model_validate(schema_raw)
        Model = to_model(schema)

        instance = Model(value="text")
        assert instance.model_dump() == {"value": "text"}

        instance = Model(value=True)
        assert instance.model_dump() == {"value": True}

    def test_allof_with_reference(self) -> None:
        """Test allOf with $ref."""
        schema_raw: SchemaRaw = {
            "$defs": {
                "BaseMixin": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                    },
                    "required": ["id"],
                },
            },
            "type": "object",
            "allOf": [
                {"$ref": "#/$defs/BaseMixin"},
                {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                    },
                },
            ],
        }
        schema = Schema.model_validate(schema_raw)
        Model = to_model(schema)

        instance = Model(id=1, name="Test")
        assert instance.model_dump() == {
            "id": 1,
            "name": "Test",
        }

    def test_root_model_with_allof(self) -> None:
        """Test RootModel with allOf."""
        schema_raw: SchemaRaw = {
            "allOf": [
                {"type": "string", "minLength": 5},
            ],
        }
        schema = Schema.model_validate(schema_raw)
        Model = to_model(schema)

        instance = Model("hello world")
        assert instance.model_dump() == "hello world"

    def test_allof_in_property(self) -> None:
        """Test allOf in property annotation."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "combined": {
                    "allOf": [
                        {
                            "type": "object",
                            "properties": {"a": {"type": "string"}},
                        },
                        {
                            "type": "object",
                            "properties": {"b": {"type": "integer"}},
                        },
                    ],
                },
            },
        }
        schema = Schema.model_validate(schema_raw)
        Model = to_model(schema)

        instance = Model(combined={"a": "test", "b": 42})
        assert instance.model_dump() == {
            "combined": {"a": "test", "b": 42},
        }

    def test_complex_union_types(self) -> None:
        """Test complex union type scenarios."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "multi_value": {
                    "anyOf": [
                        {"type": "string"},
                        {"type": "integer"},
                        {"type": "boolean"},
                    ],
                },
            },
        }
        schema = Schema.model_validate(schema_raw)
        Model = to_model(schema)

        instance = Model(multi_value="text")
        assert instance.model_dump() == {"multi_value": "text"}

        instance = Model(multi_value=42)
        assert instance.model_dump() == {"multi_value": 42}

        instance = Model(multi_value=True)
        assert instance.model_dump() == {"multi_value": True}


class TestLaxConversion:
    """Tests for lax conversion mode with type coercion."""

    def test_explicit_defaults_preserved(self) -> None:
        """Test that explicit defaults are preserved."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "status": {"type": "string", "default": "pending"},
            },
        }
        schema = Schema.model_validate(schema_raw)
        Model = to_lax_model(schema)

        instance = Model()
        assert instance.model_dump() == {"status": "pending"}

    def test_lax_accepts_full_data(self) -> None:
        """Test that lax mode still accepts complete data."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["name", "age"],
        }
        schema = Schema.model_validate(schema_raw)
        Model = to_lax_model(schema)

        instance = Model(name="Alice", age=30, tags=["dev", "python"])
        assert instance.model_dump() == {
            "name": "Alice",
            "age": 30,
            "tags": ["dev", "python"],
        }

    def test_lax_coerces_types(self) -> None:
        """Test that lax mode coerces types."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
            },
            "required": ["name", "age"],
        }
        schema = Schema.model_validate(schema_raw)
        Model = to_lax_model(schema)

        instance = Model(name=123, age="42")
        assert instance.model_dump() == {
            "name": "123",
            "age": 42,
        }

    def test_lax_mode_with_annotated_format_validator(self) -> None:
        """Test lax mode with Annotated type as format validator."""

        def uppercase(v: str) -> str:
            return v.upper()

        AnnotatedUpper = Annotated[str, AfterValidator(uppercase)]

        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "value": {"type": "string", "format": "upper"},
            },
            "required": ["value"],
        }
        schema = Schema.model_validate(schema_raw)
        Model = to_lax_model(schema, format_validators={"upper": AnnotatedUpper})

        instance = Model(value=123)
        assert instance.model_dump() == {"value": "123"}

    def test_lax_mode_with_nested_annotated(self) -> None:
        """Test lax mode with nested Annotated types."""

        def make_lower(v: str) -> str:
            return v.lower()

        def add_suffix(v: str) -> str:
            return f"{v}_SUFFIX"

        NestedAnnotated = Annotated[
            Annotated[str, AfterValidator(make_lower)],
            AfterValidator(add_suffix),
        ]

        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "text": {"type": "string", "format": "custom"},
            },
            "required": ["text"],
        }
        schema = Schema.model_validate(schema_raw)
        Model = to_lax_model(schema, format_validators={"custom": NestedAnnotated})

        instance = Model(text=456)
        assert instance.model_dump() == {
            "text": "456_SUFFIX",
        }

    def test_lax_mode_annotated_with_before_validator(self) -> None:
        """Test lax mode with BeforeValidator in Annotated type."""

        def strip_whitespace(v: str) -> str:
            if isinstance(v, str):
                return v.strip()
            return v

        StrippedStr = Annotated[str, BeforeValidator(strip_whitespace)]

        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "name": {"type": "string", "format": "stripped"},
            },
            "required": ["name"],
        }
        schema = Schema.model_validate(schema_raw)
        Model = to_lax_model(schema, format_validators={"stripped": StrippedStr})

        instance = Model(name=789)
        assert instance.model_dump() == {"name": "789"}

    def test_extract_annotated_in_lax_mode(self) -> None:
        """Test extraction of base type from Annotated in lax mode."""

        def uppercase(v: str) -> str:
            return v.upper()

        UpperStr = Annotated[str, AfterValidator(uppercase)]

        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "name": {"type": "string", "format": "upper"},
            },
            "required": ["name"],
        }
        schema = Schema.model_validate(schema_raw)
        Model = to_lax_model(schema, format_validators={"upper": UpperStr})

        instance = Model(name=12345)
        assert instance.model_dump() == {"name": "12345"}


class TestConverterErrorHandling:
    """Tests for error handling in converters."""

    def test_model_caching(self) -> None:
        """Test that identical schemas reuse cached models."""
        schema_raw1 = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
            },
        }

        schema_raw2 = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
            },
        }

        schema1 = Schema.model_validate(schema_raw1)
        schema2 = Schema.model_validate(schema_raw2)

        converter = SchemaConverter()
        model1 = converter.convert_schema(schema1)
        model2 = converter.convert_schema(schema2)

        assert model1 is model2


@pytest.mark.parametrize(
    ("schema_field", "valid_value", "invalid_value"),
    [
        ({"enum": ["active", "inactive", "pending"]}, "active", "invalid"),
        ({"const": "fixed_value"}, "fixed_value", "wrong_value"),
    ],
)
def test_literal_types(schema_field: dict, valid_value: str, invalid_value: str) -> None:
    """Test enum and const conversion to Literal."""
    schema_raw: SchemaRaw = {
        "type": "object",
        "properties": {"field": schema_field},
    }
    schema = Schema.model_validate(schema_raw)
    Model = to_model(schema)

    instance = Model(field=valid_value)
    assert instance.model_dump() == {"field": valid_value}

    with pytest.raises(ValidationError):
        Model(field=invalid_value)


class TestDictTypes:
    """Tests for dict and additionalProperties."""

    def test_dict_with_additional_properties_schema(self) -> None:
        """Test dict with typed additionalProperties."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "metadata": {"type": "object", "additionalProperties": {"type": "integer"}},
            },
        }
        schema = Schema.model_validate(schema_raw)
        Model = to_model(schema)

        instance = Model(metadata={"count": 42, "total": 100})
        assert instance.model_dump() == {
            "metadata": {"count": 42, "total": 100},
        }

    def test_dict_with_false_additional_properties(self) -> None:
        """Test dict creation with additionalProperties: false."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "data": {"type": "object", "additionalProperties": False},
            },
        }
        schema = Schema.model_validate(schema_raw)
        Model = to_model(schema)

        instance = Model(data={})
        assert instance.model_dump() == {"data": {}}

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
        }
        schema = Schema.model_validate(schema_raw)
        Model = to_model(schema)

        instance = Model(data={"a": 1, "b": "text", "c": [1, 2, 3]})
        assert instance.model_dump() == {
            "data": {"a": 1, "b": "text", "c": [1, 2, 3]},
        }


class TestMultipleTypes:
    """Tests for schemas with multiple types."""

    def test_multiple_type_union(self) -> None:
        """Test schema with multiple types."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "value": {"type": ["string", "integer", "null"]},
            },
        }
        schema = Schema.model_validate(schema_raw)
        Model = to_model(schema)

        instance = Model(value="text")
        assert instance.model_dump() == {"value": "text"}

        instance = Model(value=42)
        assert instance.model_dump() == {"value": 42}

        instance = Model(value=None)
        assert instance.model_dump() == {"value": None}


class TestAdditionalPropertiesConfig:
    """Tests for additionalProperties configuration."""

    def test_additional_properties_forbid(self) -> None:
        """Test that additionalProperties: false forbids extra fields."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "additionalProperties": False,
        }
        schema = Schema.model_validate(schema_raw)
        Model = to_model(schema)

        instance = Model(name="Alice")
        assert instance.model_dump() == {"name": "Alice"}

        with pytest.raises(ValidationError):
            Model(name="Alice", extra="field")

    def test_additional_properties_allow(self) -> None:
        """Test that additionalProperties allows extra fields."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "additionalProperties": True,
        }
        schema = Schema.model_validate(schema_raw)
        Model = to_model(schema)

        instance = Model(name="Alice", extra="allowed")
        assert instance.model_dump() == {
            "name": "Alice",
            "extra": "allowed",
        }


@pytest.mark.parametrize(
    ("schema_property", "valid_value", "invalid_value"),
    [
        (
            {"type": "array", "items": {"type": "string"}, "minItems": 1},
            ["tag1"],
            [],
        ),
        (
            {"type": "array", "items": {"type": "string"}, "maxItems": 2},
            ["tag1", "tag2"],
            ["tag1", "tag2", "tag3"],
        ),
        (
            {"type": "string", "minLength": 3},
            "abc",
            "ab",
        ),
        (
            {"type": "string", "maxLength": 5},
            "short",
            "toolong",
        ),
    ],
)
def test_constraints(
    schema_property: dict,
    valid_value,
    invalid_value,
) -> None:
    """Test min/max constraints."""
    schema_raw: SchemaRaw = {"type": "object", "properties": {"field": schema_property}}
    schema = Schema.model_validate(schema_raw)
    Model = to_model(schema)

    instance = Model(field=valid_value)
    assert instance.model_dump() == {"field": valid_value}

    with pytest.raises(ValidationError):
        Model(field=invalid_value)


class TestAnnotatedValidators:
    """Tests for Annotated type validators support."""

    def test_annotated_validator_basic(self) -> None:
        """Test basic Annotated type as validator."""

        def validate_positive(v: int) -> int:
            if v <= 0:
                raise ValueError("Must be positive")
            return v

        PositiveInt = Annotated[int, AfterValidator(validate_positive)]

        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {"count": {"type": "integer", "format": "positive"}},
            "required": ["count"],
        }
        schema = Schema.model_validate(schema_raw)
        Model = to_model(schema, format_validators={"positive": PositiveInt})

        instance = Model(count=5)
        assert instance.model_dump() == {"count": 5}

        with pytest.raises(ValidationError, match="Must be positive"):
            Model(count=-1)

    def test_annotated_validator_with_transformation(self) -> None:
        """Test Annotated type with value transformation."""

        def double(v: Any) -> Any:
            return v * 2

        def check_even(v: int) -> int:
            if v % 2 != 0:
                raise ValueError("Must be even")
            return v

        DoubledEvenInt = Annotated[int, AfterValidator(double), AfterValidator(check_even)]

        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {"count": {"type": "integer", "format": "doubled-even"}},
            "required": ["count"],
        }
        schema = Schema.model_validate(schema_raw)
        Model = to_model(schema, format_validators={"doubled-even": DoubledEvenInt})

        instance = Model(count=3)
        assert instance.model_dump() == {"count": 6}

        instance = Model(count=4)
        assert instance.model_dump() == {"count": 8}

    def test_callable_validator(self) -> None:
        """Test callable function as validator."""

        def validate_email_simple(v: str) -> str:
            if "@" not in v:
                raise ValueError("Invalid email")
            return v

        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {"email": {"type": "string", "format": "email-simple"}},
            "required": ["email"],
        }
        schema = Schema.model_validate(schema_raw)
        Model = to_model(schema, format_validators={"email-simple": validate_email_simple})

        instance = Model(email="test@example.com")
        assert instance.model_dump() == {"email": "test@example.com"}

        with pytest.raises(ValidationError, match="Invalid email"):
            Model(email="invalid")

    def test_mixed_validators(self) -> None:
        """Test multiple validator types in one schema."""

        def validate_positive(v: int) -> int:
            if v <= 0:
                raise ValueError("Must be positive")
            return v

        def validate_uppercase(v: str) -> str:
            if not v.isupper():
                raise ValueError("Must be uppercase")
            return v

        PositiveInt = Annotated[int, AfterValidator(validate_positive)]

        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "count": {"type": "integer", "format": "positive"},
                "code": {"type": "string", "format": "uppercase"},
            },
            "required": ["count", "code"],
        }
        schema = Schema.model_validate(schema_raw)
        Model = to_model(
            schema,
            format_validators={"positive": PositiveInt, "uppercase": validate_uppercase},
        )

        instance = Model(count=5, code="ABC")
        assert instance.model_dump() == {"count": 5, "code": "ABC"}

        with pytest.raises(ValidationError, match="Must be positive"):
            Model(count=-1, code="ABC")

        with pytest.raises(ValidationError, match="Must be uppercase"):
            Model(count=5, code="abc")

    def test_annotated_validator_with_lax_mode(self) -> None:
        """Test Annotated validators work with lax mode."""

        def validate_positive(v: int) -> int:
            if v <= 0:
                raise ValueError("Must be positive")
            return v

        PositiveInt = Annotated[int, AfterValidator(validate_positive)]

        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {"count": {"type": "integer", "format": "positive"}},
            "required": ["count"],
        }
        schema = Schema.model_validate(schema_raw)
        Model = to_lax_model(schema, format_validators={"positive": PositiveInt})

        instance = Model(count=5)
        assert instance.model_dump() == {"count": 5}

        instance = Model(count="10")  # type: ignore[arg-type]
        assert instance.model_dump() == {"count": 10}

        with pytest.raises(ValidationError, match="Must be positive"):
            Model(count=-1)

    def test_validator_as_type_class(self) -> None:
        """Test validator as type class."""

        class CustomType:
            def __init__(self, value: str):
                if not value.startswith("custom:"):
                    raise ValueError("Must start with 'custom:'")
                self.value = value

            def __str__(self) -> str:
                return self.value

            @classmethod
            def __get_pydantic_core_schema__(cls, source_type, handler):
                from pydantic_core import core_schema

                return core_schema.no_info_after_validator_function(
                    cls,
                    handler(str),
                    serialization=core_schema.plain_serializer_function_ser_schema(
                        lambda x: x.value, return_schema=core_schema.str_schema()
                    ),
                )

        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "field": {"type": "string", "format": "custom"},
            },
        }
        schema = Schema.model_validate(schema_raw)
        Model = to_model(schema, format_validators={"custom": CustomType})

        instance = Model(field="custom:value")
        assert instance.model_dump() == {
            "field": "custom:value",
        }


class TestSchemaEdgeCases:
    """Tests for edge cases in schema conversion."""

    def test_defs_in_nested_schema_raises_error(self) -> None:
        """Test that $defs in nested schemas raises SchemaConvertionError."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "nested": {
                    "type": "object",
                    "$defs": {
                        "SomeType": {"type": "string"},
                    },
                    "properties": {
                        "field": {"type": "string"},
                    },
                },
            },
        }
        schema = Schema.model_validate(schema_raw)

        with pytest.raises(SchemaConvertionError, match=r"\$defs is only allowed in root schema"):
            to_model(schema)

    def test_root_model_for_array_type(self) -> None:
        """Test RootModel creation for array type schemas."""
        schema_raw: SchemaRaw = {
            "type": "array",
            "items": {"type": "string"},
        }
        schema = Schema.model_validate(schema_raw)
        Model = to_model(schema)

        instance = Model(["item1", "item2", "item3"])
        assert instance.model_dump() == ["item1", "item2", "item3"]

    def test_root_model_for_string_type(self) -> None:
        """Test RootModel creation for string type schemas."""
        schema_raw: SchemaRaw = {
            "type": "string",
            "minLength": 5,
        }
        schema = Schema.model_validate(schema_raw)
        Model = to_model(schema)

        instance = Model("hello world")
        assert instance.model_dump() == "hello world"

        with pytest.raises(ValidationError):
            Model("hi")

    def test_root_model_for_integer_type(self) -> None:
        """Test RootModel creation for integer type schemas."""
        schema_raw: SchemaRaw = {
            "type": "integer",
            "minimum": 0,
            "maximum": 100,
        }
        schema = Schema.model_validate(schema_raw)
        Model = to_model(schema)

        instance = Model(42)
        assert instance.model_dump() == 42

        with pytest.raises(ValidationError):
            Model(-1)

        with pytest.raises(ValidationError):
            Model(101)

    def test_allof_without_properties_single_base(self) -> None:
        """Test allOf without properties with single base class."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "allOf": [
                {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "age": {"type": "integer"},
                    },
                    "required": ["name"],
                },
            ],
        }
        schema = Schema.model_validate(schema_raw)
        Model = to_model(schema)

        instance = Model(name="Alice", age=30)
        assert instance.model_dump() == {
            "name": "Alice",
            "age": 30,
        }

    def test_allof_without_properties_multiple_bases(self) -> None:
        """Test allOf without properties with multiple base classes."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "allOf": [
                {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                    },
                    "required": ["name"],
                },
                {
                    "type": "object",
                    "properties": {
                        "age": {"type": "integer"},
                    },
                },
                {
                    "type": "object",
                    "properties": {
                        "email": {"type": "string"},
                    },
                },
            ],
        }
        schema = Schema.model_validate(schema_raw)
        Model = to_model(schema)

        instance = Model(name="Alice", age=30, email="alice@example.com")
        assert instance.model_dump() == {
            "name": "Alice",
            "age": 30,
            "email": "alice@example.com",
        }

    def test_oneof_basic(self) -> None:
        """Test basic oneOf without discriminator."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "value": {
                    "oneOf": [
                        {"type": "string"},
                        {"type": "boolean"},
                    ],
                },
            },
        }
        schema = Schema.model_validate(schema_raw)
        Model = to_model(schema)

        instance = Model(value="text")
        assert instance.model_dump() == {"value": "text"}

        instance = Model(value=True)
        assert instance.model_dump() == {"value": True}

    def test_anyof_with_null(self) -> None:
        """Test anyOf with null type."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "value": {
                    "anyOf": [
                        {"type": "string"},
                        {"type": "null"},
                    ],
                },
            },
        }
        schema = Schema.model_validate(schema_raw)
        Model = to_model(schema)

        instance = Model(value="text")
        assert instance.model_dump() == {"value": "text"}

        instance = Model(value=None)
        assert instance.model_dump() == {"value": None}

    def test_unique_items_array(self) -> None:
        """Test array with uniqueItems constraint."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "uniqueItems": True,
                },
            },
        }
        schema = Schema.model_validate(schema_raw)
        Model = to_model(schema)

        instance = Model(tags=["python", "coding", "dev"])
        result = instance.model_dump()
        assert len(result["tags"]) == 3

    def test_number_constraints(self) -> None:
        """Test number with min/max and multiple constraints."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "score": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 100,
                    "multipleOf": 0.5,
                },
            },
        }
        schema = Schema.model_validate(schema_raw)
        Model = to_model(schema)

        instance = Model(score=50.5)
        assert instance.model_dump() == {"score": 50.5}

        with pytest.raises(ValidationError):
            Model(score=-1)

        with pytest.raises(ValidationError):
            Model(score=101)

        with pytest.raises(ValidationError):
            Model(score=50.3)

    def test_additional_properties_with_schema(self) -> None:
        """Test additionalProperties with schema definition."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
            },
            "additionalProperties": {
                "type": "integer",
            },
        }
        schema = Schema.model_validate(schema_raw)
        Model = to_model(schema)

        instance = Model(name="test", extra1=10, extra2=20)
        assert instance.model_dump() == {
            "name": "test",
            "extra1": 10,
            "extra2": 20,
        }

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
        Model = to_model(schema)

        instance = Model(valid_name="test", another_name="value")
        assert instance.model_dump() == {
            "valid_name": "test",
            "another_name": "value",
        }


class TestConverterCaching:
    """Tests for model caching in converter."""

    def test_same_schema_returns_cached_model(self) -> None:
        """Test that converting the same schema twice returns cached model."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
            },
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
        }

        schema_raw2 = {
            "type": "object",
            "properties": {
                "age": {"type": "integer"},
            },
        }

        converter = SchemaConverter()
        schema1 = Schema.model_validate(schema_raw1)
        schema2 = Schema.model_validate(schema_raw2)

        model1 = converter.convert_schema(schema1)
        model2 = converter.convert_schema(schema2)

        assert model1 is not model2


@pytest.mark.parametrize(
    ("schema_raw", "test_cases"),
    [
        (
            {
                "type": "object",
                "properties": {"field": {"type": "string"}},
                "required": ["field"],
            },
            [
                (None, ""),
                (123, "123"),
                ("test", "test"),
            ],
        ),
        (
            {
                "type": "object",
                "properties": {"field": {"type": "integer"}},
                "required": ["field"],
            },
            [
                ("42", 42),
                (3.14, 3),
                (25, 25),
            ],
        ),
        (
            {
                "type": "object",
                "properties": {"field": {"type": "number"}},
                "required": ["field"],
            },
            [
                ("3.14", 3.14),
                (42, 42.0),
                (9.99, 9.99),
            ],
        ),
        (
            {
                "type": "object",
                "properties": {"field": {"type": "array", "items": {"type": "string"}}},
                "required": ["field"],
            },
            [
                (None, []),
                ("a, b, c", ["a", "b", "c"]),
                (["x", "y"], ["x", "y"]),
            ],
        ),
    ],
)
def test_lax_coercion_by_type(schema_raw: SchemaRaw, test_cases: list[Any]) -> None:
    """Test lax mode coercion for different types."""
    schema = Schema.model_validate(schema_raw)
    Model = to_lax_model(schema)

    for input_value, expected_output in test_cases:
        instance = Model(field=input_value)
        assert instance.model_dump() == {
            "field": expected_output,
        }


class TestLaxSchemaConverter:
    """Tests for LaxSchemaConverter with additional scenarios."""

    def test_explicit_defaults_preserved(self) -> None:
        """Test that explicit defaults are preserved."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "status": {"type": "string", "default": "pending"},
            },
        }
        schema = Schema.model_validate(schema_raw)
        Model = to_lax_model(schema)

        instance = Model()
        assert instance.model_dump() == {
            "status": "pending",
        }

    def test_lax_accepts_full_data(self) -> None:
        """Test that lax mode still accepts complete data."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["name", "age"],
        }
        schema = Schema.model_validate(schema_raw)
        Model = to_lax_model(schema)

        instance = Model(name="Alice", age=30, tags=["dev", "python"])
        assert instance.model_dump() == {
            "name": "Alice",
            "age": 30,
            "tags": ["dev", "python"],
        }

    def test_lax_coerces_types(self) -> None:
        """Test that lax mode coerces types."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
            },
            "required": ["name", "age"],
        }
        schema = Schema.model_validate(schema_raw)
        Model = to_lax_model(schema)

        instance = Model(name=123, age="42")
        assert instance.model_dump() == {
            "name": "123",  # String coercion: int -> str
            "age": 42,  # Int coercion: str -> int
        }

    def test_required_fields_stay_required(self) -> None:
        """Test that required fields remain required in lax mode."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
            },
            "required": ["name"],
        }
        schema = Schema.model_validate(schema_raw)
        Model = to_lax_model(schema)

        # Required field must be provided
        # TODO: catch specific error by regex
        with pytest.raises(ValidationError) as exc_info:
            Model()
        assert "name" in str(exc_info.value)

    def test_optional_fields_stay_optional(self) -> None:
        """Test that optional fields remain optional in lax mode."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
            },
            "required": ["name"],
        }
        schema = Schema.model_validate(schema_raw)
        Model = to_lax_model(schema)

        # Optional field can be omitted
        instance = Model(name="Alice")
        assert instance.model_dump() == {
            "name": "Alice",
            "age": None,
        }

    def test_coercion_with_format_validator(self) -> None:
        """Test that coercion works with format validators."""

        def validate_positive(value: int) -> int:
            if value < 0:
                msg = "Must be positive"
                raise ValueError(msg)
            return value

        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "count": {"type": "integer", "format": "positive"},
            },
            "required": ["count"],
        }
        schema = Schema.model_validate(schema_raw)
        Model = to_lax_model(schema, format_validators={"positive": validate_positive})

        # Coercion happens first, then validation
        instance = Model(count="42")
        assert instance.model_dump() == {
            "count": 42,
        }

        # Negative value fails validation after coercion
        with pytest.raises(ValidationError):
            Model(count="-5")

    def test_multiple_fields_with_different_types(self) -> None:
        """Test coercion on multiple fields with different types."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
                "balance": {"type": "number"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["name", "age", "balance", "tags"],
        }
        schema = Schema.model_validate(schema_raw)
        Model = to_lax_model(schema)

        instance = Model(
            name=123,  # int -> str
            age="25",  # str -> int
            balance="99.99",  # str -> float
            tags="python, coding",  # CSV -> list
        )

        assert instance.model_dump() == {
            "name": "123",
            "age": 25,
            "balance": 99.99,
            "tags": ["python", "coding"],
        }

    def test_nested_objects_with_coercion(self) -> None:
        """Test that nested objects get coercion on nested fields."""
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
        Model = to_lax_model(schema)

        # Nested object fields still work
        instance = Model(user={"name": 123})
        assert instance.model_dump() == {
            "user": {
                "name": "123",  # Coercion happens on nested string field
            },
        }

    def test_no_coercion_for_union_types(self) -> None:
        """Test that union types work correctly."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "value": {
                    "anyOf": [
                        {"type": "string"},
                        {"type": "integer"},
                    ],
                },
            },
            "required": ["value"],
        }
        schema = Schema.model_validate(schema_raw)
        Model = to_lax_model(schema)

        # String value works
        instance = Model(value="test")
        assert instance.model_dump() == {
            "value": "test",
        }

        # Int value works
        instance = Model(value=42)
        assert instance.model_dump() == {
            "value": 42,
        }
