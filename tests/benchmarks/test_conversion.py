"""Benchmarks for the JSON Schema -> Pydantic conversion pipeline.

Each benchmark validates the `Schema` up front (outside the measured region) and times only
`to_model`, so the numbers track *our* converter rather than Pydantic's model build. The
end-to-end case additionally times `Schema.model_validate` to cover the full public entry path.
"""

from typing import TYPE_CHECKING, Any, Final

import pytest

from pydantic_jsonschema import Schema, to_model
from pydantic_jsonschema.rules import After, ByFunc, ByPath, ByType, MatchContext, Rule

if TYPE_CHECKING:
    from pytest_codspeed import BenchmarkFixture

__all__: list[str] = []

# A wide, flat object: many primitive properties exercising every scalar branch plus the
# common constraint keywords (bounds, length, pattern, enum, format).
_WIDE_SCHEMA: Final[dict[str, Any]] = {
    "type": "object",
    "properties": {
        "id": {"type": "integer", "minimum": 1},
        "score": {"type": "number", "minimum": 0.0, "maximum": 100.0},
        "name": {"type": "string", "minLength": 1, "maxLength": 120},
        "slug": {"type": "string", "pattern": r"^[a-z0-9-]+$"},
        "email": {"type": "string", "format": "email"},
        "homepage": {"type": "string", "format": "uri"},
        "created_at": {"type": "string", "format": "date-time"},
        "active": {"type": "boolean"},
        "status": {"type": "string", "enum": ["draft", "published", "archived"]},
        "priority": {"type": "integer", "enum": [1, 2, 3, 5, 8]},
        "tags": {"type": "array", "items": {"type": "string"}, "maxItems": 16},
        "ratios": {"type": "array", "items": {"type": "number"}},
        "nickname": {"type": "string"},
        "age": {"type": "integer", "minimum": 0, "maximum": 150},
        "balance": {"type": "number"},
        "verified": {"type": "boolean"},
        "country": {"type": "string", "minLength": 2, "maxLength": 2},
        "notes": {"type": "string"},
        "ref_count": {"type": "integer", "minimum": 0},
        "weight": {"type": "number", "exclusiveMinimum": 0.0},
    },
    "required": ["id", "name", "email", "status"],
}

# A deep, recursive shape: `$defs` + `$ref`, `allOf` composition, and arrays of nested objects —
# the paths most likely to regress when the reference resolver or composition logic changes.
_NESTED_SCHEMA: Final[dict[str, Any]] = {
    "$defs": {
        "Address": {
            "type": "object",
            "properties": {
                "street": {"type": "string"},
                "city": {"type": "string"},
                "zip": {"type": "string", "pattern": r"^\d{5}$"},
            },
            "required": ["street", "city"],
        },
        "Timestamps": {
            "type": "object",
            "properties": {
                "created_at": {"type": "string", "format": "date-time"},
                "updated_at": {"type": "string", "format": "date-time"},
            },
        },
        "Contact": {
            "allOf": [
                {"$ref": "#/$defs/Timestamps"},
                {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "emails": {
                            "type": "array",
                            "items": {"type": "string", "format": "email"},
                        },
                        "address": {"$ref": "#/$defs/Address"},
                    },
                    "required": ["name"],
                },
            ],
        },
    },
    "type": "object",
    "properties": {
        "owner": {"$ref": "#/$defs/Contact"},
        "billing_address": {"$ref": "#/$defs/Address"},
        "contacts": {"type": "array", "items": {"$ref": "#/$defs/Contact"}},
        "metadata": {
            "type": "object",
            "properties": {
                "labels": {"type": "array", "items": {"type": "string"}},
                "primary": {"$ref": "#/$defs/Address"},
            },
        },
    },
    "required": ["owner"],
}


def _strip_upper(value: str) -> str:
    """Normalize a string — the payload of the benchmarked rules, kept trivial on purpose."""
    return value.strip().upper()


def _annotation_is_int(context: MatchContext, /) -> bool:
    """Predicate for the `ByFunc` benchmark rule."""
    return context.annotation is int


# One rule per matcher kind. Rules are matched against every node the converter walks, so the cost
# scales with the rule count rather than with the number of nodes they actually hit — and a
# non-empty rule list also switches the model cache to a pointer-scoped key.
_RULES: Final[list[Rule]] = [
    Rule(ByType(str), After(_strip_upper)),
    Rule(ByPath("#/properties/name"), After(_strip_upper)),
    Rule(ByFunc(_annotation_is_int), After(abs)),
]


class TestConversionBenchmarks:
    """Time the converter on representative wide / nested / end-to-end schemas."""

    @pytest.mark.benchmark
    def test_to_model_wide(self, benchmark: "BenchmarkFixture") -> None:
        """Time `to_model` on a wide, flat schema (scalar + constraint coverage)."""
        schema = Schema.model_validate(_WIDE_SCHEMA)
        benchmark(lambda: to_model(schema))

    @pytest.mark.benchmark
    def test_to_model_nested(self, benchmark: "BenchmarkFixture") -> None:
        """Time `to_model` on a deep schema with `$ref` resolution and `allOf` composition."""
        schema = Schema.model_validate(_NESTED_SCHEMA)
        benchmark(lambda: to_model(schema))

    @pytest.mark.benchmark
    def test_validate_and_convert(self, benchmark: "BenchmarkFixture") -> None:
        """Time the full public entry path: `Schema.model_validate` followed by `to_model`."""
        benchmark(lambda: to_model(Schema.model_validate(_NESTED_SCHEMA)))

    @pytest.mark.benchmark
    def test_to_model_wide_with_rules(self, benchmark: "BenchmarkFixture") -> None:
        """Time `to_model` with one rule per matcher kind — the per-node matching cost."""
        schema = Schema.model_validate(_WIDE_SCHEMA)
        benchmark(lambda: to_model(schema, rules=_RULES))

    @pytest.mark.benchmark
    def test_to_model_nested_with_rules(self, benchmark: "BenchmarkFixture") -> None:
        """Time `to_model` with rules on a `$ref`-heavy schema (pointer-scoped model cache)."""
        schema = Schema.model_validate(_NESTED_SCHEMA)
        benchmark(lambda: to_model(schema, rules=_RULES))
