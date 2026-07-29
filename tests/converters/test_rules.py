"""Tests for the `rules` parameter: per-node loading via matchers and actions."""

from typing import TYPE_CHECKING

import pytest
from inline_snapshot import snapshot
from pydantic import ValidationError

from pydantic_jsonschema import to_model
from pydantic_jsonschema.rules import (
    After,
    Before,
    ByFunc,
    ByPath,
    ByType,
    Dump,
    MatchContext,
    Override,
    Rule,
)
from pydantic_jsonschema.schema import Schema
from tests.conftest import dump_errors

if TYPE_CHECKING:
    from tests.conftest import SchemaRaw

__all__: list[str] = []

_TAGS_SCHEMA: "SchemaRaw" = {
    "type": "object",
    "properties": {
        "tags": {"type": "array", "items": {"type": "string"}},
        "created": {"type": "string"},
    },
    "required": ["tags", "created"],
}


def csv_to_list(value: str | list[str]) -> list[str]:
    """Split a comma-separated string into a list, passing lists through unchanged."""
    return value.split(",") if isinstance(value, str) else value


def strip_upper(value: str) -> str:
    """Normalize a string by stripping whitespace and upper-casing."""
    return value.strip().upper()


def reject_empty(value: list[str]) -> list[str]:
    """Reject an empty list, else return it unchanged."""
    if not value:
        msg = "must not be empty"
        raise ValueError(msg)
    return value


def annotation_is_str(context: MatchContext, /) -> bool:
    """Predicate: match when the resolved annotation is exactly `str`."""
    return context.annotation is str


class TestBefore:
    """`Before` -> `BeforeValidator`: coerce raw input before core parsing."""

    def test_csv_string_to_list(self) -> None:
        """A comma-separated string is split into a list before list parsing."""
        schema = Schema.model_validate(_TAGS_SCHEMA)
        model = to_model(schema, rules=[Rule(ByType(list[str]), Before(csv_to_list))])

        instance = model(tags="a,b,c", created="x")
        assert instance.model_dump() == snapshot({"tags": ["a", "b", "c"], "created": "x"})

    def test_list_input_passes_through(self) -> None:
        """A list input is left unchanged (the coercion is idempotent)."""
        schema = Schema.model_validate(_TAGS_SCHEMA)
        model = to_model(schema, rules=[Rule(ByType(list[str]), Before(csv_to_list))])

        instance = model(tags=["a", "b"], created="x")
        assert instance.model_dump() == snapshot({"tags": ["a", "b"], "created": "x"})


class TestAfter:
    """`After` -> `AfterValidator`: normalize / validate the parsed value."""

    def test_normalizes_value(self) -> None:
        """The parsed string is normalized after core parsing."""
        schema = Schema.model_validate(_TAGS_SCHEMA)
        model = to_model(schema, rules=[Rule(ByPath("#/properties/created"), After(strip_upper))])

        instance = model(tags=[], created="  hi  ")
        assert instance.model_dump() == snapshot({"tags": [], "created": "HI"})

    def test_rejects_invalid_value(self) -> None:
        """An `After` validator that raises surfaces as a `ValidationError`."""
        schema = Schema.model_validate(_TAGS_SCHEMA)
        model = to_model(schema, rules=[Rule(ByType(list[str]), After(reject_empty))])

        with pytest.raises(ValidationError) as exc_info:
            model(tags=[], created="x")

        assert dump_errors(exc_info.value) == snapshot(
            [
                {
                    "type": "value_error",
                    "loc": ("tags",),
                    "msg": "Value error, must not be empty",
                    "input": [],
                }
            ]
        )


class TestOverride:
    """`Override` -> `PlainValidator`: replace core parsing entirely."""

    def test_replaces_parsing(self) -> None:
        """`Override` bypasses list parsing and produces the value directly."""
        schema = Schema.model_validate(_TAGS_SCHEMA)
        model = to_model(schema, rules=[Rule(ByType(list[str]), Override(csv_to_list))])

        instance = model(tags="a,b", created="x")
        assert instance.model_dump() == snapshot({"tags": ["a", "b"], "created": "x"})


