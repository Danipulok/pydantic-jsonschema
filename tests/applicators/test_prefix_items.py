"""Tests for the `prefixItems` applicator."""

import pytest
from inline_snapshot import snapshot
from pydantic import ValidationError

from pydantic_jsonschema import (
    to_model,
)
from pydantic_jsonschema.types import Schema
from tests.conftest import dump_errors

__all__: list[str] = []


class TestPrefixItems:
    """Tests for `prefixItems` positional validation."""

    def test_prefix_items_with_tail(self) -> None:
        """Test positional `prefixItems` plus an `items` tail schema."""
        schema = Schema.model_validate(
            {
                "type": "array",
                "prefixItems": [{"type": "string"}, {"type": "integer"}],
                "items": {"type": "boolean"},
            }
        )
        model = to_model(schema)

        assert model.model_validate(["a", 1, True, False]).model_dump() == snapshot(
            ["a", 1, True, False]
        )

        with pytest.raises(ValidationError) as exc_info:
            model.model_validate([1, 1])

        assert dump_errors(exc_info.value) == snapshot(
            [
                {
                    "type": "value_error",
                    "loc": (),
                    "msg": "Value error, Item at index `0` does not match the `prefixItems` schema",
                    "input": [1, 1],
                }
            ]
        )

        with pytest.raises(ValidationError) as exc_info:
            model.model_validate(["a", 1, "x"])

        assert dump_errors(exc_info.value) == snapshot(
            [
                {
                    "type": "value_error",
                    "loc": (),
                    "msg": "Value error, Item at index `2` does not match the `items` schema",
                    "input": ["a", 1, "x"],
                }
            ]
        )

    def test_prefix_items_extra_unconstrained(self) -> None:
        """Test elements past the prefix are unconstrained when `items` is absent."""
        schema = Schema.model_validate({"type": "array", "prefixItems": [{"type": "string"}]})
        model = to_model(schema)

        assert model.model_validate(["a", 1, {"x": 2}]).model_dump() == snapshot(["a", 1, {"x": 2}])

        with pytest.raises(ValidationError) as exc_info:
            model.model_validate([5])

        assert dump_errors(exc_info.value) == snapshot(
            [
                {
                    "type": "value_error",
                    "loc": (),
                    "msg": "Value error, Item at index `0` does not match the `prefixItems` schema",
                    "input": [5],
                }
            ]
        )

    def test_prefix_items_ref(self) -> None:
        """Test a `prefixItems` entry pointing at a `$ref` (resolved via the bound namespace)."""
        schema = Schema.model_validate(
            {
                "type": "array",
                "prefixItems": [{"$ref": "#/$defs/Point"}],
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

        assert model.model_validate([{"k": 1}]).model_dump() == snapshot([{"k": 1}])

        with pytest.raises(ValidationError) as exc_info:
            model.model_validate([{"no": 1}])

        assert dump_errors(exc_info.value) == snapshot(
            [
                {
                    "type": "value_error",
                    "loc": (),
                    "msg": "Value error, Item at index `0` does not match the `prefixItems` schema",
                    "input": [{"no": 1}],
                }
            ]
        )
