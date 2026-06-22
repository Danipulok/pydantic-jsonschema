"""Tests for the `dependentSchemas` applicator."""

import pytest
from inline_snapshot import snapshot
from pydantic import ValidationError

from pydantic_jsonschema import (
    to_model,
)
from pydantic_jsonschema.types import Schema
from tests.conftest import dump_errors

__all__: list[str] = []


class TestDependentSchemas:
    """Tests for `dependentSchemas` enforcement."""

    def test_dependent_schemas(self) -> None:
        """Test a present property applies its subschema to the whole instance."""
        schema = Schema.model_validate(
            {
                "type": "object",
                "properties": {
                    "credit_card": {"type": "integer"},
                    "billing_address": {"type": "string"},
                },
                "dependentSchemas": {
                    "credit_card": {
                        "type": "object",
                        "properties": {"billing_address": {"type": "string"}},
                        "required": ["billing_address"],
                    },
                },
            }
        )
        model = to_model(schema)

        # Trigger absent -> dependency does not apply.
        assert model.model_validate({}).model_dump() == snapshot({})

        # Trigger present and the subschema is satisfied.
        assert model.model_validate(
            {"credit_card": 1, "billing_address": "x"}
        ).model_dump() == snapshot({"credit_card": 1, "billing_address": "x"})

        # Trigger present, subschema not satisfied.
        with pytest.raises(ValidationError) as exc_info:
            model.model_validate({"credit_card": 1})

        assert dump_errors(exc_info.value) == snapshot(
            [
                {
                    "type": "value_error",
                    "loc": (),
                    "msg": "Value error, Property `credit_card` does not satisfy its `dependentSchemas` schema",
                    "input": {"credit_card": 1},
                }
            ]
        )

        # Non-mapping input passes through and is rejected by type validation.
        with pytest.raises(ValidationError):
            model.model_validate("not a mapping")

    def test_dependent_schemas_ref(self) -> None:
        """Test a `dependentSchemas` subschema pointing at a `$ref`."""
        schema = Schema.model_validate(
            {
                "type": "object",
                "properties": {"a": {"type": "integer"}},
                "dependentSchemas": {"a": {"$ref": "#/$defs/Req"}},
                "$defs": {
                    "Req": {
                        "type": "object",
                        "properties": {"b": {"type": "integer"}},
                        "required": ["b"],
                    },
                },
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
                    "msg": "Value error, Property `a` does not satisfy its `dependentSchemas` schema",
                    "input": {"a": 1},
                }
            ]
        )


class TestDependentSchemasJsonSchema:
    """`dependentSchemas` round-trips into the dumped JSON Schema."""

    def test_dependent_schemas_round_trips(self) -> None:
        """A converted model re-emits its `dependentSchemas` keyword on dump."""
        model = to_model(
            Schema.model_validate(
                {
                    "type": "object",
                    "dependentSchemas": {
                        "a": {
                            "type": "object",
                            "properties": {"b": {"type": "integer"}},
                            "required": ["b"],
                        },
                    },
                }
            )
        )

        assert model.model_json_schema() == snapshot(
            {
                "additionalProperties": True,
                "dependentSchemas": {
                    "a": {
                        "additionalProperties": True,
                        "properties": {"b": {"title": "B", "type": "integer"}},
                        "required": ["b"],
                        "title": "Model",
                        "type": "object",
                    }
                },
                "properties": {},
                "title": "Model",
                "type": "object",
            }
        )
