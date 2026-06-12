"""Tests for the `OneOf` exactly-one-branch validator."""

from typing import Annotated, ForwardRef

import pytest
from inline_snapshot import snapshot
from pydantic import BaseModel, TypeAdapter, ValidationError

from pydantic_jsonschema import OneOf, Schema, to_model


class Pet(BaseModel):
    """Sample model used as a `ForwardRef` target."""

    name: str


class TestOneOfValidation:
    """Validation semantics: exactly one branch must match."""

    def test_single_match_accepted(self) -> None:
        """Value matching exactly one branch is accepted."""

        class Model(BaseModel):
            value: Annotated[int | float, OneOf(branches=[int, float])]

        instance = Model(value=1.5)
        assert instance.value == snapshot(1.5)

    def test_multiple_matches_rejected(self) -> None:
        """Value matching more than one branch is rejected."""

        class Model(BaseModel):
            value: Annotated[int | float, OneOf(branches=[int, float])]

        with pytest.raises(ValidationError, match=r"matches 2 `oneOf` branches"):
            Model(value=1)

    def test_zero_matches_rejected(self) -> None:
        """Value matching no branch is rejected."""

        class Model(BaseModel):
            value: Annotated[str | bool, OneOf(branches=[str, bool])]

        with pytest.raises(ValidationError, match=r"matches 0 `oneOf` branches"):
            Model(value=[1, 2, 3])

    def test_branches_accept_any_iterable(self) -> None:
        """`branches` accepts any iterable, not only sequences."""
        one_of = OneOf(branches=iter([int, str]))

        class Model(BaseModel):
            value: Annotated[int | str, one_of]

        instance = Model(value="text")
        assert instance.value == snapshot("text")

    def test_as_annotation(self) -> None:
        """`as_annotation` builds a self-contained validated union annotation."""
        one_of = OneOf(branches=[int, float])
        adapter: TypeAdapter[int | float] = TypeAdapter(one_of.as_annotation())

        assert adapter.validate_python(1.5) == snapshot(1.5)

        with pytest.raises(ValidationError, match=r"matches 2 `oneOf` branches"):
            adapter.validate_python(1)

    def test_forward_ref_branch_resolved_after_binding(self) -> None:
        """`ForwardRef` branches resolve through the bound namespace."""
        one_of = OneOf(branches=[ForwardRef("Pet"), type(None)])
        one_of.bind_namespace({"Pet": Pet})

        class Model(BaseModel):
            value: Annotated[Pet | None, one_of]

        instance = Model(value={"name": "Rex"})
        assert instance.value == snapshot(Pet(name="Rex"))

        instance = Model(value=None)
        assert instance.value is None


class TestOneOfJsonSchema:
    """JSON Schema dump: `oneOf` round-trips instead of `anyOf`."""

    def test_dump_uses_one_of(self) -> None:
        """Union branches dump as `oneOf`."""

        class Model(BaseModel):
            value: Annotated[int | float, OneOf(branches=[int, float])]

        assert Model.model_json_schema() == snapshot(
            {
                "properties": {
                    "value": {
                        "oneOf": [{"type": "integer"}, {"type": "number"}],
                        "title": "Value",
                    }
                },
                "required": ["value"],
                "title": "Model",
                "type": "object",
            }
        )

    def test_single_branch_dump_has_no_union(self) -> None:
        """Single-branch `oneOf` dumps as the plain branch schema."""

        class Model(BaseModel):
            value: Annotated[str, OneOf(branches=[str])]

        assert Model.model_json_schema() == snapshot(
            {
                "properties": {"value": {"title": "Value", "type": "string"}},
                "required": ["value"],
                "title": "Model",
                "type": "object",
            }
        )

    def test_converted_model_dump_round_trips_one_of(self) -> None:
        """Model converted from a `oneOf` schema dumps `oneOf` back."""
        schema = Schema.model_validate(
            {
                "type": "object",
                "properties": {
                    "value": {
                        "oneOf": [
                            {"type": "integer"},
                            {"type": "number"},
                        ],
                    },
                },
            }
        )
        model = to_model(schema)

        assert model.model_json_schema() == snapshot(
            {
                "additionalProperties": True,
                "properties": {
                    "value": {
                        "oneOf": [{"type": "integer"}, {"type": "number"}],
                        "title": "Value",
                    }
                },
                "title": "Model",
                "type": "object",
            }
        )
