"""Property-based tests for constraint conversion (Hypothesis).

These complement the example-based tests in `test_field_kwargs.py`: instead of a
handful of hand-picked values, they fuzz many inputs and assert the boundary
relationship that each constraint keyword promises. They target only constraints
with an unambiguous, coercion-free acceptance rule (numeric bounds, string
length, integer `multipleOf`) so the property never has to second-guess Pydantic's
lax-mode coercion — that is what keeps them non-flaky under `filterwarnings=error`.
"""

from typing import TYPE_CHECKING

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from pydantic_jsonschema import to_model
from pydantic_jsonschema.schema import Schema

if TYPE_CHECKING:
    from tests.conftest import SchemaRaw

__all__: list[str] = []

# NOTE: `deadline=None` because each example rebuilds a model via `to_model`, whose
#       timing varies on shared CI runners; a per-example deadline would flake without
#       testing anything about correctness. `max_examples=50` keeps the suite fast.
_settings = settings(max_examples=50, deadline=None)


class TestIntegerBounds:
    """`minimum` / `maximum` map to inclusive integer bounds."""

    @_settings
    @given(
        bounds=st.tuples(
            st.integers(min_value=-1000, max_value=1000),
            st.integers(min_value=-1000, max_value=1000),
        ).map(lambda pair: (min(pair), max(pair))),
        value=st.integers(min_value=-2000, max_value=2000),
    )
    def test_inclusive_bounds(self, bounds: tuple[int, int], value: int) -> None:
        low, high = bounds
        property_schema: SchemaRaw = {"type": "integer", "minimum": low, "maximum": high}
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {"value": property_schema},
            "required": ["value"],
        }
        model = to_model(Schema.model_validate(schema_raw))

        if low <= value <= high:
            assert model(value=value).model_dump() == {"value": value}
        else:
            with pytest.raises(ValidationError):
                model(value=value)


class TestStringLength:
    """`minLength` / `maxLength` map to inclusive string-length bounds."""

    @_settings
    @given(
        bounds=st.tuples(
            st.integers(min_value=0, max_value=30),
            st.integers(min_value=0, max_value=30),
        ).map(lambda pair: (min(pair), max(pair))),
        text=st.text(max_size=40),
    )
    def test_inclusive_length(self, bounds: tuple[int, int], text: str) -> None:
        low, high = bounds
        property_schema: SchemaRaw = {"type": "string", "minLength": low, "maxLength": high}
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {"value": property_schema},
            "required": ["value"],
        }
        model = to_model(Schema.model_validate(schema_raw))

        if low <= len(text) <= high:
            assert model(value=text).model_dump() == {"value": text}
        else:
            with pytest.raises(ValidationError):
                model(value=text)


class TestIntegerMultipleOf:
    """An integer `multipleOf` accepts exactly the integer multiples of its divisor."""

    @_settings
    @given(
        divisor=st.integers(min_value=1, max_value=100),
        value=st.integers(min_value=-1000, max_value=1000),
    )
    def test_accepts_multiples(self, divisor: int, value: int) -> None:
        property_schema: SchemaRaw = {"type": "integer", "multipleOf": divisor}
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {"value": property_schema},
            "required": ["value"],
        }
        model = to_model(Schema.model_validate(schema_raw))

        if value % divisor == 0:
            assert model(value=value).model_dump() == {"value": value}
        else:
            with pytest.raises(ValidationError):
                model(value=value)
