"""Tests for `$ref` / `$defs` reference resolution."""

from typing import Annotated, Final

import pytest
from inline_snapshot import snapshot
from pydantic import BaseModel, JsonValue, StringConstraints, ValidationError

from pydantic_jsonschema import (
    SchemaConverter,
    to_model,
)
from pydantic_jsonschema._compat import MISSING
from pydantic_jsonschema.exceptions import SchemaConversionError, SchemaReferenceError
from pydantic_jsonschema.schema import Reference, Schema
from tests.conftest import SchemaRaw

__all__: list[str] = []

type _LowercaseType = Annotated[str, StringConstraints(pattern="^[a-z]*$")]

_STRING_DEF: Final[SchemaRaw] = {"type": "string", "maxLength": 3}
_OBJECT_DEF: Final[SchemaRaw] = {
    "type": "object",
    "properties": {"a": {"type": "integer"}},
    "required": ["a"],
}
_RECURSIVE_DEF: Final[SchemaRaw] = {
    "type": "object",
    "properties": {
        "v": {"type": "integer"},
        "next": {"$ref": "#/$defs/N", "required": ["v"]},
    },
}


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

    @pytest.mark.parametrize(
        "field_schema",
        [
            pytest.param({"$ref": "#/$defs/DoesNotExist"}, id="property"),
            pytest.param(
                {"anyOf": [{"$ref": "#/$defs/DoesNotExist"}, {"type": "null"}]},
                id="any-of",
            ),
        ],
    )
    def test_invalid_reference_error(self, field_schema: SchemaRaw) -> None:
        """Test invalid reference raises error."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {"field": field_schema},
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

    def test_reference_field_takes_def_metadata(self) -> None:
        """Test a `$ref` property takes its field metadata from the def it points at."""
        schema = Schema.model_validate(
            {
                "$defs": {"N": {"type": "integer", "description": "count"}},
                "type": "object",
                "properties": {"n": {"$ref": "#/$defs/N"}},
            }
        )
        model = to_model(schema)

        assert model.model_fields["n"].description == "count"

    @pytest.mark.parametrize(
        ("definition", "valid", "invalid"),
        [
            pytest.param({"type": "integer", "minimum": 0}, 1, -1, id="minimum"),
            pytest.param({"type": "string", "minLength": 3}, "abcd", "ab", id="min-length"),
            pytest.param({"type": "array", "maxItems": 1}, [1], [1, 2], id="max-items"),
        ],
    )
    def test_reference_to_a_bounded_scalar_def(
        self,
        *,
        definition: SchemaRaw,
        valid: JsonValue,
        invalid: JsonValue,
    ) -> None:
        """Test a `$ref` to a scalar def with a bound checks the bound once, on the def's value."""
        schema = Schema.model_validate(
            {
                "$defs": {"N": definition},
                "type": "object",
                "properties": {"n": {"$ref": "#/$defs/N"}},
                "required": ["n"],
            }
        )
        model = to_model(schema)

        assert model.model_validate({"n": valid}).model_dump() == {"n": valid}

        with pytest.raises(ValidationError):
            model.model_validate({"n": invalid})

    def test_dumped_single_scalar_all_of_loads_back(self) -> None:
        """Test the dump of a nested one-branch scalar `allOf` loads back and checks the bound."""
        schema = Schema.model_validate(
            {
                "type": "object",
                "properties": {"v": {"allOf": [{"type": "string", "minLength": 3}]}},
                "required": ["v"],
            }
        )
        dumped = to_model(schema).model_json_schema()
        model = to_model(Schema.model_validate(dumped))

        assert model.model_validate({"v": "abcd"}).model_dump() == snapshot({"v": "abcd"})

        with pytest.raises(ValidationError):
            model.model_validate({"v": "ab"})

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


