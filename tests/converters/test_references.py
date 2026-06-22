"""Tests for `$ref` / `$defs` reference resolution."""

from typing import TYPE_CHECKING

import pytest
from inline_snapshot import snapshot
from pydantic import BaseModel

from pydantic_jsonschema import (
    SchemaConverter,
    to_model,
)
from pydantic_jsonschema.exceptions import SchemaConversionError, SchemaReferenceError
from pydantic_jsonschema.types import Schema

if TYPE_CHECKING:
    from tests.conftest import SchemaRaw

__all__: list[str] = []


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
                    "required": ["street", "city"],
                },
            },
            "required": ["address"],
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
            "required": ["home"],
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
                    "required": ["name", "age"],
                },
                "Address": {
                    "type": "object",
                    "properties": {
                        "street": {"type": "string"},
                    },
                    "required": ["street"],
                },
                "Company": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                    },
                    "required": ["name"],
                },
            },
            "type": "object",
            "properties": {
                "owner": {"$ref": "#/$defs/Person"},
                "address": {"$ref": "#/$defs/Address"},
                "employer": {"$ref": "#/$defs/Company"},
            },
            "required": ["owner", "address", "employer"],
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
                    "required": ["name"],
                },
                "Address": {
                    "type": "object",
                    "properties": {
                        "street": {"type": "string"},
                        "city": {"$ref": "#/$defs/City"},
                    },
                    "required": ["street", "city"],
                },
            },
            "type": "object",
            "properties": {
                "home": {"$ref": "#/$defs/Address"},
            },
            "required": ["home"],
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
            "required": ["field"],
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
                    "required": ["email", "phone"],
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
                    "required": ["name", "value"],
                },
            },
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/Item"},
                },
            },
            "required": ["items"],
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
                    "required": ["name"],
                },
                "Article": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "author": {"$ref": "#/$defs/Author"},
                    },
                    "required": ["title", "author"],
                },
            },
            "type": "object",
            "properties": {
                "featured": {"$ref": "#/$defs/Article"},
            },
            "required": ["featured"],
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
            "required": ["address"],
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
                    "required": ["value"],
                },
            },
            "type": "object",
            "properties": {
                "field1": {"$ref": "#/$defs/CustomType"},
                "field2": {"$ref": "#/$defs/CustomType"},
            },
            "required": ["field1", "field2"],
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
                    "required": ["name"],
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
                    "required": ["street"],
                },
                "Location": {"$ref": "#/$defs/Address"},
            },
            "type": "object",
            "properties": {
                "home": {"$ref": "#/$defs/Location"},
            },
            "required": ["home"],
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
                    "required": ["value"],
                },
            },
            "type": "object",
            "properties": {
                "field": {"$ref": "#/$defs/Primary"},
            },
            "required": ["field"],
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
                                "required": ["nested"],
                            },
                        ],
                    },
                },
            },
            "required": ["items"],
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
                    "required": ["field"],
                },
            },
            "required": ["nested"],
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
            "required": ["address"],
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
                    "required": ["id", "name"],
                },
            },
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/Item"},
                },
            },
            "required": ["items"],
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
