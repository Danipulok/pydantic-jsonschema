"""Tests for the `allOf` applicator."""

from typing import Final
from uuid import UUID

import pytest
from inline_snapshot import snapshot
from pydantic import ValidationError

from pydantic_jsonschema import (
    to_model,
)
from pydantic_jsonschema.applicators import Not
from pydantic_jsonschema.applicators._base import AnnotationType
from pydantic_jsonschema.schema import Schema
from tests.conftest import SchemaRaw, dump_errors

__all__: list[str] = []

_OBJECT: Final[SchemaRaw] = {"type": "object"}
_OBJECT_X: Final[SchemaRaw] = {"type": "object", "properties": {"x": {"type": "integer"}}}
_ARRAY: Final[SchemaRaw] = {"type": "array"}
_NUMBER: Final[SchemaRaw] = {"type": "number"}
_STRING: Final[SchemaRaw] = {"type": "string"}
_REQUIRED_B: Final[SchemaRaw] = {"type": "object", "required": ["b"]}
_REQUIRED_C: Final[SchemaRaw] = {"type": "object", "required": ["c"]}
_BESIDE: Final[str] = "Value does not match the keywords beside `allOf`"
_NOT: Final[str] = "Value must not match the `not` schema"


class TestAllOf:
    """Tests for `allOf` enforcement beyond the branch that produces the value."""

    @pytest.mark.parametrize(
        ("schema_raw", "valid", "invalid", "loc", "msg"),
        [
            pytest.param(
                {"type": "string", "allOf": [{"minLength": 2}, {"maxLength": 3}]},
                "abc",
                "abcd",
                (),
                "Value does not match `allOf[1]`",
                id="string-branches",
            ),
            pytest.param(
                {"type": "string", "maxLength": 3, "allOf": [{"minLength": 2}]},
                "abc",
                "abcd",
                (),
                _BESIDE,
                id="string-own-keyword",
            ),
            pytest.param(
                {"allOf": [{"type": "integer"}, {"minimum": 5}]},
                7,
                1,
                (),
                "Value does not match `allOf[1]`",
                id="untyped-scalar-branches",
            ),
            pytest.param(
                {"type": "object", "allOf": [{"minProperties": 1}]},
                {"a": 1},
                5,
                (),
                _BESIDE,
                id="object-type-over-untyped-branch",
            ),
            pytest.param(
                {
                    "type": "integer",
                    "allOf": [{"$ref": "#/$defs/Small"}],
                    "$defs": {
                        "Small": {"maximum": 9},
                    },
                },
                7,
                7.5,
                (),
                _BESIDE,
                id="ref-branch",
            ),
            pytest.param(
                {
                    "type": "object",
                    "properties": {"a": {"type": "integer"}},
                    "allOf": [{"type": "object", "additionalProperties": {"type": "integer"}}],
                },
                {"a": 1},
                {"a": 1, "b": "x"},
                (),
                "Value does not match `allOf[0]`",
                id="object-properties-over-untyped-branch",
            ),
            pytest.param(
                {"allOf": [{"type": "string"}], "not": {"const": "x"}},
                "y",
                "x",
                (),
                _NOT,
                id="root-not",
            ),
            pytest.param(
                {
                    "type": "object",
                    "properties": {"s": {"allOf": [{"type": "string"}, {"maxLength": 2}]}},
                    "required": ["s"],
                },
                {"s": "ab"},
                {"s": "abc"},
                ("s",),
                "Value does not match `allOf[1]`",
                id="property",
            ),
            pytest.param(
                {
                    "type": "object",
                    "properties": {"s": {"allOf": [{"type": "string"}], "maxLength": 2}},
                    "required": ["s"],
                },
                {"s": "ab"},
                {"s": "abc"},
                ("s",),
                _BESIDE,
                id="property-own-keyword",
            ),
            pytest.param(
                {
                    "type": "object",
                    "properties": {"s": {"$ref": "#/$defs/S"}},
                    "required": ["s"],
                    "$defs": {"S": {"allOf": [{"type": "string"}], "maxLength": 2}},
                },
                {"s": "ab"},
                {"s": "abc"},
                ("s",),
                _BESIDE,
                id="ref-own-keyword",
            ),
            pytest.param(
                {
                    "type": "object",
                    "properties": {
                        "s": {"anyOf": [{"allOf": [{"type": "string"}], "maxLength": 2}]},
                    },
                    "required": ["s"],
                },
                {"s": "ab"},
                {"s": "abc"},
                ("s",),
                _BESIDE,
                id="any-of-branch-own-keyword",
            ),
            pytest.param(
                {
                    "type": "object",
                    "properties": {"s": {"$ref": "#/$defs/S"}},
                    "required": ["s"],
                    "$defs": {"S": {"allOf": [{"type": "string"}], "not": {"const": "x"}}},
                },
                {"s": "y"},
                {"s": "x"},
                ("s",),
                _NOT,
                id="ref-not",
            ),
        ],
    )
    def test_all_of_value(
        self,
        *,
        schema_raw: SchemaRaw,
        valid: AnnotationType,
        invalid: AnnotationType,
        loc: tuple[str, ...],
        msg: str,
    ) -> None:
        """Test a value produced by one branch is checked against the rest of the schema."""
        model = to_model(Schema.model_validate(schema_raw))

        assert model.model_validate(valid).model_dump() == valid

        with pytest.raises(ValidationError) as exc_info:
            model.model_validate(invalid)

        assert dump_errors(exc_info.value) == [
            {
                "type": "value_error",
                "loc": loc,
                "msg": f"Value error, {msg}",
                "input": invalid[loc[0]] if loc else invalid,
            }
        ]

    def test_all_of_untyped_bound_skips_other_types(self) -> None:
        """Test a branch bound without `type` passes a value it does not apply to."""
        schema = Schema.model_validate({"allOf": [{"type": "string"}, {"minimum": 5}]})
        model = to_model(schema)

        assert model.model_validate("a").model_dump() == snapshot("a")

    def test_all_of_own_format(self) -> None:
        """Test a `format` beside `allOf` is checked with the registered format type."""
        schema = Schema.model_validate(
            {"type": "string", "format": "uuid", "allOf": [{"minLength": 1}]}
        )
        model = to_model(schema, formats={"uuid": UUID})

        assert model.model_validate(
            "0192d6e4-0000-7000-8000-000000000000"
        ).model_dump() == snapshot("0192d6e4-0000-7000-8000-000000000000")

        with pytest.raises(ValidationError) as exc_info:
            model.model_validate("abc")

        assert [error["msg"] for error in dump_errors(exc_info.value)] == snapshot(
            ["Value error, Value does not match the keywords beside `allOf`"]
        )

    @pytest.mark.parametrize(
        ("value", "msg"),
        [
            pytest.param(
                {},
                "Value error, Value does not match the keywords beside `allOf`",
                id="object",
            ),
            pytest.param(
                "a",
                "Input should be a valid dictionary or instance of Model",
                id="string",
            ),
        ],
    )
    def test_all_of_type_conflicting_with_object_branches(
        self,
        value: SchemaRaw | str,
        msg: str,
    ) -> None:
        """Test a non-object `type` beside object branches rejects objects and its own type."""
        schema = Schema.model_validate({"type": "string", "allOf": [{"type": "object"}]})
        model = to_model(schema)

        with pytest.raises(ValidationError) as exc_info:
            model.model_validate(value)

        assert [error["msg"] for error in dump_errors(exc_info.value)] == [msg]

    @pytest.mark.parametrize(
        ("schema_raw", "payload", "checked"),
        [
            pytest.param(
                {
                    "type": "object",
                    "properties": {"a": {"type": "integer"}},
                    "allOf": [{"type": "object", "properties": {"b": {"type": "integer"}}}],
                    "not": {"const": {"a": 2}},
                },
                {"a": 1},
                {"a": 1},
                id="root-object",
            ),
            pytest.param(
                {
                    "type": "object",
                    "properties": {
                        "p": {
                            "allOf": [{"type": "object", "properties": {"a": {"type": "integer"}}}],
                            "not": {"const": {"a": 2}},
                        },
                    },
                },
                {"p": {"a": 1}},
                {"a": 1},
                id="nested-property",
            ),
        ],
    )
    def test_all_of_not_runs_once(
        self,
        monkeypatch: pytest.MonkeyPatch,
        *,
        schema_raw: SchemaRaw,
        payload: dict[str, int | dict[str, int]],
        checked: dict[str, int],
    ) -> None:
        """Test a `not` beside an object `allOf` runs once per value, at the root and nested."""
        inputs: list[AnnotationType] = []
        validate = Not.validate

        def record(self: Not, data: AnnotationType, /) -> AnnotationType:
            inputs.append(data)
            return validate(self, data)

        monkeypatch.setattr(Not, "validate", record)
        model = to_model(Schema.model_validate(schema_raw))

        model.model_validate(payload)

        assert inputs == [checked]

    def test_all_of_recursive_own_keywords(self) -> None:
        """Test the keywords beside `allOf` in a recursive def resolve its `$ref`."""
        schema = Schema.model_validate(
            {
                "type": "object",
                "properties": {"t": {"$ref": "#/$defs/T"}},
                "required": ["t"],
                "$defs": {
                    "T": {
                        "type": "array",
                        "allOf": [{"type": "array"}],
                        "items": {"$ref": "#/$defs/T"},
                        "maxItems": 1,
                    },
                },
            }
        )
        model = to_model(schema)

        assert model.model_validate({"t": [[[]]]}).model_dump() == snapshot({"t": [[[]]]})

        with pytest.raises(ValidationError) as exc_info:
            model.model_validate({"t": [[], []]})

        assert dump_errors(exc_info.value) == snapshot(
            [
                {
                    "type": "value_error",
                    "loc": ("t",),
                    "msg": "Value error, Value does not match the keywords beside `allOf`",
                    "input": [[], []],
                }
            ]
        )

    @pytest.mark.parametrize(
        ("own", "valid", "invalid"),
        [
            pytest.param(
                {"anyOf": [{"type": "integer"}], "not": {"const": 3}},
                4,
                3,
                id="any-of-not",
            ),
            pytest.param({"anyOf": [{"type": "integer"}], "maximum": 5}, 4, 9, id="any-of-bound"),
            pytest.param(
                {"enum": ["a", "abcd"], "not": {"const": "a"}},
                "abcd",
                "a",
                id="enum-not",
            ),
            pytest.param({"enum": ["a", "abcd"], "maxLength": 3}, "a", "abcd", id="enum-bound"),
        ],
    )
    def test_all_of_beside_preceding_keyword(
        self,
        *,
        own: SchemaRaw,
        valid: AnnotationType,
        invalid: AnnotationType,
    ) -> None:
        """Test the keywords beside an `allOf` that `enum` or `anyOf` overrides are checked."""
        schema = Schema.model_validate(
            {
                "type": "object",
                "properties": {"p": {"allOf": [{"type": ["integer", "string"]}], **own}},
                "required": ["p"],
            }
        )
        model = to_model(schema)

        assert model.model_validate({"p": valid}).model_dump() == {"p": valid}

        with pytest.raises(ValidationError):
            model.model_validate({"p": invalid})