class TestRecursiveReferences:
    """A `$def` may reference itself or another def cyclically (tree / linked-list shapes)."""

    def test_self_referential_ref(self) -> None:
        """A def whose property points at itself converts and validates nested data."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {"head": {"$ref": "#/$defs/Node"}},
            "required": ["head"],
            "$defs": {
                "Node": {
                    "type": "object",
                    "properties": {
                        "value": {"type": "integer"},
                        "next": {"anyOf": [{"$ref": "#/$defs/Node"}, {"type": "null"}]},
                    },
                    "required": ["value"],
                },
            },
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        instance = model(head={"value": 1, "next": {"value": 2, "next": None}})
        assert instance.model_dump() == snapshot(
            {"head": {"value": 1, "next": {"value": 2, "next": None}}}
        )

    def test_self_referential_ref_rejects_invalid(self) -> None:
        """The recursive type still enforces its constraints at every depth."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {"head": {"$ref": "#/$defs/Node"}},
            "required": ["head"],
            "$defs": {
                "Node": {
                    "type": "object",
                    "properties": {
                        "value": {"type": "integer"},
                        "next": {"anyOf": [{"$ref": "#/$defs/Node"}, {"type": "null"}]},
                    },
                    "required": ["value"],
                },
            },
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        with pytest.raises(ValidationError):
            model(head={"value": 1, "next": {"value": "not-an-int", "next": None}})

    def test_mutually_referential_refs(self) -> None:
        """Two defs referencing each other convert regardless of `$defs` key order."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {"a": {"$ref": "#/$defs/A"}},
            "required": ["a"],
            "$defs": {
                "B": {
                    "type": "object",
                    "properties": {
                        "label": {"type": "string"},
                        "a": {"anyOf": [{"$ref": "#/$defs/A"}, {"type": "null"}]},
                    },
                    "required": ["label"],
                },
                "A": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "b": {"anyOf": [{"$ref": "#/$defs/B"}, {"type": "null"}]},
                    },
                    "required": ["id"],
                },
            },
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        instance = model(a={"id": 1, "b": {"label": "x", "a": None}})
        assert instance.model_dump() == snapshot({"a": {"id": 1, "b": {"label": "x", "a": None}}})

    def test_direct_self_referential_ref(self) -> None:
        """A direct (non-composition) optional `$ref` to the def being built defers correctly."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {"head": {"$ref": "#/$defs/Node"}},
            "required": ["head"],
            "$defs": {
                "Node": {
                    "type": "object",
                    "properties": {
                        "value": {"type": "integer"},
                        "child": {"$ref": "#/$defs/Node"},
                    },
                    "required": ["value"],
                },
            },
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        instance = model(head={"value": 1, "child": {"value": 2}})
        assert instance.model_dump() == snapshot({"head": {"value": 1, "child": {"value": 2}}})

    def test_alias_before_recursive_target(self) -> None:
        """An alias declared before its recursive target resolves to the target's one model."""
        schema = Schema.model_validate(
            {
                "$defs": {
                    "A": {"$ref": "#/$defs/B"},
                    "B": {
                        "type": "object",
                        "properties": {"next": {"$ref": "#/$defs/B"}},
                    },
                },
                "type": "object",
                "properties": {"a": {"$ref": "#/$defs/A"}, "b": {"$ref": "#/$defs/B"}},
                "required": ["a", "b"],
            }
        )
        model = to_model(schema)

        instance = model.model_validate({"a": {"next": {}}, "b": {}})

        assert {type(instance.a), type(instance.a.next), type(instance.b)} == {type(instance.b)}  # type: ignore[attr-defined]

    @pytest.mark.parametrize(
        ("defs", "valid", "invalid"),
        [
            pytest.param(
                {
                    "A": {
                        "type": "object",
                        "properties": {"b": {"$ref": "#/$defs/B"}},
                        "required": ["b"],
                    },
                    "B": {"type": "integer"},
                },
                {"b": 1},
                {"b": "x"},
                id="property",
            ),
            pytest.param(
                {
                    "A": {"allOf": [{"$ref": "#/$defs/B"}]},
                    "B": {
                        "type": "object",
                        "properties": {"b": {"type": "integer"}},
                        "required": ["b"],
                    },
                },
                {"b": 1},
                {"b": "x"},
                id="all-of",
            ),
            pytest.param(
                {
                    "A": {
                        "type": "object",
                        "properties": {"b": {"$ref": "#/$defs/B"}},
                        "required": ["b"],
                    },
                    "B": {
                        "type": "object",
                        "properties": {
                            "next": {"$ref": "#/$defs/B"},
                            "value": {"type": "integer"},
                        },
                        "required": ["value"],
                    },
                },
                {"b": {"value": 1, "next": {"value": 2}}},
                {"b": {"value": "x"}},
                id="self-referential",
            ),
            pytest.param(
                {
                    "A": {"properties": {"b": {"$ref": "#/$defs/B"}}, "required": ["b"]},
                    "B": {"properties": {"a": {"$ref": "#/$defs/A"}}, "required": ["value"]},
                },
                {"b": {"value": 1, "a": {"b": {"value": 2}}}},
                {"b": {}},
                id="untyped-mutual",
            ),
        ],
    )
    def test_ref_to_later_def(
        self,
        defs: dict[str, SchemaRaw],
        valid: SchemaRaw,
        invalid: SchemaRaw,
    ) -> None:
        """A `$ref` resolves to a def declared after the def that refers to it."""
        schema = Schema.model_validate(
            {
                "type": "object",
                "properties": {"a": {"$ref": "#/$defs/A"}},
                "required": ["a"],
                "$defs": defs,
            }
        )
        model = to_model(schema)

        assert model.model_validate({"a": valid}).model_dump(exclude_unset=True) == {"a": valid}

        with pytest.raises(ValidationError) as exc_info:
            model.model_validate({"a": invalid})

        assert [error["loc"][:2] for error in exc_info.value.errors()] == [("a", "b")]

    @pytest.mark.parametrize(
        "branch",
        [
            pytest.param({"additionalProperties": False}, id="closed"),
            pytest.param({"properties": {"b": {"type": "string"}}}, id="shadowed"),
        ],
    )
    @pytest.mark.parametrize(
        "branch_name",
        [
            pytest.param("A", id="before"),
            pytest.param("Z", id="after"),
        ],
    )
    def test_recursive_all_of_branch_def_in_any_order(
        self,
        *,
        branch: SchemaRaw,
        branch_name: str,
    ) -> None:
        """An `allOf` branch checked on its own works, and dumps, wherever its def sorts."""
        branch_properties: SchemaRaw = branch.get("properties", {})
        schema = Schema.model_validate(
            {
                "type": "object",
                "properties": {"t": {"$ref": "#/$defs/T"}},
                "required": ["t"],
                "$defs": {
                    "B": {"type": "object", "properties": {"b": {"type": "integer"}}},
                    "T": {"allOf": [{"$ref": f"#/$defs/{branch_name}"}, {"$ref": "#/$defs/B"}]},
                    branch_name: {
                        **branch,
                        "type": "object",
                        "properties": {
                            **branch_properties,
                            "c": {"type": "array", "items": {"$ref": "#/$defs/T"}},
                        },
                    },
                },
            }
        )
        model = to_model(schema)
        reloaded = to_model(Schema.model_validate(model.model_json_schema()))

        valid: SchemaRaw = {"t": {"c": [{"c": []}]}}
        for current in (model, reloaded):
            assert current.model_validate(valid).model_dump(exclude_unset=True) == valid

            with pytest.raises(ValidationError):
                current.model_validate({"t": {"c": [{"b": 1}]}})


