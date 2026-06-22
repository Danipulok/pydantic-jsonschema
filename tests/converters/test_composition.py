"""Tests for `anyOf` / `oneOf` / `allOf` composition."""

from typing import TYPE_CHECKING

import pytest
from inline_snapshot import snapshot
from pydantic import ValidationError

from pydantic_jsonschema import (
    to_model,
)
from pydantic_jsonschema.types import Schema
from tests.conftest import dump_errors

if TYPE_CHECKING:
    from tests.conftest import SchemaRaw

__all__: list[str] = []


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
                    "required": ["age"],
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
                    "required": ["name"],
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
                            "required": ["a"],
                        },
                        {
                            "type": "object",
                            "properties": {"b": {"type": "integer"}},
                            "required": ["b"],
                        },
                    ],
                },
            },
            "required": ["combined"],
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
                    "required": ["age"],
                },
                {
                    "type": "object",
                    "properties": {
                        "email": {"type": "string"},
                    },
                    "required": ["email"],
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
            "required": ["value"],
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
            "required": ["multi_value"],
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
            "required": ["value"],
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
                    "required": ["a", "other"],
                },
                "TypeB": {
                    "type": "object",
                    "properties": {
                        "b": {"type": "integer"},
                    },
                    "required": ["b"],
                },
            },
            "type": "object",
            "properties": {
                "item": {"$ref": "#/$defs/TypeA"},
            },
            "required": ["item"],
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
            "required": ["value"],
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
            "required": ["value"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        instance = model(value=1.5)
        assert instance.model_dump() == snapshot({"value": 1.5})

        with pytest.raises(ValidationError) as exc_info:
            model(value=1)

        assert dump_errors(exc_info.value) == snapshot(
            [
                {
                    "type": "value_error",
                    "loc": ("value",),
                    "msg": "Value error, Input matches 2 `oneOf` branches, expected exactly 1",
                    "input": 1,
                }
            ]
        )

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
            "required": ["value"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        with pytest.raises(ValidationError) as exc_info:
            model(value=[1, 2, 3])

        assert dump_errors(exc_info.value) == snapshot(
            [
                {
                    "type": "value_error",
                    "loc": ("value",),
                    "msg": "Value error, Input matches 0 `oneOf` branches, expected exactly 1",
                    "input": [1, 2, 3],
                }
            ]
        )

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
                    "required": ["other"],
                },
                "TypeB": {
                    "type": "object",
                    "properties": {
                        "b": {"type": "integer"},
                    },
                    "required": ["b"],
                },
            },
            "type": "object",
            "properties": {
                "item": {"$ref": "#/$defs/TypeA"},
            },
            "required": ["item"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        instance = model(item={"other": {"b": 42}})
        assert instance.model_dump() == snapshot(
            {
                "item": {"other": {"b": 42}},
            }
        )


class TestCompositionWithSiblingType:
    """A `type` sibling to `anyOf` / `oneOf` constrains the union (keywords are conjunctive)."""

    def test_anyof_with_sibling_type_rejects_wrong_type(self) -> None:
        """`type` + `anyOf`: a value of the wrong type is rejected, not silently accepted."""
        schema_raw: SchemaRaw = {
            "type": "number",
            "anyOf": [{"minimum": 0, "maximum": 10}, {"minimum": 100}],
        }
        model = to_model(Schema.model_validate(schema_raw))

        assert model(5).model_dump() == snapshot(5)  # type: ignore[call-arg]

        with pytest.raises(ValidationError) as exc_info:
            model("hello")  # type: ignore[call-arg]
        assert dump_errors(exc_info.value) == snapshot(
            [
                {
                    "type": "float_parsing",
                    "loc": (),
                    "msg": "Input should be a valid number, unable to parse string as a number",
                    "input": "hello",
                }
            ]
        )

    def test_anyof_with_sibling_type_rejects_object(self) -> None:
        """`type` + `anyOf`: a non-scalar value is rejected by the sibling `type`."""
        schema_raw: SchemaRaw = {
            "type": "number",
            "anyOf": [{"minimum": 0, "maximum": 10}, {"minimum": 100}],
        }
        model = to_model(Schema.model_validate(schema_raw))

        with pytest.raises(ValidationError):
            model({"k": 1})  # type: ignore[call-arg]

    def test_multi_type_sibling_with_anyof(self) -> None:
        """A list-valued sibling `type` (`["integer", "string"]`) still guards the union."""
        schema_raw: SchemaRaw = {
            "type": ["integer", "string"],
            "anyOf": [{"minimum": 0}, {"minLength": 1}],
        }
        model = to_model(Schema.model_validate(schema_raw))

        assert model(5).model_dump() == snapshot(5)  # type: ignore[call-arg]
        assert model("hi").model_dump() == snapshot("hi")  # type: ignore[call-arg]

        with pytest.raises(ValidationError):
            model({"k": 1})  # type: ignore[call-arg]


class TestCompositionBranchConstraints:
    """`anyOf` / `oneOf` branches keep their own field-level constraints."""

    def test_anyof_branch_constraints_enforced(self) -> None:
        """An `anyOf` of constrained branches rejects a value outside every branch's range."""
        schema_raw: SchemaRaw = {
            "anyOf": [
                {"type": "integer", "minimum": 0, "maximum": 10},
                {"type": "integer", "minimum": 100, "maximum": 200},
            ],
        }
        model = to_model(Schema.model_validate(schema_raw))

        assert model(5).model_dump() == snapshot(5)  # type: ignore[call-arg]
        assert model(150).model_dump() == snapshot(150)  # type: ignore[call-arg]

        with pytest.raises(ValidationError):
            model(50)  # type: ignore[call-arg]  # in neither range

    def test_oneof_branch_constraints_enforced(self) -> None:
        """`oneOf` branch constraints make exactly-one-branch dispatch meaningful."""
        schema_raw: SchemaRaw = {
            "oneOf": [
                {"type": "integer", "minimum": 0, "maximum": 10},
                {"type": "integer", "minimum": 100, "maximum": 200},
            ],
        }
        model = to_model(Schema.model_validate(schema_raw))

        assert model(5).model_dump() == snapshot(5)  # type: ignore[call-arg]

        with pytest.raises(ValidationError):
            model(50)  # type: ignore[call-arg]  # matches no branch
