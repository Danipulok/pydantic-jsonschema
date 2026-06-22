"""Tests for the `not` applicator."""

import pytest
from inline_snapshot import snapshot
from pydantic import ValidationError

from pydantic_jsonschema import (
    to_model,
)
from pydantic_jsonschema.types import Schema
from tests.conftest import dump_errors

__all__: list[str] = []


class TestNot:
    """Tests for `not` enforcement.

    `not` is only as precise as the converter's coverage of its subschema: a subschema that maps
    to `Any` (e.g. an empty schema, or `required` without `type` / `properties`) matches every
    value, so `not` then rejects everything. These tests use subschemas the converter enforces.
    """

    def test_not_scalar(self) -> None:
        """Test `not` on a scalar root value (a forbidden constant)."""
        schema = Schema.model_validate({"type": "string", "not": {"const": "admin"}})
        model = to_model(schema)

        assert model.model_validate("alice").model_dump() == snapshot("alice")

        with pytest.raises(ValidationError) as exc_info:
            model.model_validate("admin")

        assert dump_errors(exc_info.value) == snapshot(
            [
                {
                    "type": "value_error",
                    "loc": (),
                    "msg": "Value error, Value must not match the `not` schema",
                    "input": "admin",
                }
            ]
        )

    def test_not_field(self) -> None:
        """Test `not` on an object property."""
        schema = Schema.model_validate(
            {
                "type": "object",
                "properties": {"name": {"type": "string", "not": {"const": "root"}}},
                "required": ["name"],
            }
        )
        model = to_model(schema)

        assert model.model_validate({"name": "bob"}).model_dump() == snapshot({"name": "bob"})

        with pytest.raises(ValidationError) as exc_info:
            model.model_validate({"name": "root"})

        assert dump_errors(exc_info.value) == snapshot(
            [
                {
                    "type": "value_error",
                    "loc": ("name",),
                    "msg": "Value error, Value must not match the `not` schema",
                    "input": "root",
                }
            ]
        )

    def test_not_root_object(self) -> None:
        """Test `not` on a root object model (wrapped via a `before` validator)."""
        schema = Schema.model_validate(
            {
                "type": "object",
                "properties": {"role": {"type": "string"}},
                "not": {
                    "type": "object",
                    "properties": {"secret": {"type": "integer"}},
                    "required": ["secret"],
                },
            }
        )
        model = to_model(schema)

        assert model.model_validate({"role": "user"}).model_dump() == snapshot({"role": "user"})

        with pytest.raises(ValidationError) as exc_info:
            model.model_validate({"role": "user", "secret": 1})

        assert dump_errors(exc_info.value) == snapshot(
            [
                {
                    "type": "value_error",
                    "loc": (),
                    "msg": "Value error, Value must not match the `not` schema",
                    "input": {"role": "user", "secret": 1},
                }
            ]
        )

    def test_not_ref(self) -> None:
        """Test `not` pointing at a `$ref` (resolved via the bound namespace)."""
        schema = Schema.model_validate(
            {
                "type": "object",
                "not": {"$ref": "#/$defs/Banned"},
                "properties": {"x": {"type": "integer"}},
                "$defs": {
                    "Banned": {
                        "type": "object",
                        "properties": {"evil": {"type": "integer"}},
                        "required": ["evil"],
                    },
                },
            }
        )
        model = to_model(schema)

        assert model.model_validate({"x": 1}).model_dump() == snapshot({"x": 1})

        with pytest.raises(ValidationError) as exc_info:
            model.model_validate({"evil": 1})

        assert dump_errors(exc_info.value) == snapshot(
            [
                {
                    "type": "value_error",
                    "loc": (),
                    "msg": "Value error, Value must not match the `not` schema",
                    "input": {"evil": 1},
                }
            ]
        )


class TestNotJsonSchema:
    """`not` round-trips into the dumped JSON Schema."""

    def test_not_round_trips(self) -> None:
        """A converted model re-emits its `not` keyword on `model_json_schema()`."""
        model = to_model(
            Schema.model_validate(
                {
                    "type": "object",
                    "properties": {"x": {"type": "integer", "not": {"const": 5}}},
                    "required": ["x"],
                }
            )
        )

        assert model.model_json_schema()["properties"]["x"] == snapshot(
            {"not": {"const": 5, "type": "integer"}, "title": "X", "type": "integer"}
        )
