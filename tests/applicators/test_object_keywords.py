"""Tests for object keywords on a schema that does not convert to an object model."""

import pytest
from inline_snapshot import snapshot
from pydantic import ValidationError

from pydantic_jsonschema import (
    to_model,
)
from pydantic_jsonschema.schema import Schema
from tests.conftest import SchemaRaw, dump_errors

__all__: list[str] = []


class TestObjectKeywords:
    """Tests for `ObjectKeywords` enforcement."""

    @pytest.mark.parametrize(
        ("field_schema", "valid", "invalid"),
        [
            pytest.param(
                {"properties": {"y": {"type": "string"}}},
                {"y": "1"},
                {"y": 1},
                id="untyped-properties",
            ),
            pytest.param(
                {"additionalProperties": {"type": "string"}},
                {"y": "1"},
                {"y": 1},
                id="untyped-additional-properties",
            ),
            pytest.param(
                {"patternProperties": {"^y$": {"type": "string"}}},
                {"y": "1"},
                {"y": 1},
                id="untyped-pattern-properties",
            ),
            pytest.param(
                {"propertyNames": {"maxLength": 1}},
                {"y": 1},
                {"yy": 1},
                id="untyped-property-names",
            ),
            pytest.param(
                {
                    "patternProperties": {"^s_": {"type": "string"}},
                    "additionalProperties": {"type": "integer"},
                },
                {"s_a": "x"},
                {"s_a": 1},
                id="untyped-pattern-and-additional-properties",
            ),
            pytest.param({"minProperties": 1}, {"y": 1}, {}, id="untyped-min-properties"),
            pytest.param(
                {"maxProperties": 1},
                {"y": 1},
                {"y": 1, "z": 2},
                id="untyped-max-properties",
            ),
            pytest.param(
                {"dependentRequired": {"y": ["z"]}},
                {"z": 1},
                {"y": 1},
                id="untyped-dependent-required",
            ),
            pytest.param(
                {"dependentSchemas": {"y": {"required": ["z"]}}},
                {"z": 1},
                {"y": 1},
                id="untyped-dependent-schemas",
            ),
            pytest.param(
                {"type": "object", "patternProperties": {"^y$": {"type": "string"}}},
                {"y": "1"},
                {"y": 1},
                id="typed-pattern-properties",
            ),
            pytest.param(
                {"type": "object", "propertyNames": {"maxLength": 1}},
                {"y": 1},
                {"yy": 1},
                id="typed-property-names",
            ),
            pytest.param(
                {"type": "object", "dependentRequired": {"y": ["z"]}},
                {"z": 1},
                {"y": 1},
                id="typed-dependent-required",
            ),
            pytest.param(
                {"type": "object", "dependentSchemas": {"y": {"required": ["z"]}}},
                {"z": 1},
                {"y": 1},
                id="typed-dependent-schemas",
            ),
        ],
    )
    def test_object_keywords_field(
        self,
        field_schema: SchemaRaw,
        valid: SchemaRaw,
        invalid: SchemaRaw,
    ) -> None:
        """Test a mapping is checked against the object keywords and keeps its value."""
        schema = Schema.model_validate(
            {"type": "object", "properties": {"a": field_schema}, "required": ["a"]}
        )
        model = to_model(schema)

        assert model.model_validate({"a": valid}).model_dump() == {"a": valid}

        with pytest.raises(ValidationError) as exc_info:
            model.model_validate({"a": invalid})

        assert {error["loc"][0] for error in dump_errors(exc_info.value)} == {"a"}

    def test_object_keywords_untyped_root_with_defs(self) -> None:
        """Test an untyped root declaring `$defs` checks its object keywords."""
        schema = Schema.model_validate(
            {
                "$defs": {"N": {"type": "integer"}},
                "properties": {"a": {"$ref": "#/$defs/N"}},
                "required": ["a"],
            }
        )
        model = to_model(schema)

        assert model.model_validate({"a": 1}).model_dump() == snapshot({"a": 1})

        with pytest.raises(ValidationError) as exc_info:
            model.model_validate({"a": "x"})

        assert dump_errors(exc_info.value) == snapshot(
            [
                {
                    "type": "int_parsing",
                    "loc": ("a",),
                    "msg": "Input should be a valid integer, unable to parse string as an integer",
                    "input": "x",
                }
            ]
        )

    def test_object_keywords_union_branch(self) -> None:
        """Test an untyped union branch skips its constraints, as a bare `Any` branch does."""
        schema = Schema.model_validate(
            {
                "type": "object",
                "properties": {
                    "v": {"anyOf": [{"minimum": 0, "required": ["a"]}, {"type": "string"}]}
                },
                "required": ["v"],
            }
        )
        model = to_model(schema)

        assert model.model_validate({"v": "s"}).model_dump() == snapshot({"v": "s"})
        assert model.model_validate({"v": {"a": 1}}).model_dump() == snapshot({"v": {"a": 1}})

        with pytest.raises(ValidationError) as exc_info:
            model.model_validate({"v": {}})

        assert dump_errors(exc_info.value) == snapshot(
            [
                {
                    "type": "value_error",
                    "loc": ("v", "function-wrap[_validate()]"),
                    "msg": "Value error, Object is missing required `a`",
                    "input": {},
                },
                {
                    "type": "string_type",
                    "loc": ("v", "str"),
                    "msg": "Input should be a valid string",
                    "input": {},
                },
            ]
        )

    def test_object_keywords_union_branch_with_applicator(self) -> None:
        """Test an untyped union branch with `not` keeps its constraints, as on a typed one."""
        schema = Schema.model_validate(
            {
                "type": "object",
                "properties": {
                    "v": {
                        "anyOf": [
                            {"minimum": 5, "not": {"const": 7}, "required": ["a"]},
                            {"type": "string"},
                        ]
                    }
                },
                "required": ["v"],
            }
        )
        model = to_model(schema)

        assert model.model_validate({"v": 6}).model_dump() == snapshot({"v": 6})

        with pytest.raises(ValidationError) as exc_info:
            model.model_validate({"v": 3})

        assert [error["type"] for error in dump_errors(exc_info.value)] == snapshot(
            ["greater_than_equal", "string_type"]
        )

    @pytest.mark.parametrize(
        "property_name",
        [
            pytest.param("_id", id="leading-underscore"),
            pytest.param("model_validate", id="model-method"),
            pytest.param("copy", id="shadowed-attribute"),
        ],
    )
    def test_object_keywords_untyped_unusable_field_name(self, property_name: str) -> None:
        """Test an untyped schema naming a property no model field can carry stays `Any`."""
        schema = Schema.model_validate(
            {
                "type": "object",
                "properties": {"a": {"properties": {property_name: {"type": "string"}}}},
                "required": ["a"],
            }
        )
        model = to_model(schema)

        assert model.model_validate({"a": {property_name: 1}}).model_dump() == {
            "a": {property_name: 1}
        }

    def test_object_keywords_untyped_non_object(self) -> None:
        """Test an untyped schema's object keywords pass every non-object value."""
        schema = Schema.model_validate(
            {"type": "object", "properties": {"a": {"required": ["y"]}}, "required": ["a"]}
        )
        model = to_model(schema)

        assert model.model_validate({"a": 5}).model_dump() == snapshot({"a": 5})
        assert model.model_validate({"a": [1]}).model_dump() == snapshot({"a": [1]})

        with pytest.raises(ValidationError) as exc_info:
            model.model_validate({"a": {}})

        assert dump_errors(exc_info.value) == snapshot(
            [
                {
                    "type": "value_error",
                    "loc": ("a",),
                    "msg": "Value error, Object is missing required `y`",
                    "input": {},
                }
            ]
        )

    def test_object_keywords_recursive_def(self) -> None:
        """Test an untyped `$defs` body referencing itself is checked at every depth."""
        schema = Schema.model_validate(
            {
                "$defs": {
                    "Node": {
                        "properties": {
                            "child": {"$ref": "#/$defs/Node"},
                            "value": {"type": "integer"},
                        },
                        "required": ["value"],
                    }
                },
                "type": "object",
                "properties": {"root": {"$ref": "#/$defs/Node"}},
            }
        )
        model = to_model(schema)

        nested = {"root": {"value": 1, "child": {"value": 2}}}
        assert model.model_validate(nested).model_dump() == snapshot(
            {"root": {"value": 1, "child": {"value": 2}}}
        )

        # A second input reuses the adapter the first one built.
        assert model.model_validate({"root": {"value": 3}}).model_dump() == snapshot(
            {"root": {"value": 3}}
        )

        with pytest.raises(ValidationError) as exc_info:
            model.model_validate({"root": {"value": 1, "child": {}}})

        # `root` and `child` are optional, so their annotation is a union with `MISSING`, whose
        #  error list and locations differ between the supported `pydantic` versions.
        missing = [
            error["loc"][-1] for error in dump_errors(exc_info.value) if error["type"] == "missing"
        ]
        assert missing == ["value"]

    def test_object_keywords_recursive_dict_def(self) -> None:
        """Test an untyped `dict`-shaped `$defs` body referencing itself is checked."""
        schema = Schema.model_validate(
            {
                "$defs": {
                    "T": {
                        "propertyNames": {"maxLength": 3},
                        "additionalProperties": {"$ref": "#/$defs/T"},
                    }
                },
                "type": "object",
                "properties": {"t": {"$ref": "#/$defs/T"}},
                "required": ["t"],
            }
        )
        model = to_model(schema)

        nested: SchemaRaw = {"t": {"abc": {"de": {}}}}
        assert model.model_validate(nested).model_dump() == snapshot({"t": {"abc": {"de": {}}}})

        with pytest.raises(ValidationError) as exc_info:
            model.model_validate({"t": {"abc": {"long": {}}}})

        assert dump_errors(exc_info.value) == snapshot(
            [
                {
                    "type": "value_error",
                    "loc": ("t", "abc"),
                    "msg": "Value error, Property name `long` does not satisfy the `propertyNames` schema",
                    "input": {"long": {}},
                }
            ]
        )
