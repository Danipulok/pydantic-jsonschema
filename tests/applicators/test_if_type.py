"""Tests for type-specific keywords on a schema whose `type` does not pin their type."""

import json
from decimal import Decimal

import pytest
from inline_snapshot import snapshot
from pydantic import BaseModel, JsonValue, ValidationError

from pydantic_jsonschema import to_model
from pydantic_jsonschema.schema import Schema
from tests.conftest import SchemaRaw, dump_errors


def _field_model(field_schema: SchemaRaw, /) -> type[BaseModel]:
    """Convert an object schema whose required property `x` carries `field_schema`."""
    return to_model(
        Schema.model_validate(
            {"type": "object", "properties": {"x": field_schema}, "required": ["x"]}
        )
    )


class TestIfType:
    """Tests for `IfType` enforcement."""

    @pytest.mark.parametrize(
        ("field_schema", "passing", "failing", "error_type"),
        [
            pytest.param(
                {"minimum": 5},
                ["s", True, [1], 7],
                3,
                "greater_than_equal",
                id="minimum",
            ),
            pytest.param({"maximum": 0}, ["s", True, None], 1, "less_than_equal", id="maximum"),
            pytest.param(
                {"exclusiveMinimum": 5},
                ["s", 6],
                5,
                "greater_than",
                id="exclusive-minimum",
            ),
            pytest.param(
                {"exclusiveMaximum": 5},
                ["s", 4.5],
                5,
                "less_than",
                id="exclusive-maximum",
            ),
            pytest.param({"multipleOf": 2}, ["s", 4], 3, "multiple_of", id="multiple-of"),
            pytest.param(
                {"minLength": 2},
                [5, [1], "ab"],
                "a",
                "string_too_short",
                id="min-length",
            ),
            pytest.param(
                {"maxLength": 1},
                [55, [1, 2], "a"],
                "ab",
                "string_too_long",
                id="max-length",
            ),
            pytest.param(
                {"pattern": "^a"},
                [5, ["b"], "ab"],
                "b",
                "string_pattern_mismatch",
                id="pattern",
            ),
            pytest.param(
                {"maximum": 9007199254740992},
                ["s", 9007199254740992],
                9007199254740993,
                "less_than_equal",
                id="large-integer",
            ),
            pytest.param(
                {"minimum": 0},
                ["s", 10**400],
                -1,
                "greater_than_equal",
                id="integer-past-float",
            ),
            pytest.param(
                {"multipleOf": 2},
                ["s", 10**40],
                10**28 + 1,
                "multiple_of",
                id="multiple-of-large-integer",
            ),
            pytest.param(
                {"multipleOf": 0.5},
                ["s", 10**40 + 1],
                0.25,
                "multiple_of",
                id="fractional-multiple-of-large-integer",
            ),
            pytest.param(
                {"multipleOf": 1.5e-20},
                ["s", 3 * (10**40 + 1)],
                10**40 + 1,
                "multiple_of",
                id="small-multiple-of-large-integer",
            ),
            pytest.param(
                {"multipleOf": 0.1234567890123457},
                ["s", 8 * 1234567890123457 * 10**60],
                pow(10**16, -1, 1234567890123457) + 8 * 1234567890123457 * 10**60,
                "multiple_of",
                id="long-multiple-of-smallest-remainder",
            ),
            pytest.param(
                {"multipleOf": 1e22},
                ["s", 10**30],
                10**30 + 1,
                "multiple_of",
                id="positive-exponent-multiple-of",
            ),
            pytest.param(
                {"type": ["integer", "null"], "maximum": 9007199254740992},
                [None, 9007199254740992],
                9007199254740993,
                "less_than_equal",
                id="nullable-large-integer",
            ),
            pytest.param(
                {"type": ["integer", "null"], "minimum": 0.5},
                [None, 1],
                0,
                "greater_than_equal",
                id="fractional-bound",
            ),
            pytest.param(
                {"type": ["integer", "null"], "minimum": 5},
                [None, 7],
                "3",
                "greater_than_equal",
                id="coerced-type-list",
            ),
            pytest.param(
                {"anyOf": [{"type": "integer"}, {"type": "null"}], "minimum": 5},
                [None, 7],
                "3",
                "greater_than_equal",
                id="coerced-any-of",
            ),
            pytest.param(
                {"type": ["integer", "number"], "minimum": 5},
                [7, 7.5],
                3,
                "greater_than_equal",
                id="number-type-list",
            ),
            pytest.param(
                {"type": ["integer", "string"], "minimum": 5},
                ["a", 7],
                3,
                "greater_than_equal",
                id="type-list",
            ),
            pytest.param(
                {"type": ["integer", "null"], "maximum": 5},
                [None, 5],
                6,
                "less_than_equal",
                id="nullable-type",
            ),
            pytest.param(
                {"type": ["string", "array"], "maxLength": 1},
                [[1, 2], "a"],
                "ab",
                "string_too_long",
                id="type-list-length",
            ),
            pytest.param(
                {"enum": [1, 30, "x"], "maximum": 10},
                ["x", 1],
                30,
                "less_than_equal",
                id="enum",
            ),
            pytest.param(
                {"anyOf": [{"type": "integer"}, {"type": "string"}], "minimum": 5},
                ["a", 7],
                3,
                "greater_than_equal",
                id="any-of",
            ),
            pytest.param(
                {"minItems": 2},
                ["a", 5, [1, 2]],
                [1],
                "too_short",
                id="min-items",
            ),
            pytest.param(
                {"maxItems": 1},
                ["ab", 5, [1]],
                [1, 2],
                "too_long",
                id="max-items",
            ),
            pytest.param(
                {"items": {"type": "integer"}},
                ["s", 5, [1]],
                ["a"],
                "int_parsing",
                id="items",
            ),
            pytest.param(
                {"prefixItems": [{"type": "integer"}]},
                ["s", [1, "x"]],
                ["a"],
                "value_error",
                id="prefix-items",
            ),
            pytest.param(
                {"contains": {"type": "integer"}},
                ["s", [1]],
                ["a"],
                "value_error",
                id="contains",
            ),
            pytest.param(
                {"uniqueItems": True},
                ["aa", [1, 2]],
                [1, 1],
                "value_error",
                id="unique-items",
            ),
            pytest.param(
                {"type": ["string", "array"], "maxItems": 1},
                ["abc", [1]],
                [1, 2],
                "too_long",
                id="type-list-items",
            ),
            pytest.param(
                {"type": ["array", "null"], "items": {"type": "integer"}},
                [None, [1]],
                ["a"],
                "int_parsing",
                id="nullable-array",
            ),
        ],
    )
    def test_keywords_check_their_type_only(
        self,
        *,
        field_schema: SchemaRaw,
        passing: list[JsonValue],
        failing: JsonValue,
        error_type: str,
    ) -> None:
        """A keyword checks values of its type, and every other value passes unchanged."""
        model = _field_model(field_schema)

        for value in passing:
            assert model.model_validate({"x": value}).model_dump() == {"x": value}

        with pytest.raises(ValidationError) as exc_info:
            model.model_validate({"x": failing})

        assert [error["type"] for error in dump_errors(exc_info.value)] == [error_type]

    def test_integer_error_reports_its_bound_as_a_number(self) -> None:
        """An integer's error carries the bound as the `float` branch reports it, JSON-ready."""
        model = _field_model({"type": ["integer", "null"], "minimum": 5})

        with pytest.raises(ValidationError) as exc_info:
            model.model_validate({"x": 3})

        assert json.loads(exc_info.value.json(include_url=False)) == snapshot(
            [
                {
                    "type": "greater_than_equal",
                    "loc": ["x"],
                    "msg": "Input should be greater than or equal to 5",
                    "input": 3,
                    "ctx": {"ge": 5.0},
                }
            ]
        )

    def test_number_keywords_check_a_decimal(self) -> None:
        """A `Decimal`, as `json.loads(..., parse_float=Decimal)` gives, is a number to check."""
        model = _field_model({"minimum": 5})

        assert model.model_validate({"x": Decimal(7)}).model_dump() == {"x": Decimal(7)}

        with pytest.raises(ValidationError) as exc_info:
            model.model_validate({"x": Decimal("3.5")})

        assert [error["type"] for error in dump_errors(exc_info.value)] == ["greater_than_equal"]

    @pytest.mark.parametrize(
        ("field_schema", "value"),
        [
            pytest.param({"type": "integer", "maxLength": 1}, 55, id="integer-max-length"),
            pytest.param({"type": "string", "minimum": 1}, "a", id="string-minimum"),
            pytest.param({"type": "array", "pattern": "^a"}, ["b"], id="array-pattern"),
        ],
    )
    def test_keywords_of_an_excluded_type_are_ignored(
        self,
        *,
        field_schema: SchemaRaw,
        value: JsonValue,
    ) -> None:
        """A keyword of a type the `type` excludes checks nothing."""
        model = _field_model(field_schema)

        assert model.model_validate({"x": value}).model_dump() == {"x": value}

    @pytest.mark.parametrize(
        ("field_schema", "passing", "failing"),
        [
            pytest.param({"not": {"minimum": 5}}, 3, "s", id="not"),
            pytest.param({"not": {"items": {"type": "string"}}}, [1], ["a"], id="not-items"),
            pytest.param(
                {"if": {"minimum": 5}, "then": {"type": "integer"}},
                3,
                "s",
                id="if",
            ),
            pytest.param(
                {"anyOf": [{"minLength": 2}, {"type": "null"}]},
                5,
                "a",
                id="any-of-branch",
            ),
            pytest.param(
                {"oneOf": [{"minLength": 2}, {"type": "null"}]},
                5,
                "a",
                id="one-of-branch",
            ),
            pytest.param(
                {"allOf": [{"minLength": 2}, {"maxLength": 3}]},
                5,
                "a",
                id="all-of-branch",
            ),
            pytest.param({"allOf": [{}], "minLength": 2}, 5, "a", id="all-of-sibling"),
            pytest.param({"allOf": [{}], "maxItems": 1}, 5, [1, 2], id="all-of-sibling-items"),
            pytest.param(
                {"type": "array", "prefixItems": [{"minimum": 5}]},
                ["s"],
                [3],
                id="prefix-items",
            ),
            pytest.param(
                {"type": "array", "prefixItems": [{}], "items": {"minimum": 5}},
                [0, "s"],
                [0, 3],
                id="prefix-items-tail",
            ),
            pytest.param({"type": "array", "contains": {"minimum": 5}}, ["s"], [3], id="contains"),
            pytest.param(
                {"type": "object", "patternProperties": {"^a": {"minimum": 5}}},
                {"a": "s"},
                {"a": 3},
                id="pattern-properties",
            ),
            pytest.param(
                {"type": "object", "propertyNames": {"maxLength": 1}},
                {"a": 1},
                {"ab": 1},
                id="property-names",
            ),
            pytest.param(
                {
                    "type": "object",
                    "dependentSchemas": {"a": {"properties": {"b": {"minimum": 5}}}},
                },
                {"a": 1, "b": "s"},
                {"a": 1, "b": 3},
                id="dependent-schemas",
            ),
        ],
    )
    def test_keywords_check_their_type_in_a_subschema(
        self,
        *,
        field_schema: SchemaRaw,
        passing: JsonValue,
        failing: JsonValue,
    ) -> None:
        """A subschema's keyword checks values of its type wherever the subschema applies."""
        model = _field_model(field_schema)

        assert model.model_validate({"x": passing}).model_dump() == {"x": passing}

        with pytest.raises(ValidationError):
            model.model_validate({"x": failing})

    @pytest.mark.parametrize(
        ("field_schema", "dumped"),
        [
            pytest.param(
                {"minimum": 5, "not": {"const": 7}},
                {"minimum": 5.0, "not": {"const": 7, "type": "integer"}, "title": "X"},
                id="not",
            ),
            pytest.param(
                {"type": ["integer", "number"], "minimum": 5},
                {
                    "anyOf": [{"type": "integer"}, {"type": "number"}],
                    "minimum": 5.0,
                    "title": "X",
                },
                id="type-list",
            ),
        ],
    )
    def test_keywords_dump_beside_the_host(
        self,
        *,
        field_schema: SchemaRaw,
        dumped: SchemaRaw,
    ) -> None:
        """The keywords dump once, beside an assertion and over a union host."""
        model = _field_model(field_schema)

        assert model.model_json_schema()["properties"]["x"] == dumped

    def test_keywords_dump_as_json_schema(self) -> None:
        """The keywords dump under their JSON Schema names, beside the host's own."""
        model = _field_model(
            {
                "enum": [1, "x"],
                "minimum": 0,
                "exclusiveMaximum": 9,
                "multipleOf": 1,
                "minLength": 1,
                "pattern": "^x",
            }
        )

        assert model.model_json_schema()["properties"]["x"] == snapshot(
            {
                "enum": [1, "x"],
                "exclusiveMaximum": 9.0,
                "minLength": 1,
                "minimum": 0.0,
                "multipleOf": 1.0,
                "pattern": "^x",
                "title": "X",
            }
        )

    def test_array_keywords_dump_as_json_schema(self) -> None:
        """The array keywords dump under their JSON Schema names, beside the host's own."""
        model = _field_model(
            {
                "type": ["string", "array"],
                "items": {"type": "integer"},
                "minItems": 1,
                "maxItems": 2,
            }
        )

        assert model.model_json_schema()["properties"]["x"] == snapshot(
            {
                "anyOf": [{"type": "string"}, {"items": {}, "type": "array"}],
                "items": {"type": "integer"},
                "maxItems": 2,
                "minItems": 1,
                "title": "X",
            }
        )

    def test_array_keywords_check_a_coerced_tuple(self) -> None:
        """A tuple the host turns into a list is checked as that list."""
        model = _field_model({"type": ["array", "null"], "maxItems": 1})

        assert model.model_validate({"x": (1,)}).model_dump() == {"x": [1]}

        with pytest.raises(ValidationError) as exc_info:
            model.model_validate({"x": (1, 2)})

        assert [error["type"] for error in dump_errors(exc_info.value)] == ["too_long"]

    def test_array_keywords_refer_back_to_their_def(self) -> None:
        """Untyped `items` referring back to the def it sits in resolves once the def is built."""
        model = to_model(
            Schema.model_validate(
                {
                    "$defs": {"T": {"items": {"$ref": "#/$defs/T"}, "maxItems": 2}},
                    "type": "object",
                    "properties": {"x": {"$ref": "#/$defs/T"}},
                    "required": ["x"],
                }
            )
        )

        assert model.model_validate({"x": [[], [[]]]}).model_dump() == {"x": [[], [[]]]}

        with pytest.raises(ValidationError) as exc_info:
            model.model_validate({"x": [[1, 2, 3]]})

        assert [error["type"] for error in dump_errors(exc_info.value)] == ["too_long"]