class TestAllOfObjects:
    """Tests for `allOf` over object branches."""

    def test_all_of_untyped_object_branches(self) -> None:
        """Test an untyped `allOf` over two object branches requires the fields of both."""
        schema = Schema.model_validate(
            {
                "allOf": [
                    {"type": "object", "properties": {"x": {"type": "integer"}}, "required": ["x"]},
                    {"type": "object", "properties": {"y": {"type": "integer"}}, "required": ["y"]},
                ]
            }
        )
        model = to_model(schema)

        assert model.model_validate({"x": 1, "y": 2}).model_dump() == snapshot({"x": 1, "y": 2})

        with pytest.raises(ValidationError) as exc_info:
            model.model_validate({"x": 1})

        assert dump_errors(exc_info.value) == snapshot(
            [{"type": "missing", "loc": ("y",), "msg": "Field required", "input": {"x": 1}}]
        )

    @pytest.mark.parametrize(
        "schema_raw",
        [
            pytest.param(
                {
                    "allOf": [{"$ref": "#/$defs/A"}, {"$ref": "#/$defs/A"}],
                    "$defs": {"A": {"type": "object", "properties": {"a": {"type": "integer"}}}},
                },
                id="ref",
            ),
            pytest.param(
                {
                    "type": "object",
                    "allOf": [{"$ref": "#/$defs/A"}, {"$ref": "#/$defs/A"}],
                    "$defs": {"A": {"type": "object", "properties": {"a": {"type": "integer"}}}},
                },
                id="typed-ref",
            ),
            pytest.param(
                {
                    "allOf": [
                        {"type": "object", "properties": {"a": {"type": "integer"}}},
                        {"type": "object", "properties": {"a": {"type": "integer"}}},
                    ]
                },
                id="inline",
            ),
            pytest.param(
                {
                    "type": "object",
                    "properties": {"b": {"type": "integer"}},
                    "allOf": [
                        {"type": "object", "properties": {"a": {"type": "integer"}}},
                        {"type": "object", "properties": {"a": {"type": "integer"}}},
                    ],
                },
                id="inline-beside-properties",
            ),
        ],
    )
    def test_all_of_repeated_object_branch(self, schema_raw: SchemaRaw) -> None:
        """Test an object branch repeated in `allOf` converts to one base."""
        model = to_model(Schema.model_validate(schema_raw))

        assert model.model_validate({"a": "1"}).model_dump(exclude_unset=True) == snapshot({"a": 1})

    @pytest.mark.parametrize(
        ("schema_raw", "payload"),
        [
            pytest.param(
                {"type": "object", "allOf": [{"$ref": "#/$defs/R"}], "maxProperties": 2},
                {"toolong": 1},
                id="beside-keyword",
            ),
            pytest.param(
                {
                    "type": "object",
                    "allOf": [
                        {"$ref": "#/$defs/R"},
                        {"type": "object", "propertyNames": {"minLength": 2}},
                    ],
                },
                {"toolong": 1},
                id="beside-object-branch-ref-check",
            ),
            pytest.param(
                {
                    "type": "object",
                    "allOf": [
                        {"$ref": "#/$defs/R"},
                        {"type": "object", "propertyNames": {"minLength": 2}},
                    ],
                },
                {"a": 1},
                id="beside-object-branch-own-check",
            ),
        ],
    )
    def test_all_of_keeps_applicators_of_a_ref_model(
        self,
        schema_raw: SchemaRaw,
        payload: dict[str, int],
    ) -> None:
        """Test an `allOf` over a model from another conversion keeps every applicator."""
        referenced = to_model(
            Schema.model_validate(
                {"type": "object", "properties": {"a": {}}, "propertyNames": {"maxLength": 1}}
            )
        )
        model = to_model(
            Schema.model_validate(schema_raw),
            refs={"#/$defs/R": referenced},
        )

        with pytest.raises(ValidationError, match="propertyNames"):
            model.model_validate(payload)

    def test_all_of_type_list(self) -> None:
        """Test an `allOf` beside a list `type` converts, and its object branch still applies."""
        schema = Schema.model_validate(
            {
                "type": ["object", "null"],
                "allOf": [
                    {"type": "object", "properties": {"x": {"type": "integer"}}, "required": ["x"]}
                ],
            }
        )
        model = to_model(schema)

        assert model.model_validate({"x": 1}).model_dump() == snapshot({"x": 1})

        with pytest.raises(ValidationError):
            model.model_validate(None)

    def test_all_of_one_of_required_branch(self) -> None:
        """Test a `oneOf` of typed `required` branches beside object branches matches one."""
        schema = Schema.model_validate(
            {
                "allOf": [
                    {"type": "object", "properties": {"k": {}}},
                    {
                        "oneOf": [
                            {"type": "object", "required": ["a"]},
                            {"type": "object", "required": ["b"]},
                        ]
                    },
                ]
            }
        )
        model = to_model(schema)

        assert model.model_validate({"a": 1}).model_dump() == snapshot({"a": 1})

        with pytest.raises(ValidationError):
            model.model_validate({"a": 1, "b": 1})

        with pytest.raises(ValidationError):
            model.model_validate({})

    def test_all_of_untyped_properties_over_object_branches(self) -> None:
        """Test an untyped schema with `properties` over object branches builds one object model."""
        schema = Schema.model_validate(
            {
                "properties": {"y": {"type": "integer"}},
                "required": ["y"],
                "allOf": [{"type": "object", "properties": {"x": {"type": "integer"}}}],
            }
        )
        model = to_model(schema)

        assert model.model_validate({"x": "1", "y": "2"}).model_dump() == snapshot({"x": 1, "y": 2})

    @pytest.mark.parametrize(
        ("branch", "own", "valid", "invalid"),
        [
            pytest.param(_OBJECT, {"enum": [{"a": 1}]}, {"a": 1}, {"a": 2}, id="enum"),
            pytest.param(_OBJECT, {"const": {"a": 1}}, {"a": 1}, {"a": 2}, id="const"),
            pytest.param(
                _OBJECT,
                {"properties": {"a": {"type": "integer"}}},
                {"a": 1},
                {"a": "s"},
                id="properties",
            ),
            pytest.param(
                _OBJECT,
                {"patternProperties": {"^x": {"type": "integer"}}},
                {"x1": 1},
                {"x1": "s"},
                id="pattern-properties",
            ),
            pytest.param(
                _OBJECT,
                {"propertyNames": {"maxLength": 1}},
                {"a": 1},
                {"ab": 1},
                id="property-names",
            ),
            pytest.param(_OBJECT, {"required": ["b"]}, {"b": 1}, {"a": 1}, id="required"),
            pytest.param(
                _OBJECT_X,
                {"minProperties": 2},
                {"x": 1, "y": 1},
                {"x": 1},
                id="min-properties",
            ),
            pytest.param(_OBJECT_X, {"maxProperties": 0}, {}, {"x": 1}, id="max-properties"),
            pytest.param(
                _OBJECT_X,
                {"additionalProperties": False},
                {},
                {"x": 1},
                id="no-additional",
            ),
            pytest.param(
                _OBJECT,
                {"dependentRequired": {"a": ["b"]}},
                {"a": 1, "b": 1},
                {"a": 1},
                id="dependent-required",
            ),
            pytest.param(
                _OBJECT,
                {"dependentSchemas": {"a": {"type": "object", "required": ["b"]}}},
                {"a": 1, "b": 1},
                {"a": 1},
                id="dependent-schemas",
            ),
            pytest.param(
                _OBJECT,
                {"anyOf": [_REQUIRED_B, _REQUIRED_C]},
                {"b": 1},
                {"a": 1},
                id="any-of",
            ),
            pytest.param(
                _OBJECT,
                {"oneOf": [_REQUIRED_B, _REQUIRED_C]},
                {"b": 1},
                {"b": 1, "c": 1},
                id="one-of",
            ),
            pytest.param(
                _ARRAY,
                {"type": "array", "items": {"type": "integer"}},
                [1],
                ["s"],
                id="items",
            ),
            pytest.param(
                _ARRAY,
                {"type": "array", "prefixItems": [{"type": "integer"}]},
                [1],
                ["s"],
                id="prefix-items",
            ),
            pytest.param(
                _ARRAY,
                {"type": "array", "contains": {"type": "integer"}},
                [1],
                ["s"],
                id="contains",
            ),
            pytest.param(
                _ARRAY,
                {"type": "array", "contains": {"type": "integer"}, "maxContains": 1},
                [1],
                [1, 2],
                id="max-contains",
            ),
            pytest.param(
                _ARRAY,
                {"type": "array", "contains": {"type": "integer"}, "minContains": 2},
                [1, 2],
                [1],
                id="min-contains",
            ),
            pytest.param(_ARRAY, {"type": "array", "minItems": 1}, [1], [], id="min-items"),
            pytest.param(_ARRAY, {"type": "array", "maxItems": 1}, [1], [1, 2], id="max-items"),
            pytest.param(
                _ARRAY,
                {"type": "array", "uniqueItems": True},
                [1, 2],
                [1, 1],
                id="unique-items",
            ),
            pytest.param(_NUMBER, {"multipleOf": 2}, 4, 3, id="multiple-of"),
            pytest.param(_NUMBER, {"maximum": 1}, 1, 2, id="maximum"),
            pytest.param(_NUMBER, {"exclusiveMaximum": 1}, 0, 1, id="exclusive-maximum"),
            pytest.param(_NUMBER, {"minimum": 1}, 1, 0, id="minimum"),
            pytest.param(_NUMBER, {"exclusiveMinimum": 1}, 2, 1, id="exclusive-minimum"),
            pytest.param(_STRING, {"minLength": 2}, "ab", "a", id="min-length"),
            pytest.param(_STRING, {"maxLength": 1}, "a", "ab", id="max-length"),
            pytest.param(_STRING, {"pattern": "^a"}, "a", "b", id="pattern"),
        ],
    )
    def test_all_of_checks_every_keyword_beside_it(
        self,
        *,
        branch: SchemaRaw,
        own: SchemaRaw,
        valid: AnnotationType,
        invalid: AnnotationType,
    ) -> None:
        """Test each validating keyword beside `allOf` is checked."""
        model = to_model(Schema.model_validate({"allOf": [branch], **own}))

        assert model.model_validate(valid).model_dump() == valid

        with pytest.raises(ValidationError):
            model.model_validate(invalid)

    @pytest.mark.parametrize(
        "property_schema",
        [
            pytest.param(
                {
                    "oneOf": [{"type": "string"}, {"type": "integer"}],
                    "allOf": [{"type": "string"}],
                    "maxLength": 2,
                },
                id="one-of",
            ),
            pytest.param(
                {"const": "abc", "allOf": [{"type": "string"}], "maxLength": 2},
                id="const",
            ),
        ],
    )
    def test_all_of_property_keywords_beside_producer(self, *, property_schema: SchemaRaw) -> None:
        """Test a property whose `oneOf` or `const` produces the value still checks `maxLength`."""
        schema = Schema.model_validate({"type": "object", "properties": {"s": property_schema}})
        model = to_model(schema)

        with pytest.raises(ValidationError):
            model.model_validate({"s": "abc"})

    @pytest.mark.parametrize(
        "own",
        [
            pytest.param({"maxLength": 1}, id="string"),
            pytest.param({"minimum": 5}, id="number"),
            pytest.param({"minItems": 5}, id="array"),
        ],
    )
    def test_all_of_object_ignores_other_type_keywords(self, own: SchemaRaw) -> None:
        """Test a string, number or array keyword beside an object `allOf` ignores the object."""
        model = to_model(Schema.model_validate({"allOf": [{"type": "object"}], **own}))

        assert model.model_validate({"a": 1, "b": 2}).model_dump() == {"a": 1, "b": 2}

    @pytest.mark.parametrize(
        ("schema_raw", "invalid", "msg"),
        [
            pytest.param(
                {
                    "allOf": [
                        {
                            "type": "object",
                            "properties": {"a": {}},
                            "patternProperties": {"^x": {"type": "integer"}},
                        },
                        {"maxProperties": 3},
                    ]
                },
                {"a": 1, "x1": "s"},
                "Value error, Property `x1` does not satisfy its `patternProperties` schema",
                id="object-branch-applicator",
            ),
            pytest.param(
                {"allOf": [{"allOf": [{"type": "string"}, {"maxLength": 2}]}, {"minLength": 1}]},
                "abc",
                "Value error, Value does not match `allOf[1]`",
                id="nested-all-of",
            ),
        ],
    )
    def test_all_of_keeps_branch_applicators(
        self,
        schema_raw: SchemaRaw,
        invalid: SchemaRaw | str,
        msg: str,
    ) -> None:
        """Test the applicators of the branch producing the value still run under `AllOf`."""
        model = to_model(Schema.model_validate(schema_raw))

        with pytest.raises(ValidationError) as exc_info:
            model.model_validate(invalid)

        assert [error["msg"] for error in dump_errors(exc_info.value)] == [msg]

    @pytest.mark.parametrize(
        ("first", "second", "invalid", "msg"),
        [
            pytest.param(
                {"required": ["a"]},
                {"required": ["b"]},
                {"a": 1},
                "Value error, Object must have the properties `b`",
                id="required",
            ),
            pytest.param(
                {"dependentRequired": {"a": ["x"]}},
                {"dependentRequired": {"c": ["y"]}},
                {"c": 1},
                "Value error, Property `c` requires `y`",
                id="dependent-required",
            ),
            pytest.param(
                {"minProperties": 1},
                {"maxProperties": 1},
                {"a": 1, "b": 2},
                "Value error, Object must have at most `1` properties",
                id="property-count",
            ),
            pytest.param(
                {"propertyNames": {"maxLength": 3}},
                {"propertyNames": {"minLength": 2}},
                {"a": 1},
                "Value error, Property name `a` does not satisfy the `propertyNames` schema",
                id="applicator",
            ),
        ],
    )
    def test_all_of_checks_every_object_branch(
        self,
        *,
        first: SchemaRaw,
        second: SchemaRaw,
        invalid: SchemaRaw,
        msg: str,
    ) -> None:
        """Test the same object keyword on two object branches is checked for both."""
        schema = Schema.model_validate(
            {"allOf": [{"type": "object", **first}, {"type": "object", **second}]}
        )
        model = to_model(schema)

        with pytest.raises(ValidationError) as exc_info:
            model.model_validate(invalid)

        assert [error["msg"] for error in dump_errors(exc_info.value)] == [msg]


