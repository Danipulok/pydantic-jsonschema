"""Tests for object-keyword validators (`minProperties` / `dependentRequired`)."""

import pytest
from inline_snapshot import snapshot
from pydantic import ValidationError

from pydantic_jsonschema import (
    to_model,
)
from pydantic_jsonschema.schema import Schema
from tests.conftest import dump_errors

__all__: list[str] = []


class TestPropertyCount:
    """Tests for `minProperties` / `maxProperties` enforcement."""

    def test_min_properties_object(self) -> None:
        """Test `minProperties` on an object with declared properties."""
        schema = Schema.model_validate(
            {
                "type": "object",
                "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
                "minProperties": 2,
            }
        )
        model = to_model(schema)

        assert model.model_validate({"a": 1, "b": 2}).model_dump() == snapshot({"a": 1, "b": 2})

        with pytest.raises(ValidationError) as exc_info:
            model.model_validate({"a": 1})

        assert dump_errors(exc_info.value) == snapshot(
            [
                {
                    "type": "value_error",
                    "loc": (),
                    "msg": "Value error, Object must have at least `2` properties",
                    "input": {"a": 1},
                }
            ]
        )

        # Non-mapping input passes through the count validator and is rejected by type validation.
        with pytest.raises(ValidationError):
            model.model_validate("not a mapping")

    def test_max_properties_counts_extra_keys(self) -> None:
        """Test `maxProperties` counts `extra` keys, not only declared fields."""
        schema = Schema.model_validate(
            {
                "type": "object",
                "properties": {"a": {"type": "integer"}},
                "maxProperties": 1,
            }
        )
        model = to_model(schema)

        assert model.model_validate({"a": 1}).model_dump() == snapshot({"a": 1})

        with pytest.raises(ValidationError) as exc_info:
            model.model_validate({"a": 1, "extra": 2})

        assert dump_errors(exc_info.value) == snapshot(
            [
                {
                    "type": "value_error",
                    "loc": (),
                    "msg": "Value error, Object must have at most `1` properties",
                    "input": {"a": 1, "extra": 2},
                }
            ]
        )

    def test_property_count_dict_root(self) -> None:
        """Test `minProperties` / `maxProperties` on a dict-root object (no declared properties)."""
        schema = Schema.model_validate(
            {
                "type": "object",
                "additionalProperties": {"type": "integer"},
                "minProperties": 1,
                "maxProperties": 2,
            }
        )
        model = to_model(schema)

        assert model.model_validate({"a": 1, "b": 2}).model_dump() == snapshot({"a": 1, "b": 2})

        with pytest.raises(ValidationError) as exc_info:
            model.model_validate({})

        assert dump_errors(exc_info.value) == snapshot(
            [
                {
                    "type": "too_short",
                    "loc": (),
                    "msg": "Dictionary should have at least 1 item after validation, not 0",
                    "input": {},
                }
            ]
        )

        with pytest.raises(ValidationError) as exc_info:
            model.model_validate({"a": 1, "b": 2, "c": 3})

        assert dump_errors(exc_info.value) == snapshot(
            [
                {
                    "type": "too_long",
                    "loc": (),
                    "msg": "Dictionary should have at most 2 items after validation, not 3",
                    "input": {"a": 1, "b": 2, "c": 3},
                }
            ]
        )


class TestDependentRequired:
    """Tests for `dependentRequired` enforcement."""

    def test_dependent_required(self) -> None:
        """Test a trigger property makes its dependent properties required."""
        schema = Schema.model_validate(
            {
                "type": "object",
                "properties": {
                    "credit_card": {"type": "integer"},
                    "billing_address": {"type": "string"},
                    "cvv": {"type": "integer"},
                },
                "dependentRequired": {"credit_card": ["billing_address", "cvv"]},
            }
        )
        model = to_model(schema)

        # Trigger absent -> no dependency applies.
        assert model.model_validate({}).model_dump() == snapshot({})

        # Trigger present with all dependents.
        assert model.model_validate(
            {"credit_card": 1, "billing_address": "x", "cvv": 2}
        ).model_dump() == snapshot({"credit_card": 1, "billing_address": "x", "cvv": 2})

        # Trigger present, dependents missing.
        with pytest.raises(ValidationError) as exc_info:
            model.model_validate({"credit_card": 1})

        assert dump_errors(exc_info.value) == snapshot(
            [
                {
                    "type": "value_error",
                    "loc": (),
                    "msg": "Value error, Property `credit_card` requires `billing_address`, `cvv`",
                    "input": {"credit_card": 1},
                }
            ]
        )

        # Non-mapping input passes through and is rejected by type validation.
        with pytest.raises(ValidationError):
            model.model_validate("not a mapping")
