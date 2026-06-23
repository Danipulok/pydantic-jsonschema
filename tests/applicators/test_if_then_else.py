"""Tests for the `if`/`then`/`else` applicator."""

import pytest
from inline_snapshot import snapshot
from pydantic import ValidationError

from pydantic_jsonschema import (
    to_model,
)
from pydantic_jsonschema.schema import Schema
from tests.conftest import dump_errors

__all__: list[str] = []


class TestIfThenElse:
    """Tests for `if` / `then` / `else` conditional validation."""

    def test_if_then_root_object(self) -> None:
        """Test `if` / `then` on a root object (no `else`)."""
        schema = Schema.model_validate(
            {
                "type": "object",
                "properties": {"country": {"type": "string"}, "postal_code": {"type": "string"}},
                "if": {
                    "type": "object",
                    "properties": {"country": {"const": "US"}},
                    "required": ["country"],
                },
                "then": {
                    "type": "object",
                    "properties": {"postal_code": {"type": "string"}},
                    "required": ["postal_code"],
                },
            }
        )
        model = to_model(schema)

        # `if` matches and `then` is satisfied.
        assert model.model_validate(
            {"country": "US", "postal_code": "12345"}
        ).model_dump() == snapshot({"country": "US", "postal_code": "12345"})

        # `if` does not match -> no `else`, so it passes.
        assert model.model_validate({"country": "CA"}).model_dump() == snapshot({"country": "CA"})

        # `if` matches but `then` fails.
        with pytest.raises(ValidationError) as exc_info:
            model.model_validate({"country": "US"})

        assert dump_errors(exc_info.value) == snapshot(
            [
                {
                    "type": "value_error",
                    "loc": (),
                    "msg": "Value error, Value matches `if` but not `then`",
                    "input": {"country": "US"},
                }
            ]
        )

    def test_if_then_else_scalar(self) -> None:
        """Test `if` / `then` / `else` on a scalar root (the `else` branch and a constraint)."""
        schema = Schema.model_validate(
            {
                "type": "integer",
                "if": {"const": 0},
                "then": {"const": 0},
                "else": {"type": "integer", "exclusiveMinimum": 0},
            }
        )
        model = to_model(schema)

        assert model.model_validate(0).model_dump() == snapshot(0)
        assert model.model_validate(5).model_dump() == snapshot(5)

        with pytest.raises(ValidationError) as exc_info:
            model.model_validate(-3)

        assert dump_errors(exc_info.value) == snapshot(
            [
                {
                    "type": "value_error",
                    "loc": (),
                    "msg": "Value error, Value does not match `if` and not `else`",
                    "input": -3,
                }
            ]
        )

    def test_if_else_only(self) -> None:
        """Test `if` / `else` without `then` (a matching `if` imposes no extra constraint)."""
        schema = Schema.model_validate(
            {
                "type": "string",
                "if": {"const": "x"},
                "else": {"type": "string", "minLength": 3},
            }
        )
        model = to_model(schema)

        # `if` matches -> no `then`, so it passes.
        assert model.model_validate("x").model_dump() == snapshot("x")
        # `if` does not match -> `else` is satisfied.
        assert model.model_validate("abc").model_dump() == snapshot("abc")

        with pytest.raises(ValidationError) as exc_info:
            model.model_validate("ab")

        assert dump_errors(exc_info.value) == snapshot(
            [
                {
                    "type": "value_error",
                    "loc": (),
                    "msg": "Value error, Value does not match `if` and not `else`",
                    "input": "ab",
                }
            ]
        )

    def test_if_then_ref(self) -> None:
        """Test `if` / `then` pointing at `$ref`s (resolved via the bound namespace)."""
        schema = Schema.model_validate(
            {
                "type": "object",
                "properties": {"kind": {"type": "string"}, "size": {"type": "integer"}},
                "if": {"$ref": "#/$defs/IsBox"},
                "then": {"$ref": "#/$defs/HasSize"},
                "$defs": {
                    "IsBox": {
                        "type": "object",
                        "properties": {"kind": {"const": "box"}},
                        "required": ["kind"],
                    },
                    "HasSize": {
                        "type": "object",
                        "properties": {"size": {"type": "integer"}},
                        "required": ["size"],
                    },
                },
            }
        )
        model = to_model(schema)

        assert model.model_validate({"kind": "box", "size": 1}).model_dump() == snapshot(
            {"kind": "box", "size": 1}
        )

        with pytest.raises(ValidationError) as exc_info:
            model.model_validate({"kind": "box"})

        assert dump_errors(exc_info.value) == snapshot(
            [
                {
                    "type": "value_error",
                    "loc": (),
                    "msg": "Value error, Value matches `if` but not `then`",
                    "input": {"kind": "box"},
                }
            ]
        )


class TestIfThenElseJsonSchema:
    """`if` / `then` / `else` round-trip into the dumped JSON Schema."""

    def test_if_then_else_round_trips(self) -> None:
        """A converted model re-emits its `if` / `then` / `else` keywords on dump."""
        model = to_model(
            Schema.model_validate(
                {
                    "type": "object",
                    "properties": {
                        "a": {
                            "type": "integer",
                            "if": {"const": 1},
                            "then": {"const": 1},
                            "else": {"const": 2},
                        },
                    },
                    "required": ["a"],
                }
            )
        )

        assert model.model_json_schema()["properties"]["a"] == snapshot(
            {
                "else": {"const": 2, "type": "integer"},
                "if": {"const": 1, "type": "integer"},
                "then": {"const": 1, "type": "integer"},
                "title": "A",
                "type": "integer",
            }
        )

    def test_if_then_only_round_trips(self) -> None:
        """`if` / `then` without `else` dumps without an `else` keyword."""
        model = to_model(
            Schema.model_validate(
                {
                    "type": "object",
                    "properties": {
                        "a": {"type": "integer", "if": {"const": 1}, "then": {"const": 1}}
                    },
                    "required": ["a"],
                }
            )
        )

        assert model.model_json_schema()["properties"]["a"] == snapshot(
            {
                "if": {"const": 1, "type": "integer"},
                "then": {"const": 1, "type": "integer"},
                "title": "A",
                "type": "integer",
            }
        )

    def test_if_else_only_round_trips(self) -> None:
        """`if` / `else` without `then` dumps without a `then` keyword."""
        model = to_model(
            Schema.model_validate(
                {
                    "type": "object",
                    "properties": {
                        "a": {"type": "integer", "if": {"const": 1}, "else": {"const": 2}}
                    },
                    "required": ["a"],
                }
            )
        )

        assert model.model_json_schema()["properties"]["a"] == snapshot(
            {
                "else": {"const": 2, "type": "integer"},
                "if": {"const": 1, "type": "integer"},
                "title": "A",
                "type": "integer",
            }
        )

    def test_if_then_root_object_round_trips(self) -> None:
        """A root-object `if`/`then` (applied via the model wrapper) also re-emits its keywords."""
        model = to_model(
            Schema.model_validate(
                {
                    "type": "object",
                    "properties": {"country": {"type": "string"}, "zip": {"type": "string"}},
                    "if": {"properties": {"country": {"const": "US"}}, "required": ["country"]},
                    "then": {"required": ["zip"]},
                }
            )
        )

        assert model.model_json_schema() == snapshot(
            {
                "additionalProperties": True,
                "if": {},
                "properties": {
                    "country": {"title": "Country", "type": "string"},
                    "zip": {"title": "Zip", "type": "string"},
                },
                "then": {},
                "title": "Model",
                "type": "object",
            }
        )