class TestAllOfJsonSchema:
    """`allOf` round-trips into the dumped JSON Schema."""

    def test_all_of_round_trips(self) -> None:
        """A non-object `allOf` re-emits the branches it checks on `model_json_schema()`."""
        model = to_model(
            Schema.model_validate({"type": "string", "allOf": [{"minLength": 2}, {"maxLength": 3}]})
        )

        assert model.model_json_schema() == snapshot(
            {
                "$defs": {"ModelAllOf1": {"maxLength": 3, "title": "ModelAllOf1"}},
                "allOf": [{"$ref": "#/$defs/ModelAllOf1"}, {"type": "string"}],
                "minLength": 2,
                "title": "Model",
            }
        )

    def test_all_of_untyped_round_trips(self) -> None:
        """An untyped `allOf` with no keywords beside it emits only the branches it checks."""
        model = to_model(Schema.model_validate({"allOf": [{"type": "integer"}, {"maximum": 9}]}))

        assert model.model_json_schema() == snapshot(
            {
                "$defs": {"ModelAllOf1": {"le": 9.0, "title": "ModelAllOf1"}},
                "allOf": [{"$ref": "#/$defs/ModelAllOf1"}],
                "title": "Model",
                "type": "integer",
            }
        )

    def test_all_of_objects_round_trip(self) -> None:
        """An `allOf` over object branches with only metadata beside it dumps as one model."""
        model = to_model(
            Schema.model_validate(
                {
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "$id": "https://example.com/model.json",
                    "type": "object",
                    "allOf": [
                        {"type": "object", "properties": {"x": {"type": "integer"}}},
                        {"type": "object", "properties": {"y": {"type": "integer"}}},
                    ],
                }
            )
        )

        assert model.model_json_schema() == snapshot(
            {
                "additionalProperties": True,
                "properties": {
                    "y": {"title": "Y", "type": "integer"},
                    "x": {"title": "X", "type": "integer"},
                },
                "title": "Model",
                "type": "object",
            }
        )

    def test_all_of_ref_with_metadata_round_trips(self) -> None:
        """A property `allOf` over one `$ref` with only metadata beside it dumps as the `$ref`."""
        model = to_model(
            Schema.model_validate(
                {
                    "type": "object",
                    "properties": {
                        "address": {
                            "allOf": [{"$ref": "#/$defs/Address"}],
                            "title": "Address",
                            "description": "Home address",
                            "readOnly": True,
                        },
                    },
                    "$defs": {
                        "Address": {
                            "type": "object",
                            "properties": {"city": {"type": "string"}},
                        },
                    },
                }
            )
        )

        assert model.model_json_schema() == snapshot(
            {
                "$defs": {
                    "Model": {
                        "additionalProperties": True,
                        "properties": {"city": {"title": "City", "type": "string"}},
                        "title": "Model",
                        "type": "object",
                    }
                },
                "additionalProperties": True,
                "properties": {
                    "address": {
                        "$ref": "#/$defs/Model",
                        "description": "Home address",
                        "title": "Address",
                    }
                },
                "title": "Model",
                "type": "object",
            }
        )

    def test_all_of_titled_branch_round_trips(self) -> None:
        """A titled inline branch keeps its own title as its name."""
        model = to_model(
            Schema.model_validate(
                {"allOf": [{"type": "string"}, {"title": "Short", "maxLength": 3}]}
            )
        )

        assert model.model_json_schema() == snapshot(
            {
                "$defs": {"Short": {"maxLength": 3, "title": "Short"}},
                "allOf": [{"$ref": "#/$defs/Short"}],
                "title": "Model",
                "type": "string",
            }
        )

    def test_all_of_nested_round_trips(self) -> None:
        """An `allOf` producing a nested `allOf` model emits the branches of both."""
        model = to_model(
            Schema.model_validate(
                {"allOf": [{"allOf": [{"type": "string"}, {"maxLength": 3}]}, {"minLength": 2}]}
            )
        )

        assert model.model_json_schema() == snapshot(
            {
                "$defs": {
                    "pydantic_jsonschema__converters___converter__ModelAllOf1__1": {
                        "maxLength": 3,
                        "title": "ModelAllOf1",
                    },
                    "pydantic_jsonschema__converters___converter__ModelAllOf1__2": {
                        "minLength": 2,
                        "title": "ModelAllOf1",
                    },
                },
                "allOf": [
                    {"$ref": "#/$defs/pydantic_jsonschema__converters___converter__ModelAllOf1__1"},
                    {"$ref": "#/$defs/pydantic_jsonschema__converters___converter__ModelAllOf1__2"},
                ],
                "title": "Model",
                "type": "string",
            }
        )

    def test_all_of_repeated_not_round_trips(self) -> None:
        """A `not` beside `allOf` and one in the producing branch are both emitted."""
        model = to_model(
            Schema.model_validate(
                {"allOf": [{"type": "integer", "not": {"const": 1}}], "not": {"const": 2}}
            )
        )

        assert model.model_json_schema() == snapshot(
            {
                "allOf": [
                    {"not": {"const": 1, "type": "integer"}, "title": "Model", "type": "integer"},
                    {"not": {"const": 2, "type": "integer"}},
                ]
            }
        )

    def test_all_of_object_branch_applicators_round_trip(self) -> None:
        """Test the applicators of every object branch are dumped."""
        schema = Schema.model_validate(
            {
                "allOf": [
                    {"type": "object", "propertyNames": {"maxLength": 3}},
                    {"type": "object", "propertyNames": {"minLength": 2}},
                ]
            }
        )

        assert to_model(schema).model_json_schema() == snapshot(
            {
                "allOf": [
                    {
                        "additionalProperties": True,
                        "properties": {},
                        "propertyNames": {"maxLength": 3},
                        "title": "Model",
                        "type": "object",
                    },
                    {"propertyNames": {"minLength": 2}},
                ]
            }
        )
