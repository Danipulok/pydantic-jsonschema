"""Tests for the `contains` applicator."""

import pytest
from inline_snapshot import snapshot
from pydantic import ValidationError

from pydantic_jsonschema import (
    to_model,
)
from pydantic_jsonschema.types import Schema
from tests.conftest import dump_errors

__all__: list[str] = []


class TestContains:
    """Tests for `contains` / `minContains` / `maxContains` enforcement."""

    def test_contains_at_least_one(self) -> None:
        """Test `contains` requires at least one matching element by default."""
        schema = Schema.model_validate({"type": "array", "contains": {"type": "integer"}})
        model = to_model(schema)

        assert model.model_validate([1, "a"]).model_dump() == snapshot([1, "a"])

        with pytest.raises(ValidationError) as exc_info:
            model.model_validate(["a", "b"])

        assert dump_errors(exc_info.value) == snapshot(
            [
                {
                    "type": "value_error",
                    "loc": (),
                    "msg": "Value error, Array must contain at least `1` matches, got `0`",
                    "input": ["a", "b"],
                }
            ]
        )

    def test_min_contains(self) -> None:
        """Test `minContains` raises the required match count."""
        schema = Schema.model_validate(
            {"type": "array", "contains": {"type": "integer"}, "minContains": 2}
        )
        model = to_model(schema)

        assert model.model_validate([1, 2, "a"]).model_dump() == snapshot([1, 2, "a"])

        with pytest.raises(ValidationError) as exc_info:
            model.model_validate([1, "a"])

        assert dump_errors(exc_info.value) == snapshot(
            [
                {
                    "type": "value_error",
                    "loc": (),
                    "msg": "Value error, Array must contain at least `2` matches, got `1`",
                    "input": [1, "a"],
                }
            ]
        )

    def test_max_contains(self) -> None:
        """Test `maxContains` caps the allowed match count."""
        schema = Schema.model_validate(
            {"type": "array", "contains": {"type": "integer"}, "maxContains": 1}
        )
        model = to_model(schema)

        assert model.model_validate([1, "a"]).model_dump() == snapshot([1, "a"])

        with pytest.raises(ValidationError) as exc_info:
            model.model_validate([1, 2])

        assert dump_errors(exc_info.value) == snapshot(
            [
                {
                    "type": "value_error",
                    "loc": (),
                    "msg": "Value error, Array must contain at most `1` matches, got `2`",
                    "input": [1, 2],
                }
            ]
        )

    def test_min_contains_zero_allows_no_match(self) -> None:
        """Test `minContains: 0` makes `contains` satisfiable with zero matches."""
        schema = Schema.model_validate(
            {"type": "array", "contains": {"type": "integer"}, "minContains": 0}
        )
        model = to_model(schema)
        assert model.model_validate(["a", "b"]).model_dump() == snapshot(["a", "b"])

    def test_contains_ref(self) -> None:
        """Test `contains` pointing at a `$ref` (resolved via the bound namespace)."""
        schema = Schema.model_validate(
            {
                "type": "array",
                "contains": {"$ref": "#/$defs/Point"},
                "$defs": {
                    "Point": {
                        "type": "object",
                        "properties": {"x": {"type": "integer"}},
                        "required": ["x"],
                    },
                },
            }
        )
        model = to_model(schema)

        assert model.model_validate([{"x": 1}, {"y": 2}]).model_dump() == snapshot(
            [{"x": 1}, {"y": 2}]
        )

        with pytest.raises(ValidationError) as exc_info:
            model.model_validate([{"y": 2}])

        assert dump_errors(exc_info.value) == snapshot(
            [
                {
                    "type": "value_error",
                    "loc": (),
                    "msg": "Value error, Array must contain at least `1` matches, got `0`",
                    "input": [{"y": 2}],
                }
            ]
        )


class TestContainsJsonSchema:
    """`contains` / `minContains` / `maxContains` round-trip into the dumped JSON Schema."""

    def test_contains_round_trips(self) -> None:
        """A converted model re-emits its `contains` bounds on `model_json_schema()`."""
        model = to_model(
            Schema.model_validate(
                {
                    "type": "object",
                    "properties": {
                        "a": {
                            "type": "array",
                            "contains": {"type": "integer"},
                            "minContains": 2,
                            "maxContains": 4,
                        },
                    },
                    "required": ["a"],
                }
            )
        )

        assert model.model_json_schema()["properties"]["a"] == snapshot(
            {
                "contains": {"type": "integer"},
                "items": {},
                "maxContains": 4,
                "minContains": 2,
                "title": "A",
                "type": "array",
            }
        )

    def test_contains_default_bounds_round_trips(self) -> None:
        """Default `minContains` (1) and absent `maxContains` are not emitted on dump."""
        model = to_model(
            Schema.model_validate(
                {
                    "type": "object",
                    "properties": {"a": {"type": "array", "contains": {"type": "integer"}}},
                    "required": ["a"],
                }
            )
        )

        assert model.model_json_schema()["properties"]["a"] == snapshot(
            {"contains": {"type": "integer"}, "items": {}, "title": "A", "type": "array"}
        )
