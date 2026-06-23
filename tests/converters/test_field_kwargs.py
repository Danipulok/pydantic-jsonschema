"""Tests for field constraints, defaults, and `FieldInfo` metadata."""

from typing import TYPE_CHECKING, Any

import pytest
from annotated_types import Gt, Lt
from inline_snapshot import snapshot
from pydantic import JsonValue, ValidationError

from pydantic_jsonschema import (
    to_model,
)
from pydantic_jsonschema.schema import Schema
from tests.conftest import dump_errors

if TYPE_CHECKING:
    from pydantic.fields import FieldInfo

    from tests.conftest import SchemaRaw

__all__: list[str] = []


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
            "required": ["score"],
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
        """Test `uniqueItems` accepts distinct items and rejects duplicates."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "uniqueItems": True,
                },
            },
            "required": ["tags"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        instance = model(tags=["python", "coding", "dev"])
        assert instance.model_dump() == snapshot(
            {
                "tags": ["python", "coding", "dev"],
            }
        )

        with pytest.raises(ValidationError) as exc_info:
            model(tags=["dup", "dup"])

        assert dump_errors(exc_info.value) == snapshot(
            [
                {
                    "type": "value_error",
                    "loc": ("tags",),
                    "msg": "Value error, Array items must be unique",
                    "input": ["dup", "dup"],
                }
            ]
        )

    def test_unique_items_unhashable(self) -> None:
        """Test `uniqueItems` rejects duplicate object items (unhashable, no `set`)."""
        schema = Schema.model_validate(
            {"type": "array", "items": {"type": "object"}, "uniqueItems": True}
        )
        model = to_model(schema)

        assert model.model_validate([{"a": 1}, {"b": 2}]).model_dump() == snapshot(
            [{"a": 1}, {"b": 2}]
        )

        with pytest.raises(ValidationError) as exc_info:
            model.model_validate([{"a": 1}, {"a": 1}])

        assert dump_errors(exc_info.value) == snapshot(
            [
                {
                    "type": "value_error",
                    "loc": (),
                    "msg": "Value error, Array items must be unique",
                    "input": [{"a": 1}, {"a": 1}],
                }
            ]
        )

    def test_unique_items_false_is_noop(self) -> None:
        """Test `uniqueItems: false` imposes no constraint."""
        schema = Schema.model_validate(
            {"type": "array", "items": {"type": "integer"}, "uniqueItems": False}
        )
        model = to_model(schema)
        assert model.model_validate([1, 1, 1]).model_dump() == snapshot([1, 1, 1])


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
