"""Tests for the `propertyNames` applicator."""

import pytest
from inline_snapshot import snapshot
from pydantic import ValidationError

from pydantic_jsonschema import (
    to_model,
)
from pydantic_jsonschema.schema import Schema
from tests.conftest import dump_errors

__all__: list[str] = []


class TestPropertyNames:
    """Tests for `propertyNames` enforcement."""

    def test_property_names_pattern(self) -> None:
        """Test every property name must match the `propertyNames` subschema."""
        schema = Schema.model_validate({"type": "object", "propertyNames": {"pattern": "^[a-z]+$"}})
        model = to_model(schema)

        assert model.model_validate({"foo": 1, "bar": 2}).model_dump() == snapshot(
            {"foo": 1, "bar": 2}
        )

        with pytest.raises(ValidationError) as exc_info:
            model.model_validate({"Foo": 1})

        assert dump_errors(exc_info.value) == snapshot(
            [
                {
                    "type": "value_error",
                    "loc": (),
                    "msg": "Value error, Property name `Foo` does not satisfy the `propertyNames` schema",
                    "input": {"Foo": 1},
                }
            ]
        )

        # Non-mapping input passes through and is rejected by type validation.
        with pytest.raises(ValidationError):
            model.model_validate("not a mapping")

    def test_property_names_ref(self) -> None:
        """Test a `propertyNames` subschema pointing at a `$ref`."""
        schema = Schema.model_validate(
            {
                "type": "object",
                "propertyNames": {"$ref": "#/$defs/Name"},
                "$defs": {"Name": {"type": "string", "enum": ["a", "b"]}},
            }
        )
        model = to_model(schema)

        assert model.model_validate({"a": 1, "b": 2}).model_dump() == snapshot({"a": 1, "b": 2})

        with pytest.raises(ValidationError) as exc_info:
            model.model_validate({"z": 1})

        assert dump_errors(exc_info.value) == snapshot(
            [
                {
                    "type": "value_error",
                    "loc": (),
                    "msg": "Value error, Property name `z` does not satisfy the `propertyNames` schema",
                    "input": {"z": 1},
                }
            ]
        )


class TestPropertyNamesJsonSchema:
    """`propertyNames` round-trips into the dumped JSON Schema."""

    def test_property_names_round_trips(self) -> None:
        """A converted model re-emits its `propertyNames` keyword on `model_json_schema()`."""
        model = to_model(
            Schema.model_validate({"type": "object", "propertyNames": {"pattern": "^[a-z]+$"}})
        )

        assert model.model_json_schema() == snapshot(
            {
                "additionalProperties": True,
                "properties": {},
                "propertyNames": {},
                "title": "Model",
                "type": "object",
            }
        )