def _in_property(subschema: SchemaRaw, /) -> SchemaRaw:
    return {
        "type": "object",
        "properties": {"p": subschema},
        "required": ["p"],
        "$defs": {"S": _STRING_DEF, "O": _OBJECT_DEF},
    }


class TestReferenceSiblings:
    """A `$ref` beside other keywords checks both the target and the keywords."""

    @pytest.mark.parametrize(
        ("schema_raw", "valid", "invalid"),
        [
            pytest.param(
                {"$defs": {"S": _STRING_DEF}, "$ref": "#/$defs/S"},
                "ab",
                "abcd",
                id="root-scalar",
            ),
            pytest.param(
                {"$defs": {"O": _OBJECT_DEF}, "$ref": "#/$defs/O"},
                {"a": 1},
                {"a": "x"},
                id="root-object",
            ),
            pytest.param(
                {"$defs": {"S": _STRING_DEF}, "$ref": "#/$defs/S", "minLength": 2},
                "ab",
                "a",
                id="root-with-sibling",
            ),
            pytest.param(
                _in_property({"$ref": "#/$defs/S", "minLength": 2}),
                {"p": "ab"},
                {"p": "a"},
                id="property-sibling",
            ),
            pytest.param(
                _in_property({"$ref": "#/$defs/S", "minLength": 2}),
                {"p": "ab"},
                {"p": "abcd"},
                id="property-target",
            ),
            pytest.param(
                _in_property({"$ref": "#/$defs/O", "required": ["b"]}),
                {"p": {"a": 1, "b": 2}},
                {"p": {"a": 1}},
                id="property-required",
            ),
            pytest.param(
                _in_property({"$ref": "#/$defs/O", "properties": {"b": {"type": "string"}}}),
                {"p": {"a": 1, "b": "x"}},
                {"p": {"a": 1, "b": 2}},
                id="property-nested-schema-sibling",
            ),
            pytest.param(
                _in_property({"$ref": "#/$defs/O", "properties": {"b": {"type": "string"}}}),
                {"p": {"a": 1, "b": "x"}},
                {"p": {"b": "x"}},
                id="property-nested-schema-target",
            ),
            pytest.param(
                _in_property({"$ref": "#/$defs/S", "not": {"const": "ab"}}),
                {"p": "abc"},
                {"p": "ab"},
                id="property-not",
            ),
            pytest.param(
                {
                    "type": "array",
                    "items": {"$ref": "#/$defs/S", "maxLength": 1},
                    "$defs": {"S": _STRING_DEF},
                },
                ["a"],
                ["ab"],
                id="items",
            ),
            pytest.param(
                {
                    "type": "object",
                    "properties": {"p": {"$ref": "#/$defs/A"}},
                    "required": ["p"],
                    "$defs": {"S": _STRING_DEF, "A": {"$ref": "#/$defs/S", "minLength": 2}},
                },
                {"p": "ab"},
                {"p": "a"},
                id="def-alias",
            ),
            pytest.param(
                _in_property({"$ref": "#/$defs/S", "allOf": [{"minLength": 2}]}),
                {"p": "ab"},
                {"p": "a"},
                id="all-of-sibling",
            ),
            pytest.param(
                _in_property(
                    {"anyOf": [{"$ref": "#/$defs/S", "minLength": 2}, {"type": "integer"}]}
                ),
                {"p": "ab"},
                {"p": "a"},
                id="any-of-branch",
            ),
            pytest.param(
                _in_property(
                    {"type": "array", "prefixItems": [{"$ref": "#/$defs/S", "minLength": 2}]}
                ),
                {"p": ["ab"]},
                {"p": ["a"]},
                id="prefix-items-branch",
            ),
            pytest.param(
                _in_property({"$ref": "#/$defs/S", "enum": ["ab", "abcd"]}),
                {"p": "ab"},
                {"p": "abcd"},
                id="enum-sibling",
            ),
            pytest.param(
                _in_property({"$ref": "#/$defs/S", "anyOf": [{"type": "string", "minLength": 2}]}),
                {"p": "ab"},
                {"p": "abcd"},
                id="any-of-sibling",
            ),
            pytest.param(
                _in_property({"$ref": "#/$defs/S", "oneOf": [{"type": "string", "minLength": 2}]}),
                {"p": "ab"},
                {"p": "abcd"},
                id="one-of-sibling",
            ),
            pytest.param(
                {
                    "type": "object",
                    "properties": {
                        "p": {
                            "$ref": "#/$defs/A",
                            "items": {"$ref": "#/$defs/S", "minLength": 2},
                            "minItems": 1,
                            "maxItems": 5,
                        },
                    },
                    "required": ["p"],
                    "$defs": {"A": {"type": "array"}, "S": _STRING_DEF},
                },
                {"p": ["ab"]},
                {"p": ["a"]},
                id="ref-inside-a-moved-ref",
            ),
        ],
    )
    def test_checks_target_and_siblings(
        self,
        *,
        schema_raw: SchemaRaw,
        valid: JsonValue,
        invalid: JsonValue,
    ) -> None:
        """The value must satisfy the target and the keywords beside `$ref`, also after a dump."""
        model = to_model(Schema.model_validate(schema_raw))
        reloaded = to_model(Schema.model_validate(model.model_json_schema()))

        for current in (model, reloaded):
            current.model_validate(valid)

            with pytest.raises(ValidationError):
                current.model_validate(invalid)

    @pytest.mark.parametrize(
        ("schema_raw", "valid", "invalid"),
        [
            pytest.param(
                {
                    "$defs": {"N": _RECURSIVE_DEF},
                    "$ref": "#/$defs/N",
                },
                {"v": 1, "next": {"v": 2}},
                {"v": 1, "next": {}},
                id="recursive",
            ),
            pytest.param(
                {
                    "$defs": {
                        "N": {
                            "type": "object",
                            "properties": {
                                "kids": {
                                    "type": "array",
                                    "items": {"$ref": "#/$defs/N", "minProperties": 1},
                                },
                            },
                        },
                    },
                    "$ref": "#/$defs/N",
                },
                {"kids": [{"kids": []}]},
                {"kids": [{}]},
                id="recursive-items",
            ),
            pytest.param(
                {
                    "$defs": {
                        "N": {
                            "type": "object",
                            "properties": {
                                "v": {"type": "integer"},
                                "next": {"allOf": [{"$ref": "#/$defs/N"}], "required": ["v"]},
                            },
                        },
                    },
                    "$ref": "#/$defs/N",
                },
                {"v": 1, "next": {"v": 2}},
                {"v": 1, "next": {}},
                id="recursive-explicit-all-of",
            ),
            pytest.param(
                {
                    "$defs": {
                        "N": {
                            "type": "object",
                            "properties": {
                                "v": {"type": "integer"},
                                "next": {"$ref": "#/$defs/N", "allOf": [{"required": ["v"]}]},
                            },
                        },
                    },
                    "$ref": "#/$defs/N",
                },
                {"v": 1, "next": {"v": 2}},
                {"v": 1, "next": {}},
                id="recursive-all-of-sibling",
            ),
            pytest.param(
                {
                    "$defs": {"N": {"properties": {"next": {"$ref": "#/$defs/N", "minimum": 2}}}},
                    "$ref": "#/$defs/N",
                },
                {"next": 3},
                {"next": 1},
                id="recursive-bound-sibling",
            ),
        ],
    )
    def test_recursive_ref_checks_target_and_siblings(
        self,
        *,
        schema_raw: SchemaRaw,
        valid: JsonValue,
        invalid: JsonValue,
    ) -> None:
        """A `$ref` to the def it sits in checks the def and the keywords beside it."""
        model = to_model(Schema.model_validate(schema_raw))

        model.model_validate(valid)

        with pytest.raises(ValidationError):
            model.model_validate(invalid)

    @pytest.mark.parametrize(
        "value",
        [
            pytest.param({}, id="object"),
            pytest.param("x", id="string"),
        ],
    )
    def test_recursive_bound_sibling_ignores_a_non_number(self, *, value: JsonValue) -> None:
        """A bound beside a `$ref` to the def it sits in applies to numbers only."""
        schema = Schema.model_validate(
            {
                "$defs": {"N": {"properties": {"next": {"$ref": "#/$defs/N", "minimum": 2}}}},
                "$ref": "#/$defs/N",
            }
        )

        to_model(schema).model_validate({"next": value})

    @pytest.mark.parametrize(
        ("annotations", "parsed_type"),
        [
            pytest.param({"title": "Titled"}, Reference, id="parsed-as-reference"),
            pytest.param(
                {"title": "Titled", "description": "D", "default": {"a": 1}},
                Schema,
                id="parsed-as-schema",
            ),
        ],
    )
    def test_annotation_siblings_keep_the_shared_model(
        self,
        *,
        annotations: SchemaRaw,
        parsed_type: type[Schema | Reference],
    ) -> None:
        """A `$ref` beside annotations only resolves to the same model as a plain `$ref`."""
        schema = Schema.model_validate(
            {
                "type": "object",
                "properties": {
                    "plain": {"$ref": "#/$defs/O"},
                    "titled": {"$ref": "#/$defs/O", **annotations},
                },
                "required": ["plain", "titled"],
                "$defs": {"O": _OBJECT_DEF},
            }
        )
        assert schema.properties is not MISSING
        assert type(schema.properties["titled"]) is parsed_type

        model = to_model(schema)

        fields = model.model_fields
        assert fields["titled"].annotation == fields["plain"].annotation

    def test_annotation_siblings_of_a_schema_node_apply(self) -> None:
        """`title`, `description` and `default` beside a `$ref` parsed as a `Schema` apply."""
        schema = Schema.model_validate(
            {
                "type": "object",
                "properties": {
                    "p": {
                        "$ref": "#/$defs/O",
                        "title": "T",
                        "description": "D",
                        "default": {"a": 1},
                    },
                },
                "$defs": {"O": _OBJECT_DEF},
            }
        )
        model = to_model(schema)

        field = model.model_fields["p"]
        assert (field.title, field.description, field.default) == ("T", "D", {"a": 1})

        with pytest.raises(ValidationError):
            model.model_validate({"p": {"a": "x"}})

    def test_const_sibling_checks_the_target(self) -> None:
        """A `const` beside `$ref` still checks the target, which here no value satisfies."""
        model = to_model(
            Schema.model_validate(_in_property({"$ref": "#/$defs/S", "const": "abcd"}))
        )

        with pytest.raises(ValidationError):
            model.model_validate({"p": "abcd"})

    @pytest.mark.parametrize(
        ("attribute", "value"),
        [
            pytest.param("title", "T", id="title"),
            pytest.param("description", "D", id="description"),
            pytest.param("default", {"a": 1}, id="default"),
        ],
    )
    def test_annotation_sibling_of_a_reference_applies(
        self,
        *,
        attribute: str,
        value: JsonValue,
    ) -> None:
        """One annotation beside `$ref`, parsed as a `Reference`, lands on the field."""
        schema = Schema.model_validate(
            {
                "type": "object",
                "properties": {"p": {"$ref": "#/$defs/O", attribute: value}},
                "$defs": {"O": _OBJECT_DEF},
            }
        )
        assert schema.properties is not MISSING
        assert type(schema.properties["p"]) is Reference

        field = to_model(schema).model_fields["p"]

        assert getattr(field, attribute) == value

    @pytest.mark.parametrize(
        ("property_schema", "title"),
        [
            pytest.param({"$ref": "#/$defs/S"}, "From the def", id="plain"),
            pytest.param(
                {"$ref": "#/$defs/S", "minLength": 1},
                "From the def",
                id="validating-sibling",
            ),
            pytest.param({"$ref": "#/$defs/S", "title": "T"}, "T", id="annotation-sibling"),
            pytest.param({"allOf": [{"$ref": "#/$defs/S"}]}, "From the def", id="explicit-all-of"),
        ],
    )
    def test_definition_metadata_reaches_the_field(
        self,
        *,
        property_schema: SchemaRaw,
        title: str,
    ) -> None:
        """A field takes the metadata of its `$ref` target it does not set."""
        definition = {
            **_STRING_DEF,
            "title": "From the def",
            "description": "From the def",
            "default": "xy",
            "examples": ["ab"],
        }
        schema = Schema.model_validate(
            {
                "type": "object",
                "properties": {"p": property_schema},
                "$defs": {"S": definition},
            }
        )

        field = to_model(schema).model_fields["p"]

        assert (field.title, field.description, field.default, field.examples) == (
            title,
            "From the def",
            "xy",
            ["ab"],
        )

    @pytest.mark.parametrize(
        "sibling",
        [
            pytest.param({"title": 5}, id="annotation"),
            pytest.param({"examples": "x"}, id="annotation-not-a-list"),
            pytest.param({"minLength": "a"}, id="validating"),
            pytest.param({"allOf": {"minLength": 2}}, id="all-of-not-a-list"),
        ],
    )
    def test_invalid_sibling_raises(self, *, sibling: SchemaRaw) -> None:
        """A keyword of the wrong type beside `$ref` is refused, naming it and the `$ref`."""
        schema = Schema.model_validate(_in_property({"$ref": "#/$defs/S", **sibling}))
        [keyword] = sibling

        with pytest.raises(SchemaReferenceError, match=f"beside `\\$ref` at `{keyword}`") as raised:
            to_model(schema)

        assert raised.value.path == ["properties.p"]

    @pytest.mark.parametrize(
        ("sibling", "invalid"),
        [
            pytest.param({"enum": ["ab", "abcd"]}, "xy", id="enum"),
            pytest.param({"const": "ab"}, "xy", id="const"),
            pytest.param({"anyOf": [{"type": "string", "minLength": 2}]}, "a", id="any-of"),
            pytest.param({"oneOf": [{"type": "string", "minLength": 2}]}, "a", id="one-of"),
        ],
    )
    def test_own_branch_sibling_checks(
        self,
        *,
        sibling: SchemaRaw,
        invalid: str,
    ) -> None:
        """A keyword in its own `allOf` branch rejects a value the target accepts."""
        model = to_model(Schema.model_validate(_in_property({"$ref": "#/$defs/S", **sibling})))

        with pytest.raises(ValidationError):
            model.model_validate({"p": invalid})

    def test_own_metadata_wins_over_the_definition(self) -> None:
        """A field beside a validating keyword keeps its own metadata over its target's."""
        definition = {
            **_STRING_DEF,
            "title": "S title",
            "description": "S desc",
            "default": "xy",
            "examples": ["ab"],
        }
        property_schema = {
            "$ref": "#/$defs/S",
            "minLength": 1,
            "title": "P title",
            "description": "P desc",
            "default": "zz",
            "examples": ["cd"],
        }
        schema = Schema.model_validate(
            {
                "type": "object",
                "properties": {"p": property_schema},
                "$defs": {"S": definition},
            }
        )

        field = to_model(schema).model_fields["p"]

        assert (field.title, field.description, field.default, field.examples) == (
            "P title",
            "P desc",
            "zz",
            ["cd"],
        )

    def test_hand_built_reference_checks_a_nested_ref(self) -> None:
        """A nested `$ref` beside a keyword is checked inside a `Reference` built in code."""
        reference = Reference.model_validate(
            {"$ref": "#/$defs/A", "items": {"$ref": "#/$defs/S", "minLength": 2}}
        )
        schema = Schema.model_validate(
            {
                "type": "object",
                "properties": {"p": reference},
                "required": ["p"],
                "$defs": {"A": {"type": "array"}, "S": _STRING_DEF},
            }
        )
        model = to_model(schema)
        model.model_validate({"p": ["ab"]})

        with pytest.raises(ValidationError):
            model.model_validate({"p": ["a"]})

    @pytest.mark.parametrize(
        "annotations",
        [
            pytest.param({"title": "Pet"}, id="parsed-as-reference"),
            pytest.param({"title": "Pet", "description": "D"}, id="parsed-as-schema"),
        ],
    )
    def test_annotated_union_branches_keep_the_discriminator(
        self,
        *,
        annotations: SchemaRaw,
    ) -> None:
        """Annotations beside each `$ref` branch of a `oneOf` keep the discriminated union."""
        schema = Schema.model_validate(
            {
                "type": "object",
                "properties": {
                    "pet": {
                        "oneOf": [
                            {"$ref": "#/$defs/Cat", **annotations},
                            {"$ref": "#/$defs/Dog", **annotations},
                        ],
                    },
                },
                "required": ["pet"],
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
            }
        )

        field = to_model(schema).model_fields["pet"]

        assert field.discriminator == "kind"

    @pytest.mark.parametrize(
        "defs",
        [
            pytest.param({"A": {"$ref": "#/$defs/A", "minLength": 1}}, id="self"),
            pytest.param(
                {
                    "A": {"$ref": "#/$defs/B", "minLength": 1},
                    "B": {"$ref": "#/$defs/A", "maxLength": 3},
                },
                id="cycle",
            ),
            pytest.param(
                {
                    "A": {
                        "allOf": [
                            {"$ref": "#/$defs/A"},
                            {"type": "object", "properties": {"x": {"type": "string"}}},
                        ],
                    },
                },
                id="beside-an-inline-object",
            ),
        ],
    )
    def test_def_inheriting_from_itself_raises(self, *, defs: dict[str, SchemaRaw]) -> None:
        """A def whose `$ref` beside other keywords leads back to itself is refused."""
        schema = Schema.model_validate(
            {"type": "object", "properties": {"p": {"$ref": "#/$defs/A"}}, "$defs": defs}
        )

        with pytest.raises(SchemaReferenceError, match="inside its own definition"):
            to_model(schema)

    def test_format_sibling_checks_with_a_formats_entry(self) -> None:
        """A `format` beside `$ref` checks the value once `formats` maps it to a type."""
        schema = Schema.model_validate(_in_property({"$ref": "#/$defs/S", "format": "lower"}))
        model = to_model(
            schema,
            formats={"lower": _LowercaseType},
        )

        model.model_validate({"p": "ab"})

        with pytest.raises(ValidationError):
            model.model_validate({"p": "AB"})

    @pytest.mark.parametrize(
        ("schema_raw", "path"),
        [
            pytest.param({"$ref": 5, "type": "string"}, [], id="root-number"),
            pytest.param({"$ref": None, "type": "string"}, [], id="root-null"),
            pytest.param(
                {
                    "type": "object",
                    "properties": {
                        "a": {
                            "type": "object",
                            "properties": {"p": {"$ref": 5, "type": "string"}},
                        },
                    },
                },
                ["properties.a", "properties.p"],
                id="nested-property",
            ),
            pytest.param(
                {"type": "array", "prefixItems": [{}, {"$ref": 5, "type": "string"}]},
                ["prefixItems[1]"],
                id="list-branch",
            ),
        ],
    )
    def test_non_string_ref_raises(
        self,
        *,
        schema_raw: SchemaRaw,
        path: list[str],
    ) -> None:
        """A `$ref` that is not a string is a reference error at its location, not a recursion."""
        schema = Schema.model_validate(schema_raw)

        with pytest.raises(SchemaReferenceError, match="must be a string") as raised:
            to_model(schema)

        assert raised.value.path == path
