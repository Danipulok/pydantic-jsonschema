"""Tests for JSON Schema to Pydantic model conversion."""

from datetime import UTC, datetime
from ipaddress import IPv4Address
from typing import TYPE_CHECKING, Annotated, Any
from uuid import UUID

import pytest
from annotated_types import Gt, Lt
from inline_snapshot import snapshot
from pydantic import BaseModel, GetCoreSchemaHandler, JsonValue, ValidationError
from pydantic.functional_validators import AfterValidator
from pydantic_core import CoreSchema, core_schema

from pydantic_jsonschema import (
    SchemaConverter,
    to_model,
)
from pydantic_jsonschema.exceptions import SchemaConversionError, SchemaReferenceError
from pydantic_jsonschema.formats import UUID as UUID_FORMAT
from pydantic_jsonschema.formats import DateTime, Email, IPv4, Uri
from pydantic_jsonschema.types import Schema

if TYPE_CHECKING:
    from pydantic.fields import FieldInfo

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
                },
            },
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
                        },
                    },
                },
            },
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
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        instance = model(data=[1, "two", 3.0, True, None])
        assert instance.model_dump() == snapshot(
            {
                "data": [1, "two", 3.0, True, None],
            }
        )


class TestReferences:
    """Tests for `$defs` and `$ref` support."""

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
        model = to_model(schema)

        instance = model(address={"street": "Main St", "city": "NYC"})
        assert instance.model_dump() == snapshot(
            {
                "address": {
                    "street": "Main St",
                    "city": "NYC",
                },
            }
        )

    def test_defs_with_single_reference(self) -> None:
        """Test schema with `$defs` containing one definition."""
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
        model = to_model(schema)

        instance = model(home={"street": "Main St", "city": "NYC"})
        assert instance.model_dump() == snapshot(
            {
                "home": {
                    "street": "Main St",
                    "city": "NYC",
                },
            }
        )

    def test_defs_with_multiple_references(self) -> None:
        """Test schema with multiple `$defs`."""
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
        model = to_model(schema)

        instance = model(
            owner={"name": "Alice", "age": 30},
            address={"street": "Main St"},
            employer={"name": "ACME Corp"},
        )
        assert instance.model_dump() == snapshot(
            {
                "owner": {"name": "Alice", "age": 30},
                "address": {"street": "Main St"},
                "employer": {"name": "ACME Corp"},
            }
        )

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
        model = to_model(schema)

        instance = model(home={"street": "Main St", "city": {"name": "NYC"}})
        assert instance.model_dump() == snapshot(
            {
                "home": {
                    "street": "Main St",
                    "city": {"name": "NYC"},
                },
            }
        )

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
        """Test property using `$ref`."""
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
        model = to_model(schema)

        instance = model(contact={"email": "test@example.com", "phone": "123-456"})
        assert instance.model_dump() == snapshot(
            {
                "contact": {
                    "email": "test@example.com",
                    "phone": "123-456",
                },
            }
        )

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
        model = to_model(schema)

        instance = model(items=[{"name": "A", "value": 1}, {"name": "B", "value": 2}])
        assert instance.model_dump() == snapshot(
            {
                "items": [
                    {"name": "A", "value": 1},
                    {"name": "B", "value": 2},
                ],
            }
        )

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
        model = to_model(schema)

        instance = model(featured={"title": "Test", "author": {"name": "Alice"}})
        assert instance.model_dump() == snapshot(
            {
                "featured": {"title": "Test", "author": {"name": "Alice"}},
            }
        )

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
            },
        )
        model = converter.convert_schema(schema)

        instance = model(address={"street": "Main St", "city": "NYC"})
        assert instance.model_dump() == snapshot(
            {
                "address": {"street": "Main St", "city": "NYC"},
            }
        )

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
        model = to_model(schema)

        instance = model(
            field1={"value": "test1"},
            field2={"value": "test2"},
        )
        assert instance.model_dump() == snapshot(
            {
                "field1": {"value": "test1"},
                "field2": {"value": "test2"},
            }
        )

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
        model = to_model(schema)

        instance = model([{"name": "item1"}, {"name": "item2"}])  # type: ignore[call-arg]
        assert instance.model_dump() == snapshot([{"name": "item1"}, {"name": "item2"}])

    def test_defs_alias_reference(self) -> None:
        """Test `$defs` entry that is a `Reference` alias to another def."""
        schema_raw: SchemaRaw = {
            "$defs": {
                "Address": {
                    "type": "object",
                    "properties": {
                        "street": {"type": "string"},
                    },
                },
                "Location": {"$ref": "#/$defs/Address"},
            },
            "type": "object",
            "properties": {
                "home": {"$ref": "#/$defs/Location"},
            },
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        instance = model(home={"street": "Main St"})
        assert instance.model_dump() == snapshot(
            {
                "home": {"street": "Main St"},
            }
        )

    def test_defs_alias_chain(self) -> None:
        """Test `$defs` alias chain resolving through multiple references."""
        schema_raw: SchemaRaw = {
            "$defs": {
                "Primary": {"$ref": "#/$defs/Secondary"},
                "Secondary": {"$ref": "#/$defs/Target"},
                "Target": {
                    "type": "object",
                    "properties": {
                        "value": {"type": "integer"},
                    },
                },
            },
            "type": "object",
            "properties": {
                "field": {"$ref": "#/$defs/Primary"},
            },
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        instance = model(field={"value": 42})
        assert instance.model_dump() == snapshot(
            {
                "field": {"value": 42},
            }
        )

    def test_defs_alias_cycle_raises(self) -> None:
        """Test circular `$defs` alias chain raises `SchemaReferenceError`."""
        schema_raw: SchemaRaw = {
            "$defs": {
                "First": {"$ref": "#/$defs/Second"},
                "Second": {"$ref": "#/$defs/First"},
            },
            "type": "object",
            "properties": {},
        }
        schema = Schema.model_validate(schema_raw)

        with pytest.raises(SchemaReferenceError, match=r"Circular \$defs alias chain"):
            to_model(schema)

    def test_defs_alias_unknown_target_raises(self) -> None:
        """Test `$defs` alias pointing to a missing def raises `SchemaReferenceError`."""
        schema_raw: SchemaRaw = {
            "$defs": {
                "Alias": {"$ref": "#/$defs/DoesNotExist"},
            },
            "type": "object",
            "properties": {},
        }
        schema = Schema.model_validate(schema_raw)

        with pytest.raises(SchemaReferenceError, match=r"unknown target"):
            to_model(schema)

    def test_defs_alias_external_ref_raises(self) -> None:
        """Test `$defs` alias with external reference raises `SchemaReferenceError`."""
        schema_raw: SchemaRaw = {
            "$defs": {
                "Alias": {"$ref": "https://example.com/schemas/address.json"},
            },
            "type": "object",
            "properties": {},
        }
        schema = Schema.model_validate(schema_raw)

        with pytest.raises(SchemaReferenceError, match=r"external reference"):
            to_model(schema)

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
        model = to_model(schema)

        instance = model(items=["text", {"nested": "value"}])
        assert instance.model_dump() == snapshot(
            {
                "items": ["text", {"nested": "value"}],
            }
        )

    def test_defs_in_nested_schema_raises_error(self) -> None:
        """Test that `$defs` in nested schemas raises `SchemaConversionError`."""
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

        with pytest.raises(SchemaConversionError, match=r"\$defs is only allowed in root schema"):
            to_model(schema)

    def test_schema_with_prebuilt_refs_no_defs(self) -> None:
        """Test converter with pre-built refs but no `$defs` in schema.

        This ensures the forward reference namespace building works correctly
        when there are no schema definitions to process (empty defs cache).
        """

        class CustomAddress(BaseModel):
            street: str
            city: str

        # Schema without `$defs`, but will use pre-built ref.
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "address": {"$ref": "#/$defs/CustomAddress"},
            },
        }
        schema = Schema.model_validate(schema_raw)

        # Create converter with pre-built ref for CustomAddress
        converter = SchemaConverter(refs={"#/$defs/CustomAddress": CustomAddress})
        model = converter.convert_schema(schema)

        instance = model(address={"street": "Main St", "city": "NYC"})
        assert instance.model_dump() == snapshot(
            {
                "address": {"street": "Main St", "city": "NYC"},
            }
        )

    def test_array_items_with_ref_generation(self) -> None:
        """Test array with `$ref` in items triggers model generation."""
        schema_raw: SchemaRaw = {
            "$defs": {
                "Item": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"},
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
        model = to_model(schema)

        instance = model(items=[{"id": 1, "name": "first"}, {"id": 2, "name": "second"}])
        assert instance.model_dump() == snapshot(
            {
                "items": [
                    {"id": 1, "name": "first"},
                    {"id": 2, "name": "second"},
                ],
            }
        )


class TestComposition:
    """Tests for `allOf` / `anyOf` / `oneOf` composition keywords."""

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
        model = to_model(schema)

        instance = model(name="Alice", age=30)
        assert instance.model_dump() == snapshot(
            {
                "name": "Alice",
                "age": 30,
            }
        )

    def test_allof_with_reference(self) -> None:
        """Test `allOf` with `$ref`."""
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
        model = to_model(schema)

        instance = model(id=1, name="Test")
        assert instance.model_dump() == snapshot(
            {
                "id": 1,
                "name": "Test",
            }
        )

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
        model = to_model(schema)

        instance = model(combined={"a": "test", "b": 42})
        assert instance.model_dump() == snapshot(
            {
                "combined": {"a": "test", "b": 42},
            }
        )

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
        model = to_model(schema)

        instance = model(name="Alice", age=30)
        assert instance.model_dump() == snapshot(
            {
                "name": "Alice",
                "age": 30,
            }
        )

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
        model = to_model(schema)

        instance = model(name="Alice", age=30, email="alice@example.com")
        assert instance.model_dump() == snapshot(
            {
                "name": "Alice",
                "age": 30,
                "email": "alice@example.com",
            }
        )

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
        model = to_model(schema)

        instance = model(value="hello")
        assert instance.model_dump() == snapshot({"value": "hello"})

        instance = model(value=42)
        assert instance.model_dump() == snapshot({"value": 42})

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
        model = to_model(schema)

        instance = model(multi_value="text")
        assert instance.model_dump() == snapshot({"multi_value": "text"})

        instance = model(multi_value=42)
        assert instance.model_dump() == snapshot({"multi_value": 42})

        instance = model(multi_value=True)
        assert instance.model_dump() == snapshot({"multi_value": True})

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
        model = to_model(schema)

        instance = model(value="text")
        assert instance.model_dump() == snapshot({"value": "text"})

        instance = model(value=None)
        assert instance.model_dump() == snapshot({"value": None})

    def test_anyof_with_unresolved_forward_ref(self) -> None:
        """Test anyOf with forward reference to another def type."""
        schema_raw: SchemaRaw = {
            "$defs": {
                "TypeA": {
                    "type": "object",
                    "properties": {
                        "a": {"type": "string"},
                        "other": {
                            "anyOf": [
                                {"$ref": "#/$defs/TypeB"},
                                {"type": "null"},
                            ],
                        },
                    },
                },
                "TypeB": {
                    "type": "object",
                    "properties": {
                        "b": {"type": "integer"},
                    },
                },
            },
            "type": "object",
            "properties": {
                "item": {"$ref": "#/$defs/TypeA"},
            },
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        instance = model(item={"a": "test", "other": {"b": 42}})
        assert instance.model_dump() == snapshot(
            {
                "item": {"a": "test", "other": {"b": 42}},
            }
        )

        instance = model(item={"a": "test", "other": None})
        assert instance.model_dump() == snapshot(
            {
                "item": {"a": "test", "other": None},
            }
        )

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
        model = to_model(schema)

        instance = model(value="text")
        assert instance.model_dump() == snapshot({"value": "text"})

        instance = model(value=True)
        assert instance.model_dump() == snapshot({"value": True})

    def test_oneof_overlapping_branches_rejected(self) -> None:
        """Test `oneOf` rejects a value matching more than one branch."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "value": {
                    "oneOf": [
                        {"type": "integer"},
                        {"type": "number"},
                    ],
                },
            },
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        instance = model(value=1.5)
        assert instance.model_dump() == snapshot({"value": 1.5})

        with pytest.raises(ValidationError, match=r"matches 2 `oneOf` branches"):
            model(value=1)

    def test_oneof_no_matching_branch_rejected(self) -> None:
        """Test `oneOf` rejects a value matching zero branches."""
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
        model = to_model(schema)

        with pytest.raises(ValidationError, match=r"matches 0 `oneOf` branches"):
            model(value=[1, 2, 3])

    def test_oneof_with_forward_ref(self) -> None:
        """Test `oneOf` with a forward reference branch resolved lazily."""
        schema_raw: SchemaRaw = {
            "$defs": {
                "TypeA": {
                    "type": "object",
                    "properties": {
                        "other": {
                            "oneOf": [
                                {"$ref": "#/$defs/TypeB"},
                                {"type": "null"},
                            ],
                        },
                    },
                },
                "TypeB": {
                    "type": "object",
                    "properties": {
                        "b": {"type": "integer"},
                    },
                },
            },
            "type": "object",
            "properties": {
                "item": {"$ref": "#/$defs/TypeA"},
            },
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        instance = model(item={"other": {"b": 42}})
        assert instance.model_dump() == snapshot(
            {
                "item": {"other": {"b": 42}},
            }
        )

        instance = model(item={"other": None})
        assert instance.model_dump() == snapshot(
            {
                "item": {"other": None},
            }
        )


class TestDiscriminatedOneOf:
    """`oneOf` branches sharing a const tag map to a Pydantic discriminated union."""

    def test_routes_by_tag(self) -> None:
        """A const-tagged `oneOf` validates each branch by its discriminator value."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "pet": {
                    "oneOf": [
                        {
                            "type": "object",
                            "title": "Cat",
                            "properties": {
                                "type": {"const": "cat"},
                                "meow": {"type": "boolean"},
                            },
                            "required": ["type", "meow"],
                        },
                        {
                            "type": "object",
                            "title": "Dog",
                            "properties": {
                                "type": {"const": "dog"},
                                "bark": {"type": "boolean"},
                            },
                            "required": ["type", "bark"],
                        },
                    ],
                },
            },
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        cat = model(pet={"type": "cat", "meow": True})
        assert cat.model_dump() == snapshot({"pet": {"type": "cat", "meow": True}})

        dog = model(pet={"type": "dog", "bark": False})
        assert dog.model_dump() == snapshot({"pet": {"type": "dog", "bark": False}})

    def test_root_level_discriminated_union(self) -> None:
        """A root `oneOf` of tagged objects becomes a discriminated `RootModel`."""
        schema_raw: SchemaRaw = {
            "oneOf": [
                {
                    "type": "object",
                    "title": "Cat",
                    "properties": {"type": {"const": "cat"}, "meow": {"type": "boolean"}},
                    "required": ["type", "meow"],
                },
                {
                    "type": "object",
                    "title": "Dog",
                    "properties": {"type": {"const": "dog"}, "bark": {"type": "boolean"}},
                    "required": ["type", "bark"],
                },
            ],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        pet = model.model_validate({"type": "cat", "meow": True})
        assert pet.model_dump() == snapshot({"type": "cat", "meow": True})

        assert model.model_json_schema() == snapshot(
            {
                "$defs": {
                    "Cat": {
                        "additionalProperties": True,
                        "properties": {
                            "type": {"const": "cat", "title": "Type", "type": "string"},
                            "meow": {"title": "Meow", "type": "boolean"},
                        },
                        "required": ["type", "meow"],
                        "title": "Cat",
                        "type": "object",
                    },
                    "Dog": {
                        "additionalProperties": True,
                        "properties": {
                            "type": {"const": "dog", "title": "Type", "type": "string"},
                            "bark": {"title": "Bark", "type": "boolean"},
                        },
                        "required": ["type", "bark"],
                        "title": "Dog",
                        "type": "object",
                    },
                },
                "discriminator": {
                    "mapping": {"cat": "#/$defs/Cat", "dog": "#/$defs/Dog"},
                    "propertyName": "type",
                },
                "oneOf": [{"$ref": "#/$defs/Cat"}, {"$ref": "#/$defs/Dog"}],
                "title": "Model",
            }
        )

        with pytest.raises(ValidationError) as exc_info:
            model.model_validate({"type": "fish"})

        assert exc_info.value.errors(include_url=False, include_context=False) == snapshot(
            [
                {
                    "type": "union_tag_invalid",
                    "loc": (),
                    "msg": "Input tag 'fish' found using 'type' does not match any of the expected tags: 'cat', 'dog'",
                    "input": {"type": "fish"},
                }
            ]
        )

    def test_unknown_tag_rejected(self) -> None:
        """A value whose tag matches no branch is rejected as an invalid tag."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "pet": {
                    "oneOf": [
                        {
                            "type": "object",
                            "title": "Cat",
                            "properties": {"type": {"const": "cat"}},
                            "required": ["type"],
                        },
                        {
                            "type": "object",
                            "title": "Dog",
                            "properties": {"type": {"const": "dog"}},
                            "required": ["type"],
                        },
                    ],
                },
            },
            "required": ["pet"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        with pytest.raises(ValidationError) as exc_info:
            model(pet={"type": "fish"})

        assert exc_info.value.errors(include_url=False, include_context=False) == snapshot(
            [
                {
                    "type": "union_tag_invalid",
                    "loc": ("pet",),
                    "msg": "Input tag 'fish' found using 'type' does not match any of the expected tags: 'cat', 'dog'",
                    "input": {"type": "fish"},
                }
            ]
        )

    def test_routing_uses_tag_not_structure(self) -> None:
        """Validation routes by the tag value, then checks that one branch's shape."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "pet": {
                    "oneOf": [
                        {
                            "type": "object",
                            "title": "Cat",
                            "properties": {
                                "type": {"const": "cat"},
                                "meow": {"type": "boolean"},
                            },
                            "required": ["type", "meow"],
                        },
                        {
                            "type": "object",
                            "title": "Dog",
                            "properties": {
                                "type": {"const": "dog"},
                                "bark": {"type": "boolean"},
                            },
                            "required": ["type", "bark"],
                        },
                    ],
                },
            },
            "required": ["pet"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        # Tag says `cat`, so the `cat` branch is checked: its required `meow` is missing.
        # The error is branch-specific (`pet.cat.meow`), not "matches N oneOf branches".
        with pytest.raises(ValidationError) as exc_info:
            model(pet={"type": "cat", "bark": True})

        assert exc_info.value.errors(include_url=False, include_context=False) == snapshot(
            [
                {
                    "type": "missing",
                    "loc": ("pet", "cat", "meow"),
                    "msg": "Field required",
                    "input": {"type": "cat", "bark": True},
                }
            ]
        )

    def test_dump_round_trips_one_of_with_discriminator(self) -> None:
        """A discriminated union dumps back as `oneOf` plus a `discriminator`."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "pet": {
                    "oneOf": [
                        {
                            "type": "object",
                            "title": "Cat",
                            "properties": {"type": {"const": "cat"}},
                            "required": ["type"],
                        },
                        {
                            "type": "object",
                            "title": "Dog",
                            "properties": {"type": {"const": "dog"}},
                            "required": ["type"],
                        },
                    ],
                },
            },
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        assert model.model_json_schema() == snapshot(
            {
                "$defs": {
                    "Cat": {
                        "additionalProperties": True,
                        "properties": {"type": {"const": "cat", "title": "Type", "type": "string"}},
                        "required": ["type"],
                        "title": "Cat",
                        "type": "object",
                    },
                    "Dog": {
                        "additionalProperties": True,
                        "properties": {"type": {"const": "dog", "title": "Type", "type": "string"}},
                        "required": ["type"],
                        "title": "Dog",
                        "type": "object",
                    },
                },
                "additionalProperties": True,
                "properties": {
                    "pet": {
                        "discriminator": {
                            "mapping": {"cat": "#/$defs/Cat", "dog": "#/$defs/Dog"},
                            "propertyName": "type",
                        },
                        "oneOf": [{"$ref": "#/$defs/Cat"}, {"$ref": "#/$defs/Dog"}],
                        "title": "Pet",
                    }
                },
                "title": "Model",
                "type": "object",
            }
        )

    def test_from_references(self) -> None:
        """`oneOf` of `$ref` branches with a shared tag becomes discriminated."""
        schema_raw: SchemaRaw = {
            "$defs": {
                "Cat": {
                    "type": "object",
                    "properties": {"kind": {"const": "cat"}},
                    "required": ["kind"],
                },
                "Dog": {
                    "type": "object",
                    "properties": {"kind": {"const": "dog"}},
                    "required": ["kind"],
                },
            },
            "type": "object",
            "properties": {
                "pet": {"oneOf": [{"$ref": "#/$defs/Cat"}, {"$ref": "#/$defs/Dog"}]},
            },
            "required": ["pet"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        assert model(pet={"kind": "dog"}).model_dump() == snapshot({"pet": {"kind": "dog"}})

        with pytest.raises(ValidationError) as exc_info:
            model(pet={"kind": "bird"})

        assert exc_info.value.errors(include_url=False, include_context=False) == snapshot(
            [
                {
                    "type": "union_tag_invalid",
                    "loc": ("pet",),
                    "msg": "Input tag 'bird' found using 'kind' does not match any of the expected tags: 'cat', 'dog'",
                    "input": {"kind": "bird"},
                }
            ]
        )

    def test_single_value_enum_tag(self) -> None:
        """A single-value `enum` acts as a const tag for discrimination."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "shape": {
                    "oneOf": [
                        {
                            "type": "object",
                            "title": "Circle",
                            "properties": {"kind": {"enum": ["circle"]}},
                            "required": ["kind"],
                        },
                        {
                            "type": "object",
                            "title": "Square",
                            "properties": {"kind": {"enum": ["square"]}},
                            "required": ["kind"],
                        },
                    ],
                },
            },
            "required": ["shape"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        assert model(shape={"kind": "circle"}).model_dump() == snapshot(
            {"shape": {"kind": "circle"}}
        )

        with pytest.raises(ValidationError) as exc_info:
            model(shape={"kind": "triangle"})

        assert exc_info.value.errors(include_url=False, include_context=False) == snapshot(
            [
                {
                    "type": "union_tag_invalid",
                    "loc": ("shape",),
                    "msg": "Input tag 'triangle' found using 'kind' does not match any of the expected tags: 'circle', 'square'",
                    "input": {"kind": "triangle"},
                }
            ]
        )

    def test_untagged_branches_fall_back_to_one_of(self) -> None:
        """Without a required const tag, `oneOf` keeps the wrap-validator semantics."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "value": {
                    "oneOf": [
                        {
                            "type": "object",
                            "properties": {"tag": {"const": "a"}, "x": {"type": "integer"}},
                        },
                        {
                            "type": "object",
                            "properties": {"tag": {"const": "b"}, "y": {"type": "integer"}},
                        },
                    ],
                },
            },
            "required": ["value"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        # No tag field: both untagged branches match, so the `OneOf` validator
        # reports the multi-branch match instead of routing by a discriminator.
        with pytest.raises(ValidationError) as exc_info:
            model(value={"x": 1})

        assert exc_info.value.errors(include_url=False, include_context=False) == snapshot(
            [
                {
                    "type": "value_error",
                    "loc": ("value",),
                    "msg": "Value error, Input matches 2 `oneOf` branches, expected exactly 1",
                    "input": {"x": 1},
                }
            ]
        )

    def test_non_distinct_tag_falls_back_to_one_of(self) -> None:
        """A const shared with the same value across branches is not a discriminator."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "value": {
                    "oneOf": [
                        {
                            "type": "object",
                            "properties": {"tag": {"const": "same"}, "x": {"type": "integer"}},
                            "required": ["tag"],
                        },
                        {
                            "type": "object",
                            "properties": {"tag": {"const": "same"}, "y": {"type": "integer"}},
                            "required": ["tag"],
                        },
                    ],
                },
            },
            "required": ["value"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        with pytest.raises(ValidationError) as exc_info:
            model(value={"tag": "same"})

        assert exc_info.value.errors(include_url=False, include_context=False) == snapshot(
            [
                {
                    "type": "value_error",
                    "loc": ("value",),
                    "msg": "Value error, Input matches 2 `oneOf` branches, expected exactly 1",
                    "input": {"tag": "same"},
                }
            ]
        )

    def test_non_scalar_tag_falls_back_to_one_of(self) -> None:
        """A non-scalar const (only `str` / `int` / `bool` / `None` tag) is not a discriminator."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "value": {
                    "oneOf": [
                        {
                            "type": "object",
                            "properties": {"kind": {"const": 1.5}},
                            "required": ["kind"],
                        },
                        {
                            "type": "object",
                            "properties": {"kind": {"const": 2.5}},
                            "required": ["kind"],
                        },
                    ],
                },
            },
            "required": ["value"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        with pytest.raises(ValidationError) as exc_info:
            model(value={"kind": 9.9})

        assert exc_info.value.errors(include_url=False, include_context=False) == snapshot(
            [
                {
                    "type": "value_error",
                    "loc": ("value",),
                    "msg": "Value error, Input matches 0 `oneOf` branches, expected exactly 1",
                    "input": {"kind": 9.9},
                }
            ]
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


class TestConstraints:
    """Tests for value constraint keywords."""

    @pytest.mark.parametrize(
        ("schema_property", "valid_value", "invalid_value"),
        [
            pytest.param(
                {"type": "array", "items": {"type": "string"}, "minItems": 1},
                ["tag1"],
                [],
                id="array-min-items",
            ),
            pytest.param(
                {"type": "array", "items": {"type": "string"}, "maxItems": 2},
                ["tag1", "tag2"],
                ["tag1", "tag2", "tag3"],
                id="array-max-items",
            ),
            pytest.param(
                {"type": "string", "minLength": 3},
                "abc",
                "ab",
                id="string-min-length",
            ),
            pytest.param(
                {"type": "string", "maxLength": 5},
                "short",
                "toolong",
                id="string-max-length",
            ),
            pytest.param(
                {"type": "string", "pattern": "^[a-z]+-[0-9]+$"},
                "order-42",
                "ORDER-42",
                id="string-pattern",
            ),
        ],
    )
    def test_constraints(
        self,
        schema_property: dict[str, Any],
        valid_value: JsonValue,
        invalid_value: JsonValue,
    ) -> None:
        """Test min/max constraints."""
        schema_raw: SchemaRaw = {"type": "object", "properties": {"field": schema_property}}
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        instance = model(field=valid_value)
        assert instance.model_dump() == {"field": valid_value}

        with pytest.raises(ValidationError):
            model(field=invalid_value)

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
        model = to_model(schema)

        instance = model(score=50.5)
        assert instance.model_dump() == snapshot({"score": 50.5})

        with pytest.raises(ValidationError):
            model(score=-1)

        with pytest.raises(ValidationError):
            model(score=101)

        with pytest.raises(ValidationError):
            model(score=50.3)

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
        model = to_model(schema)

        instance = model(tags=["python", "coding", "dev"])
        assert instance.model_dump() == snapshot(
            {
                "tags": ["python", "coding", "dev"],
            }
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


class TestDefaults:
    """Tests for field default handling."""

    def test_explicit_default_preserved(self) -> None:
        """Test that explicit default value is used when field is omitted."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "status": {"type": "string", "default": "pending"},
            },
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        instance = model()
        assert instance.model_dump() == snapshot({"status": "pending"})

    def test_optional_field_without_default_is_omitted(self) -> None:
        """Optional field without explicit default is absent from dumps and JSON Schema."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "value": {"type": "integer"},
            },
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        assert model().model_dump() == snapshot({})
        assert model(value=42).model_dump() == snapshot({"value": 42})
        assert model.model_json_schema() == snapshot(
            {
                "additionalProperties": True,
                "properties": {"value": {"title": "Value", "type": "integer"}},
                "title": "Model",
                "type": "object",
            }
        )

        with pytest.raises(ValidationError):
            model(value="not-an-integer")


class TestFormatValidators:
    """Tests for `format_validators` support: custom validators and built-in aliases."""

    def test_annotated_validator_basic(self) -> None:
        """Test basic Annotated type as validator."""

        def validate_positive(v: int) -> int:
            if v <= 0:
                msg = "Must be positive"
                raise ValueError(msg)
            return v

        PositiveInt = Annotated[int, AfterValidator(validate_positive)]  # noqa: N806

        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {"count": {"type": "integer", "format": "positive"}},
            "required": ["count"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema, format_validators={"positive": PositiveInt})

        instance = model(count=5)
        assert instance.model_dump() == snapshot({"count": 5})

        with pytest.raises(ValidationError, match="Must be positive"):
            model(count=-1)

    def test_annotated_validator_with_transformation(self) -> None:
        """Test Annotated type with value transformation."""

        def double(v: int) -> int:
            return v * 2

        def check_even(v: int) -> int:
            if v % 2 != 0:
                msg = "Must be even"
                raise ValueError(msg)
            return v

        DoubledEvenInt = Annotated[int, AfterValidator(double), AfterValidator(check_even)]  # noqa: N806

        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {"count": {"type": "integer", "format": "doubled-even"}},
            "required": ["count"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema, format_validators={"doubled-even": DoubledEvenInt})

        instance = model(count=3)
        assert instance.model_dump() == snapshot({"count": 6})

        instance = model(count=4)
        assert instance.model_dump() == snapshot({"count": 8})

    def test_callable_validator(self) -> None:
        """Test callable function as validator."""

        def validate_email_simple(v: str) -> str:
            if "@" not in v:
                msg = "Invalid email"
                raise ValueError(msg)
            return v

        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {"email": {"type": "string", "format": "email-simple"}},
            "required": ["email"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema, format_validators={"email-simple": validate_email_simple})  # type: ignore[dict-item]

        instance = model(email="test@example.com")
        assert instance.model_dump() == snapshot({"email": "test@example.com"})

        with pytest.raises(ValidationError, match="Invalid email"):
            model(email="invalid")

    def test_mixed_validators(self) -> None:
        """Test multiple validator types in one schema."""

        def validate_positive(v: int) -> int:
            if v <= 0:
                msg = "Must be positive"
                raise ValueError(msg)
            return v

        def validate_uppercase(v: str) -> str:
            if not v.isupper():
                msg = "Must be uppercase"
                raise ValueError(msg)
            return v

        PositiveInt = Annotated[int, AfterValidator(validate_positive)]  # noqa: N806

        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "count": {"type": "integer", "format": "positive"},
                "code": {"type": "string", "format": "uppercase"},
            },
            "required": ["count", "code"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(
            schema,
            format_validators={"positive": PositiveInt, "uppercase": validate_uppercase},  # type: ignore[dict-item]
        )

        instance = model(count=5, code="ABC")
        assert instance.model_dump() == snapshot({"count": 5, "code": "ABC"})

        with pytest.raises(ValidationError, match="Must be positive"):
            model(count=-1, code="ABC")

        with pytest.raises(ValidationError, match="Must be uppercase"):
            model(count=5, code="abc")

    def test_validator_as_type_class(self) -> None:
        """Test validator as type class."""

        class CustomType:
            def __init__(self, value: str) -> None:
                if not value.startswith("custom:"):
                    msg = "Must start with 'custom:'"
                    raise ValueError(msg)
                self.value = value

            def __str__(self) -> str:
                return self.value

            @classmethod
            def __get_pydantic_core_schema__(
                cls,
                source_type: Any,  # noqa: ANN401
                handler: GetCoreSchemaHandler,
            ) -> CoreSchema:
                return core_schema.no_info_after_validator_function(
                    cls,
                    handler(str),
                    serialization=core_schema.plain_serializer_function_ser_schema(
                        lambda x: x.value,
                        return_schema=core_schema.str_schema(),
                    ),
                )

        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "field": {"type": "string", "format": "custom"},
            },
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema, format_validators={"custom": CustomType})

        instance = model(field="custom:value")
        assert instance.model_dump() == snapshot(
            {
                "field": "custom:value",
            }
        )

    def test_native_python_types_as_validators(self) -> None:
        """Test native Python types (datetime, UUID, etc.) as format validators."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "created_at": {"type": "string", "format": "date-time"},
                "email": {"type": "string", "format": "email"},
                "id": {"type": "string", "format": "uuid"},
                "ip": {"type": "string", "format": "ipv4"},
            },
            "required": ["created_at", "email", "id", "ip"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(
            schema,
            format_validators={
                "date-time": datetime,
                "email": Email,
                "uuid": UUID_FORMAT,
                "ipv4": IPv4Address,
            },
        )

        annotations = model.model_fields
        assert annotations["created_at"].annotation is datetime
        assert annotations["email"].annotation is str
        assert annotations["id"].annotation is UUID
        assert annotations["ip"].annotation is IPv4Address

        instance = model(
            created_at="2024-01-15T10:30:00",
            email="test@example.com",
            id="550e8400-e29b-41d4-a716-446655440000",
            ip="192.168.1.1",
        )
        assert isinstance(instance.created_at, datetime)  # type: ignore[attr-defined]
        assert isinstance(instance.email, str)  # type: ignore[attr-defined]
        assert isinstance(instance.id, UUID)  # type: ignore[attr-defined]
        assert isinstance(instance.ip, IPv4Address)  # type: ignore[attr-defined]

    def test_schema_format_email(self) -> None:
        """Test SchemaFormat EMAIL validator with to_model."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "email": {"type": "string", "format": "email"},
            },
            "required": ["email"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema, format_validators={"email": Email})

        instance = model(email="alice@example.com")
        assert instance.model_dump() == snapshot(
            {
                "email": "alice@example.com",
            }
        )

        with pytest.raises(ValidationError):
            model(email="not-an-email")

    def test_schema_format_date_time(self) -> None:
        """Test SchemaFormat DATE_TIME validator with to_model."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "created_at": {"type": "string", "format": "date-time"},
            },
            "required": ["created_at"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema, format_validators={"date-time": DateTime})

        instance = model(created_at="2024-01-15T10:30:00Z")

        assert instance.model_dump() == snapshot(
            {
                "created_at": datetime(
                    year=2024,
                    month=1,
                    day=15,
                    hour=10,
                    minute=30,
                    tzinfo=UTC,
                ),
            }
        )

        with pytest.raises(ValidationError):
            model(created_at="not-a-datetime")

    def test_schema_format_uuid(self) -> None:
        """Test SchemaFormat UUID validator with to_model."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "id": {"type": "string", "format": "uuid"},
            },
            "required": ["id"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema, format_validators={"uuid": UUID_FORMAT})

        instance = model(id="550e8400-e29b-41d4-a716-446655440000")
        assert instance.model_dump() == snapshot(
            {
                "id": UUID("550e8400-e29b-41d4-a716-446655440000"),
            }
        )

        with pytest.raises(ValidationError):
            model(id="not-a-uuid")

    def test_schema_format_ipv4(self) -> None:
        """Test SchemaFormat IPV4 validator with to_model."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "ip": {"type": "string", "format": "ipv4"},
            },
            "required": ["ip"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema, format_validators={"ipv4": IPv4})

        instance = model(ip="192.168.1.1")
        assert instance.model_dump() == snapshot(
            {
                "ip": IPv4Address("192.168.1.1"),
            }
        )

        with pytest.raises(ValidationError):
            model(ip="999.999.999.999")

    def test_schema_format_uri(self) -> None:
        """Test SchemaFormat URI validator with to_model."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "website": {"type": "string", "format": "uri"},
            },
            "required": ["website"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema, format_validators={"uri": Uri})

        instance = model(website="https://example.com")
        assert instance.model_dump() == snapshot(
            {
                "website": "https://example.com",
            }
        )

        with pytest.raises(ValidationError):
            model(website="example.com")

    def test_schema_format_multiple_formats(self) -> None:
        """Test multiple SchemaFormat validators in one model."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "email": {"type": "string", "format": "email"},
                "website": {"type": "string", "format": "uri"},
                "created_at": {"type": "string", "format": "date-time"},
                "id": {"type": "string", "format": "uuid"},
                "ip": {"type": "string", "format": "ipv4"},
            },
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(
            schema,
            format_validators={
                "email": Email,
                "uri": Uri,
                "date-time": DateTime,
                "uuid": UUID_FORMAT,
                "ipv4": IPv4,
            },
        )

        instance = model(
            email="alice@example.com",
            website="https://example.com",
            created_at="2024-01-15T10:30:00Z",
            id="550e8400-e29b-41d4-a716-446655440000",
            ip="192.168.1.1",
        )

        assert instance.model_dump() == snapshot(
            {
                "email": "alice@example.com",
                "website": "https://example.com",
                "created_at": datetime(
                    year=2024,
                    month=1,
                    day=15,
                    hour=10,
                    minute=30,
                    tzinfo=UTC,
                ),
                "id": UUID("550e8400-e29b-41d4-a716-446655440000"),
                "ip": IPv4Address("192.168.1.1"),
            }
        )


