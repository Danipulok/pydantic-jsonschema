"""Tests for the `oneOf` applicator."""

import pytest
from inline_snapshot import snapshot
from pydantic import ValidationError

from pydantic_jsonschema import to_model
from pydantic_jsonschema.types import Schema
from tests.conftest import dump_errors

__all__: list[str] = []


class TestOneOf:
    """Tests for `oneOf` enforcement: a value must match exactly one branch.

    A plain Python `Union` accepts a value matching *any* branch, so the converter wraps
    non-discriminated `oneOf` in a validator that counts matching branches and rejects a value
    matching zero or more than one. (Object branches tagged by a shared constant promote to a
    native discriminated union instead — see `tests/converters/test_discriminator.py`.)
    """

    def test_exactly_one_branch_accepted(self) -> None:
        """A value matching exactly one branch is accepted; matching several is rejected."""
        schema = Schema.model_validate(
            {
                "type": "object",
                "properties": {"value": {"oneOf": [{"type": "integer"}, {"type": "number"}]}},
                "required": ["value"],
            }
        )
        model = to_model(schema)

        # `1.5` is not a valid integer, so it matches only the `number` branch.
        assert model.model_validate({"value": 1.5}).model_dump() == snapshot({"value": 1.5})

        # `1` validates as both `integer` and `number`, so it matches two branches.
        with pytest.raises(ValidationError) as exc_info:
            model.model_validate({"value": 1})

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

    def test_zero_matches_rejected(self) -> None:
        """A value matching no branch is rejected."""
        schema = Schema.model_validate(
            {
                "type": "object",
                "properties": {"value": {"oneOf": [{"type": "integer"}, {"type": "number"}]}},
                "required": ["value"],
            }
        )
        model = to_model(schema)

        with pytest.raises(ValidationError) as exc_info:
            model.model_validate({"value": "text"})

        assert dump_errors(exc_info.value) == snapshot(
            [
                {
                    "type": "value_error",
                    "loc": ("value",),
                    "msg": "Value error, Input matches 0 `oneOf` branches, expected exactly 1",
                    "input": "text",
                }
            ]
        )

    def test_one_of_scalar_root(self) -> None:
        """`oneOf` on a scalar root value enforces exactly-one-branch semantics."""
        schema = Schema.model_validate({"oneOf": [{"type": "integer"}, {"type": "number"}]})
        model = to_model(schema)

        assert model.model_validate(1.5).model_dump() == snapshot(1.5)

        with pytest.raises(ValidationError) as exc_info:
            model.model_validate(1)

        assert dump_errors(exc_info.value) == snapshot(
            [
                {
                    "type": "value_error",
                    "loc": (),
                    "msg": "Value error, Input matches 2 `oneOf` branches, expected exactly 1",
                    "input": 1,
                }
            ]
        )

    def test_one_of_ref_branch(self) -> None:
        """A recursive `$ref` branch resolves lazily through the bound namespace."""
        schema = Schema.model_validate(
            {
                "type": "object",
                "properties": {"tree": {"$ref": "#/$defs/Node"}},
                "required": ["tree"],
                "$defs": {
                    "Node": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "integer"},
                            "next": {"oneOf": [{"$ref": "#/$defs/Node"}, {"type": "null"}]},
                        },
                        "required": ["value"],
                    },
                },
            }
        )
        model = to_model(schema)

        leaf = model.model_validate({"tree": {"value": 1, "next": None}})
        assert leaf.model_dump() == snapshot({"tree": {"value": 1, "next": None}})

        nested = model.model_validate({"tree": {"value": 1, "next": {"value": 2, "next": None}}})
        assert nested.model_dump() == snapshot(
            {"tree": {"value": 1, "next": {"value": 2, "next": None}}}
        )


class TestOneOfJsonSchema:
    """`oneOf` round-trips into the dumped JSON Schema instead of `anyOf`."""

    def test_multi_branch_dumps_one_of(self) -> None:
        """A multi-branch `oneOf` re-emits `oneOf` (not `anyOf`) on `model_json_schema()`."""
        model = to_model(
            Schema.model_validate(
                {
                    "type": "object",
                    "properties": {"value": {"oneOf": [{"type": "integer"}, {"type": "number"}]}},
                    "required": ["value"],
                }
            )
        )

        assert model.model_json_schema()["properties"]["value"] == snapshot(
            {"oneOf": [{"type": "integer"}, {"type": "number"}], "title": "Value"}
        )

    def test_single_branch_dumps_plain(self) -> None:
        """A single-branch `oneOf` dumps as the plain branch schema (no `oneOf` wrapper)."""
        model = to_model(
            Schema.model_validate(
                {
                    "type": "object",
                    "properties": {"value": {"oneOf": [{"type": "string"}]}},
                    "required": ["value"],
                }
            )
        )

        assert model.model_json_schema()["properties"]["value"] == snapshot(
            {"title": "Value", "type": "string"}
        )
