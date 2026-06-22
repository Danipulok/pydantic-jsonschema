"""Tests for the `patternProperties` applicator."""

import pytest
from inline_snapshot import snapshot
from pydantic import ValidationError

from pydantic_jsonschema import (
    to_model,
)
from pydantic_jsonschema.types import Schema
from tests.conftest import dump_errors

__all__: list[str] = []


class TestPatternProperties:
    """Tests for `patternProperties` enforcement."""

    def test_pattern_properties(self) -> None:
        """Test values of matching property names are validated; non-matching are ignored."""
        schema = Schema.model_validate(
            {"type": "object", "patternProperties": {"^x-": {"type": "integer"}}}
        )
        model = to_model(schema)

        # `x-count` matches and validates; `name` does not match -> ignored.
        assert model.model_validate({"x-count": 5, "name": "a"}).model_dump() == snapshot(
            {"x-count": 5, "name": "a"}
        )

        with pytest.raises(ValidationError) as exc_info:
            model.model_validate({"x-count": "nope"})

        assert dump_errors(exc_info.value) == snapshot(
            [
                {
                    "type": "value_error",
                    "loc": (),
                    "msg": "Value error, Property `x-count` does not satisfy its `patternProperties` schema",
                    "input": {"x-count": "nope"},
                }
            ]
        )

        # Non-mapping input passes through and is rejected by type validation.
        with pytest.raises(ValidationError):
            model.model_validate("not a mapping")

    def test_pattern_properties_with_declared(self) -> None:
        """Test `patternProperties` alongside declared properties, with a constraint subschema."""
        schema = Schema.model_validate(
            {
                "type": "object",
                "properties": {"id": {"type": "integer"}},
                "patternProperties": {"^meta_": {"type": "string", "minLength": 2}},
            }
        )
        model = to_model(schema)

        assert model.model_validate({"id": 1, "meta_x": "ab"}).model_dump() == snapshot(
            {"id": 1, "meta_x": "ab"}
        )

        with pytest.raises(ValidationError) as exc_info:
            model.model_validate({"id": 1, "meta_x": "a"})

        assert dump_errors(exc_info.value) == snapshot(
            [
                {
                    "type": "value_error",
                    "loc": (),
                    "msg": "Value error, Property `meta_x` does not satisfy its `patternProperties` schema",
                    "input": {"id": 1, "meta_x": "a"},
                }
            ]
        )

    def test_pattern_properties_ref(self) -> None:
        """Test a `patternProperties` value pointing at a `$ref`."""
        schema = Schema.model_validate(
            {
                "type": "object",
                "patternProperties": {"^p": {"$ref": "#/$defs/Point"}},
                "$defs": {
                    "Point": {
                        "type": "object",
                        "properties": {"k": {"type": "integer"}},
                        "required": ["k"],
                    },
                },
            }
        )
        model = to_model(schema)

        assert model.model_validate({"p1": {"k": 1}}).model_dump() == snapshot({"p1": {"k": 1}})

        with pytest.raises(ValidationError) as exc_info:
            model.model_validate({"p1": {"no": 1}})

        assert dump_errors(exc_info.value) == snapshot(
            [
                {
                    "type": "value_error",
                    "loc": (),
                    "msg": "Value error, Property `p1` does not satisfy its `patternProperties` schema",
                    "input": {"p1": {"no": 1}},
                }
            ]
        )


class TestPatternPropertiesJsonSchema:
    """`patternProperties` round-trips into the dumped JSON Schema."""

    def test_pattern_properties_round_trips(self) -> None:
        """A converted model re-emits its `patternProperties` keyword on dump."""
        model = to_model(
            Schema.model_validate(
                {"type": "object", "patternProperties": {"^x": {"type": "integer"}}}
            )
        )

        assert model.model_json_schema() == snapshot(
            {
                "additionalProperties": True,
                "patternProperties": {"^x": {"type": "integer"}},
                "properties": {},
                "title": "Model",
                "type": "object",
            }
        )