class TestFieldInfoMetadata:
    """Tests for JSON Schema metadata passed through to Pydantic `FieldInfo`."""

    def test_title_and_description(self) -> None:
        """Test `title` and `description` propagate to `FieldInfo`."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "title": "Full Name",
                    "description": "The user's full legal name.",
                },
            },
            "required": ["name"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        field_info: FieldInfo = model.model_fields["name"]
        assert field_info.title == "Full Name"
        assert field_info.description == "The user's full legal name."

    def test_examples(self) -> None:
        """Test `examples` propagate to `FieldInfo`."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "email": {
                    "type": "string",
                    "examples": ["user@example.com", "admin@example.com"],
                },
            },
            "required": ["email"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        field_info: FieldInfo = model.model_fields["email"]
        assert field_info.examples == snapshot(["user@example.com", "admin@example.com"])

    def test_exclusive_minimum_and_maximum(self) -> None:
        """Test `exclusiveMinimum` and `exclusiveMaximum` map to `gt` and `lt`."""
        exclusive_min: int = 0
        exclusive_max: int = 100
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "score": {
                    "type": "number",
                    "exclusiveMinimum": exclusive_min,
                    "exclusiveMaximum": exclusive_max,
                },
            },
            "required": ["score"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        field_info: FieldInfo = model.model_fields["score"]
        assert field_info.metadata == snapshot([Gt(gt=0.0), Lt(lt=100.0)])


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
        }

        converter = SchemaConverter()
        schema = Schema.model_validate(schema_raw)
        model = converter.convert_schema(schema)

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