class TestDump:
    """`Dump` -> `PlainSerializer`: transform the value on serialization."""

    def test_serializes_value(self) -> None:
        """The list is joined into a string on `model_dump`."""
        schema = Schema.model_validate(_TAGS_SCHEMA)
        model = to_model(schema, rules=[Rule(ByType(list[str]), Dump(",".join))])

        instance = model(tags=["x", "y"], created="z")
        assert instance.model_dump() == snapshot({"tags": "x,y", "created": "z"})


class TestMatchers:
    """Matcher selection: `ByType`, `ByPath`, `ByFunc`."""

    def test_by_type_no_match_leaves_field_untouched(self) -> None:
        """A `ByType` mismatch does not wrap the field, so raw input fails validation."""
        schema = Schema.model_validate(_TAGS_SCHEMA)
        model = to_model(schema, rules=[Rule(ByType(list[int]), Before(csv_to_list))])

        with pytest.raises(ValidationError) as exc_info:
            model(tags="a,b,c", created="x")

        assert dump_errors(exc_info.value) == snapshot(
            [
                {
                    "type": "list_type",
                    "loc": ("tags",),
                    "msg": "Input should be a valid list",
                    "input": "a,b,c",
                }
            ]
        )

    def test_by_path_matches_pointer(self) -> None:
        """`ByPath` targets a single node by its JSON Pointer."""
        schema = Schema.model_validate(_TAGS_SCHEMA)
        model = to_model(schema, rules=[Rule(ByPath("#/properties/created"), After(strip_upper))])

        instance = model(tags=[], created="hi")
        assert instance.model_dump() == snapshot({"tags": [], "created": "HI"})

    def test_by_func_predicate(self) -> None:
        """`ByFunc` matches every node whose predicate returns `True`."""
        schema = Schema.model_validate(_TAGS_SCHEMA)
        model = to_model(schema, rules=[Rule(ByFunc(annotation_is_str), After(strip_upper))])

        instance = model(tags=[], created="  hi ")
        assert instance.model_dump() == snapshot({"tags": [], "created": "HI"})


class TestRoundTrip:
    """Two rules sharing a matcher express a load-and-dump round-trip."""

    def test_before_and_dump(self) -> None:
        """`Before` coerces on input and `Dump` serializes on output for one type."""
        schema = Schema.model_validate(_TAGS_SCHEMA)
        model = to_model(
            schema,
            rules=[
                Rule(ByType(list[str]), Before(csv_to_list)),
                Rule(ByType(list[str]), Dump(",".join)),
            ],
        )

        instance = model(tags="x,y", created="z")
        # `Before` coerced the CSV string into a list internally; `Dump` re-joins it on output.
        # `getattr` sidesteps the dynamic model's untyped attribute access.
        assert getattr(instance, "tags") == snapshot(["x", "y"])  # noqa: B009
        assert instance.model_dump() == snapshot({"tags": "x,y", "created": "z"})


class TestNoRules:
    """Absence of rules is a no-op."""

    def test_empty_rules_unchanged(self) -> None:
        """Passing no rules leaves conversion unchanged."""
        schema = Schema.model_validate(_TAGS_SCHEMA)
        model = to_model(schema)

        instance = model(tags=["a"], created="c")
        assert instance.model_dump() == snapshot({"tags": ["a"], "created": "c"})


class TestRuleObjects:
    """Rules are frozen data: they compare, hash, and `repr` predictably."""

    def test_equal_rules_compare_equal(self) -> None:
        """Two rules built from the same parts are equal and hash equal."""
        first = Rule(ByType(list[str]), Before(csv_to_list))
        second = Rule(ByType(list[str]), Before(csv_to_list))

        assert first == second
        assert hash(first) == hash(second)

    def test_repr_is_data(self) -> None:
        """A rule's `repr` shows its matcher and action as data (function address elided)."""
        rule = Rule(ByPath("#/properties/created"), After(strip_upper))
        # NOTE: A function's `repr` carries its non-deterministic memory address, so match only
        # the stable prefix (`repr(rule) == "..."` would flap across runs).
        assert repr(rule).startswith(
            "Rule(matcher=ByPath(pointer='#/properties/created'), action=After(func=<function "
        )
