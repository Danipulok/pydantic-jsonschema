"""Tests for core JSON Schema to Pydantic model conversion."""

from typing import Any, Final

import pytest
from inline_snapshot import snapshot
from pydantic import BaseModel, ValidationError

from pydantic_jsonschema import (
    SchemaConverter,
    to_model,
)
from pydantic_jsonschema.applicators import PropertyNames
from pydantic_jsonschema.exceptions import SchemaConversionError, SchemaReferenceError
from pydantic_jsonschema.schema import Schema
from tests.conftest import SchemaRaw, dump_errors

__all__: list[str] = []

_UNDECLARED_USER: Final[Schema] = Schema.model_validate(
    {
        "type": "object",
        "properties": {"user": {"$ref": "#/$defs/User"}},
    }
)


class TestBasicConversion:
    """Tests for basic schema conversion."""

    def test_simple_object_schema(self) -> None:
        """Test converting simple object schema."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
            },
            "required": ["name"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        instance = model(
            name="Alice",
            age=30,
        )
        assert instance.model_dump() == snapshot(
            {
                "name": "Alice",
                "age": 30,
            }
        )

        instance = model(name="Bob")
        assert instance.model_dump() == snapshot({"name": "Bob"})

        with pytest.raises(ValidationError):
            model(age=25)

    def test_array_schema(self) -> None:
        """Test array schema conversion."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": ["tags"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        instance = model(tags=["python", "dev"])
        assert instance.model_dump() == snapshot(
            {
                "tags": ["python", "dev"],
            }
        )

    def test_nested_objects(self) -> None:
        """Test nested object schemas."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "user": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                    },
                    "required": ["name"],
                },
            },
            "required": ["user"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        instance = model(user={"name": "Alice"})
        assert instance.model_dump() == snapshot(
            {
                "user": {"name": "Alice"},
            }
        )

    def test_deeply_nested_objects(self) -> None:
        """Test deeply nested object structures."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "level1": {
                    "type": "object",
                    "properties": {
                        "level2": {
                            "type": "object",
                            "properties": {
                                "value": {"type": "integer"},
                            },
                            "required": ["value"],
                        },
                    },
                    "required": ["level2"],
                },
            },
            "required": ["level1"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        instance = model(level1={"level2": {"value": 42}})
        assert instance.model_dump() == snapshot(
            {
                "level1": {
                    "level2": {
                        "value": 42,
                    },
                },
            }
        )

    def test_schema_without_type(self) -> None:
        """Test schema without type accepts any value."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "anything": {},
            },
            "required": ["anything"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        instance = model(anything="string")
        assert instance.model_dump() == snapshot(
            {
                "anything": "string",
            }
        )

        instance = model(anything=123)
        assert instance.model_dump() == snapshot(
            {
                "anything": 123,
            }
        )

    def test_multiple_type_union(self) -> None:
        """Test schema with multiple types."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "value": {"type": ["string", "integer", "null"]},
            },
            "required": ["value"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        instance = model(value="text")
        assert instance.model_dump() == snapshot({"value": "text"})

        instance = model(value=42)
        assert instance.model_dump() == snapshot({"value": 42})

        instance = model(value=None)
        assert instance.model_dump() == snapshot({"value": None})

    def test_multiple_type_union_with_object(self) -> None:
        """Test multi-type union including `object` still rejects unlisted types."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "value": {"type": ["object", "string"]},
            },
            "required": ["value"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        instance = model(value={"key": 1})
        assert instance.model_dump() == snapshot({"value": {"key": 1}})

        instance = model(value="text")
        assert instance.model_dump() == snapshot({"value": "text"})

        with pytest.raises(ValidationError):
            model(value=42)

    def test_array_without_items_schema(self) -> None:
        """Test array without items schema accepts any element types."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "data": {"type": "array"},
            },
            "required": ["data"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        instance = model(data=[1, "two", 3.0, True, None])
        assert instance.model_dump() == snapshot(
            {
                "data": [1, "two", 3.0, True, None],
            }
        )


class TestObjectApplicators:
    """Tests for the subclass that attaches object applicators to a model."""

    def test_instance_passes_back(self) -> None:
        """Test a model instance is accepted where its model is expected."""
        schema = Schema.model_validate(
            {
                "type": "object",
                "properties": {
                    "p": {
                        "allOf": [{"type": "object", "properties": {"a": {"type": "integer"}}}],
                        "minProperties": 1,
                    },
                },
            }
        )
        model = to_model(schema)
        instance = model.model_validate({"p": {"a": 1}})

        assert model.model_validate(instance).model_dump() == {"p": {"a": 1}}
        assert model.model_validate({"p": vars(instance)["p"]}).model_dump() == {"p": {"a": 1}}

    @pytest.mark.parametrize(
        ("schema_raw", "value"),
        [
            pytest.param(
                {"type": "object", "properties": {"p": {"$ref": "#/$defs/P"}}},
                {"p": {"a": 1}},
                id="property",
            ),
            pytest.param(
                {"type": "array", "items": {"$ref": "#/$defs/P"}},
                [{"a": 1}],
                id="item",
            ),
        ],
    )
    def test_nested_applicator_runs_once(
        self,
        monkeypatch: pytest.MonkeyPatch,
        *,
        schema_raw: SchemaRaw,
        value: Any,  # noqa: ANN401
    ) -> None:
        """Test the applicator of a model used as a nested type runs once per value."""
        inputs: list[Any] = []
        validate = PropertyNames.validate

        def record(self: PropertyNames, data: Any, /) -> Any:  # noqa: ANN401
            inputs.append(data)
            return validate(self, data)

        monkeypatch.setattr(PropertyNames, "validate", record)
        schema = Schema.model_validate(
            {
                **schema_raw,
                "$defs": {
                    "P": {
                        "type": "object",
                        "properties": {"a": {"type": "integer"}},
                        "propertyNames": {"maxLength": 1},
                    },
                },
            }
        )
        model = to_model(schema)

        model.model_validate(value)

        assert inputs == [{"a": 1}]

    def test_recursive_applicator_checks_every_level(self) -> None:
        """Test the applicator of a recursive model checks the value one level down."""
        schema = Schema.model_validate(
            {
                "type": "object",
                "properties": {"n": {"$ref": "#/$defs/N"}},
                "required": ["n"],
                "$defs": {
                    "N": {
                        "type": "object",
                        "properties": {"c": {"type": "array", "items": {"$ref": "#/$defs/N"}}},
                        "required": ["c"],
                        "propertyNames": {"maxLength": 1},
                    },
                },
            }
        )
        model = to_model(schema)

        valid: dict[str, Any] = {"n": {"c": [{"c": []}]}}
        assert model.model_validate(valid).model_dump() == valid

        with pytest.raises(ValidationError) as exc_info:
            model.model_validate({"n": {"c": [{"c": [], "bb": 0}]}})

        assert dump_errors(exc_info.value) == [
            {
                "type": "value_error",
                "loc": ("n", "c", 0),
                "msg": (
                    "Value error, Property name `bb` does not satisfy the `propertyNames` schema"
                ),
                "input": {"c": [], "bb": 0},
            }
        ]

    @pytest.mark.parametrize(
        "assertion",
        [
            pytest.param({"not": {"type": "object", "minProperties": 3}}, id="not"),
            pytest.param({"if": {"const": 1}, "then": {"const": 2}}, id="if"),
        ],
    )
    def test_root_assertion_keeps_object_applicators(self, assertion: SchemaRaw) -> None:
        """Test a root `not` / `if` keeps the object applicators of the model it wraps."""
        schema = Schema.model_validate(
            {
                "type": "object",
                "properties": {"a": {}},
                "propertyNames": {"maxLength": 1},
                **assertion,
            }
        )
        model = to_model(schema)

        assert model.model_validate({"a": 1}).model_dump() == {"a": 1}

        with pytest.raises(ValidationError) as exc_info:
            model.model_validate({"a": 1, "Toolong": 1})

        assert dump_errors(exc_info.value) == [
            {
                "type": "value_error",
                "loc": (),
                "msg": (
                    "Value error, Property name `Toolong` does not satisfy"
                    " the `propertyNames` schema"
                ),
                "input": {"a": 1, "Toolong": 1},
            }
        ]


class TestPropertyNames:
    """Tests for properties whose name Pydantic refuses as a field name."""

    @pytest.mark.parametrize(
        "property_name",
        [
            pytest.param("_id", id="leading-underscore"),
            pytest.param("__x", id="double-underscore"),
            pytest.param("_", id="underscore-only"),
            pytest.param("model_validate", id="model-method"),
            pytest.param("model_config", id="model-config"),
        ],
    )
    def test_renamed_property_round_trips(self, property_name: str) -> None:
        """Test a refused name validates, dumps and documents under the property name."""
        schema = Schema.model_validate(
            {
                "type": "object",
                "properties": {property_name: {"type": "string"}},
                "required": [property_name],
            }
        )
        model = to_model(schema)

        assert model.model_validate({property_name: "v"}).model_dump() == {property_name: "v"}
        assert list(model.model_json_schema()["properties"]) == [property_name]

        with pytest.raises(ValidationError) as exc_info:
            model.model_validate({})

        assert [error["type"] for error in dump_errors(exc_info.value)] == ["missing"]

    def test_shadowing_property_keeps_its_name(self) -> None:
        """Test a `BaseModel` attribute outside `model_` stays the field name, as before."""
        schema = Schema.model_validate(
            {"type": "object", "properties": {"copy": {"type": "string"}}}
        )

        with pytest.warns(UserWarning, match='Field name "copy"'):
            model = to_model(schema)

        assert list(model.model_fields) == ["copy"]

    def test_renamed_field_avoids_a_declared_name(self) -> None:
        """Test `_id` beside `id_` keeps both properties."""
        schema = Schema.model_validate(
            {
                "type": "object",
                "properties": {"_id": {"type": "string"}, "id_": {"type": "integer"}},
            }
        )
        model = to_model(schema)

        assert model.model_validate({"_id": "a", "id_": 1}).model_dump() == snapshot(
            {"_id": "a", "id_": 1}
        )
        assert {name: field.alias for name, field in model.model_fields.items()} == snapshot(
            {"id__": "_id", "id_": None}
        )

    def test_renamed_field_beside_a_plain_name_in_another_branch(self) -> None:
        """Test `_id` in one `allOf` branch and `id` in another keep both values."""
        schema = Schema.model_validate(
            {
                "allOf": [
                    {"type": "object", "properties": {"_id": {"type": "string"}}},
                    {"type": "object", "properties": {"id": {"type": "integer"}}},
                ]
            }
        )
        model = to_model(schema)

        assert model.model_validate({"_id": "a", "id": 1}).model_dump() == snapshot(
            {"_id": "a", "id": 1}
        )

    def test_renamed_property_overrides_its_all_of_base(self) -> None:
        """Test a property beside `allOf` replaces the base field of the same refused name."""
        schema = Schema.model_validate(
            {
                "allOf": [{"type": "object", "properties": {"_id": {"type": "string"}}}],
                "type": "object",
                "properties": {"_id": {"type": "string", "minLength": 2}},
                "required": ["_id"],
            }
        )
        model = to_model(schema)

        assert model.model_validate({"_id": "ab"}).model_dump() == snapshot({"_id": "ab"})
        assert {name: field.alias for name, field in model.model_fields.items()} == snapshot(
            {"id_": "_id"}
        )

        with pytest.raises(ValidationError) as exc_info:
            model.model_validate({"_id": "a"})

        assert [error["type"] for error in dump_errors(exc_info.value)] == ["string_too_short"]

    @pytest.mark.parametrize(
        ("property_name", "field_name"),
        [
            pytest.param("_id", "id_", id="leading-underscore"),
            pytest.param("__x", "x_", id="double-underscore"),
            pytest.param("_", "field_", id="underscore-only"),
            pytest.param("model_validate", "model_validate_", id="model-method"),
            pytest.param("model_name", "model_name", id="model-prefix-not-a-member"),
        ],
    )
    def test_field_name_of_a_property(
        self,
        property_name: str,
        field_name: str,
    ) -> None:
        """Test which field name a property gets."""
        schema = Schema.model_validate(
            {"type": "object", "properties": {property_name: {"type": "string"}}}
        )
        model = to_model(schema)

        assert list(model.model_fields) == [field_name]

    def test_renamed_fields_of_two_properties_stay_apart(self) -> None:
        """Test `_id` and `__id` get two fields, both checked."""
        schema = Schema.model_validate(
            {
                "type": "object",
                "properties": {"_id": {"type": "string"}, "__id": {"type": "integer"}},
                "required": ["_id", "__id"],
            }
        )
        model = to_model(schema)

        assert {name: field.alias for name, field in model.model_fields.items()} == snapshot(
            {"id_": "_id", "id__": "__id"}
        )

        with pytest.raises(ValidationError) as exc_info:
            model.model_validate({"_id": 1, "__id": 1})

        assert [error["type"] for error in dump_errors(exc_info.value)] == ["string_type"]

    def test_renamed_ref_property_validates_under_its_name(self) -> None:
        """Test a `$ref` property with a refused name validates under the property name."""
        schema = Schema.model_validate(
            {
                "$defs": {"S": {"type": "string"}},
                "type": "object",
                "properties": {"_id": {"$ref": "#/$defs/S"}},
                "required": ["_id"],
            }
        )
        model = to_model(schema)

        assert model.model_validate({"_id": "ab"}).model_dump() == snapshot({"_id": "ab"})

    def test_renamed_property_avoids_a_base_field(self) -> None:
        """Test an own `_id` beside an `allOf` base declaring `id_` keeps the base field."""
        schema = Schema.model_validate(
            {
                "allOf": [
                    {
                        "type": "object",
                        "properties": {"id_": {"type": "integer"}},
                        "required": ["id_"],
                    }
                ],
                "type": "object",
                "properties": {"_id": {"type": "string"}},
                "required": ["_id"],
            }
        )
        model = to_model(schema)

        assert {name: field.alias for name, field in model.model_fields.items()} == snapshot(
            {"id_": None, "id__": "_id"}
        )

        with pytest.raises(ValidationError) as exc_info:
            model.model_validate({"_id": "a", "id_": "x"})

        assert [error["type"] for error in dump_errors(exc_info.value)] == ["int_parsing"]

    def test_property_named_like_a_renamed_base_field(self) -> None:
        """Test an own `id_` beside a base `_id`, whose field is `id_`, keeps the base default."""
        schema = Schema.model_validate(
            {
                "allOf": [
                    {
                        "type": "object",
                        "properties": {"_id": {"type": "string", "default": "d"}},
                    }
                ],
                "type": "object",
                "properties": {"id_": {"type": "integer"}},
            }
        )
        model = to_model(schema)

        assert model.model_validate({"id_": 1}).model_dump() == snapshot({"_id": "d", "id_": 1})

    def test_renamed_property_beside_its_base_and_a_like_named_property(self) -> None:
        """Test an own `_id` overriding a base `_id` keeps its own constraint beside `id_`."""
        schema = Schema.model_validate(
            {
                "allOf": [
                    {
                        "type": "object",
                        "properties": {"_id": {"type": "string"}},
                        "required": ["_id"],
                    }
                ],
                "type": "object",
                "properties": {
                    "_id": {"type": "string", "minLength": 2},
                    "id_": {"type": "integer"},
                },
                "required": ["_id", "id_"],
            }
        )
        model = to_model(schema)

        with pytest.raises(ValidationError) as exc_info:
            model.model_validate({"_id": "a", "id_": 1})

        assert [error["type"] for error in dump_errors(exc_info.value)] == ["string_too_short"]

    @pytest.mark.parametrize(
        "branches",
        [
            pytest.param(
                [
                    {"type": "object", "properties": {"_id": {"type": "string"}}},
                    {
                        "type": "object",
                        "properties": {"id_": {"type": "integer"}},
                        "additionalProperties": False,
                    },
                ],
                id="renamed-first",
            ),
            pytest.param(
                [
                    {"type": "object", "properties": {"id_": {"type": "integer"}}},
                    {"type": "object", "properties": {"_id": {"type": "string"}}},
                ],
                id="renamed-second",
            ),
        ],
    )
    def test_renamed_field_meets_a_property_of_another_branch(
        self,
        branches: list[SchemaRaw],
    ) -> None:
        """Test `_id` and `id_` in two `allOf` branches fail, since they would share one field."""
        schema = Schema.model_validate({"allOf": branches})

        with pytest.raises(SchemaConversionError) as exc_info:
            to_model(schema)

        assert "`id_`" in str(exc_info.value)

    def test_renamed_field_meets_a_property_of_another_ref_branch(self) -> None:
        """Test `_id` and `id_` in two `$ref` branches beside an inline branch fail too."""
        schema = Schema.model_validate(
            {
                "$defs": {
                    "A": {"type": "object", "properties": {"_id": {"type": "string"}}},
                    "B": {"type": "object", "properties": {"id_": {"type": "integer"}}},
                },
                "allOf": [
                    {"$ref": "#/$defs/A"},
                    {"$ref": "#/$defs/B"},
                    {"type": "object", "properties": {"x": {}}},
                ],
            }
        )

        with pytest.raises(SchemaConversionError) as exc_info:
            to_model(schema)

        assert "`id_`" in str(exc_info.value)

    def test_renamed_property_skips_every_taken_name(self) -> None:
        """Test `_id` beside `id_` and `id__` takes `id___`, keeping its own `type`."""
        schema = Schema.model_validate(
            {
                "type": "object",
                "properties": {
                    "_id": {"type": "string"},
                    "id_": {"type": "integer"},
                    "id__": {"type": "boolean"},
                },
                "required": ["_id", "id_", "id__"],
            }
        )
        model = to_model(schema)

        assert {name: field.alias for name, field in model.model_fields.items()} == snapshot(
            {"id___": "_id", "id_": None, "id__": None}
        )

        with pytest.raises(ValidationError) as exc_info:
            model.model_validate({"_id": 1, "id_": 1, "id__": True})

        assert [error["type"] for error in dump_errors(exc_info.value)] == ["string_type"]

    def test_renamed_property_replaces_a_required_base_field(self) -> None:
        """Test an own `_id` beside an `allOf` base `_id` keeps the base `type` and `required`."""
        schema = Schema.model_validate(
            {
                "allOf": [
                    {
                        "type": "object",
                        "properties": {"_id": {"type": "string"}},
                        "required": ["_id"],
                    }
                ],
                "type": "object",
                "properties": {"_id": {"minLength": 2}},
            }
        )
        model = to_model(schema)

        assert model.model_validate({"_id": "ab"}).model_dump() == snapshot({"_id": "ab"})

        for document in ({}, {"_id": 55}):
            with pytest.raises(ValidationError):
                model.model_validate(document)


class TestRootModels:
    """Tests for `RootModel` creation from non-object root schemas."""

    def test_root_model_for_array_type(self) -> None:
        """Test RootModel creation for array type schemas."""
        schema_raw: SchemaRaw = {
            "type": "array",
            "items": {"type": "string"},
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        instance = model(["item1", "item2", "item3"])  # type: ignore[call-arg]
        assert instance.model_dump() == snapshot(["item1", "item2", "item3"])

    def test_root_model_for_string_type(self) -> None:
        """Test RootModel creation for string type schemas."""
        schema_raw: SchemaRaw = {
            "type": "string",
            "minLength": 5,
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        instance = model("hello world")  # type: ignore[call-arg]
        assert instance.model_dump() == snapshot("hello world")

        with pytest.raises(ValidationError):
            model("hi")  # type: ignore[call-arg]

        # Root value has no "absent" concept -> required.
        with pytest.raises(ValidationError):
            model()

    def test_root_model_for_integer_type(self) -> None:
        """Test RootModel creation for integer type schemas."""
        schema_raw: SchemaRaw = {
            "type": "integer",
            "minimum": 0,
            "maximum": 100,
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        valid_value: int = 42
        instance = model(valid_value)  # type: ignore[call-arg]
        assert instance.model_dump() == valid_value  # type: ignore[comparison-overlap]

        invalid_value: int = -1
        with pytest.raises(ValidationError):
            model(invalid_value)  # type: ignore[call-arg]

        invalid_value = 101
        with pytest.raises(ValidationError):
            model(invalid_value)  # type: ignore[call-arg]

    def test_root_model_with_allof(self) -> None:
        """Test RootModel with allOf."""
        schema_raw: SchemaRaw = {
            "allOf": [
                {"type": "string", "minLength": 5},
            ],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        instance = model("hello world")  # type: ignore[call-arg]
        assert instance.model_dump() == snapshot("hello world")

    def test_root_additional_properties_typed_validation(self) -> None:
        """Test root object with schema-valued `additionalProperties` validates value types."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "additionalProperties": {"type": "integer"},
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        instance = model({"count": 42, "total": 100})  # type: ignore[call-arg]
        assert instance.model_dump() == snapshot(
            {
                "count": 42,
                "total": 100,
            }
        )

        with pytest.raises(ValidationError):
            model({"count": "not-an-integer"})  # type: ignore[call-arg]

    def test_root_additional_properties_with_ref(self) -> None:
        """Test root object with `$ref`-valued `additionalProperties`."""
        schema_raw: SchemaRaw = {
            "$defs": {
                "Item": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                    },
                    "required": ["name"],
                },
            },
            "type": "object",
            "additionalProperties": {"$ref": "#/$defs/Item"},
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        instance = model({"first": {"name": "A"}, "second": {"name": "B"}})  # type: ignore[call-arg]
        assert instance.model_dump() == snapshot(
            {
                "first": {"name": "A"},
                "second": {"name": "B"},
            }
        )

        with pytest.raises(ValidationError):
            model({"first": "not-an-item"})  # type: ignore[call-arg]


class TestLiteralTypes:
    """Tests for `enum` / `const` conversion to `Literal`."""

    @pytest.mark.parametrize(
        ("schema_field", "valid_value", "invalid_value"),
        [
            pytest.param(
                {"enum": ["active", "inactive", "pending"]},
                "active",
                "invalid",
                id="enum",
            ),
            pytest.param(
                {"const": "fixed_value"},
                "fixed_value",
                "wrong_value",
                id="const",
            ),
            pytest.param(
                {"const": None},
                None,
                "not-null",
                id="const-null",
            ),
        ],
    )
    def test_literal_types(
        self,
        schema_field: dict[str, Any],
        valid_value: str | None,
        invalid_value: str,
    ) -> None:
        """Test enum and const conversion to Literal."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {"field": schema_field},
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        instance = model(field=valid_value)
        assert instance.model_dump() == {"field": valid_value}

        with pytest.raises(ValidationError):
            model(field=invalid_value)

    def test_empty_enum_raises_conversion_error(self) -> None:
        """An empty `enum` raises a clean `SchemaConversionError`, not a bare `AssertionError`."""
        with pytest.raises(SchemaConversionError) as exc_info:
            to_model(Schema.model_validate({"enum": []}))
        assert str(exc_info.value) == snapshot(
            "SchemaConversionError(message='`enum` must contain at least one value')"
        )


class TestAdditionalProperties:
    """Tests for `additionalProperties` handling."""

    def test_dict_with_additional_properties_schema(self) -> None:
        """Test dict with typed additionalProperties."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "metadata": {"type": "object", "additionalProperties": {"type": "integer"}},
            },
            "required": ["metadata"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        instance = model(metadata={"count": 42, "total": 100})
        assert instance.model_dump() == snapshot(
            {
                "metadata": {"count": 42, "total": 100},
            }
        )

    def test_dict_with_false_additional_properties(self) -> None:
        """Test object creation with additionalProperties: false."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "data": {"type": "object", "additionalProperties": False},
            },
            "required": ["data"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        instance = model(data={})
        assert instance.model_dump() == snapshot({"data": {}})

        with pytest.raises(ValidationError):
            model(data={"extra": "field"})

    def test_additional_properties_true(self) -> None:
        """Test additionalProperties: true allows any values."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "data": {
                    "type": "object",
                    "additionalProperties": True,
                },
            },
            "required": ["data"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        instance = model(data={"a": 1, "b": "text", "c": [1, 2, 3]})
        assert instance.model_dump() == snapshot(
            {
                "data": {"a": 1, "b": "text", "c": [1, 2, 3]},
            }
        )

    def test_additional_properties_forbid(self) -> None:
        """Test that additionalProperties: false forbids extra fields."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "additionalProperties": False,
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        instance = model(name="Alice")
        assert instance.model_dump() == snapshot({"name": "Alice"})

        with pytest.raises(ValidationError):
            model(
                name="Alice",
                extra="field",
            )

    def test_additional_properties_allow(self) -> None:
        """Test that additionalProperties allows extra fields."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "additionalProperties": True,
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        instance = model(
            name="Alice",
            extra="allowed",
        )
        assert instance.model_dump() == snapshot(
            {
                "name": "Alice",
                "extra": "allowed",
            }
        )

    def test_additional_properties_with_schema(self) -> None:
        """Test additionalProperties with schema definition."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
            },
            "required": ["name"],
            "additionalProperties": {
                "type": "integer",
            },
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        instance = model(
            name="test",
            extra1=10,
            extra2=20,
        )
        assert instance.model_dump() == snapshot(
            {
                "name": "test",
                "extra1": 10,
                "extra2": 20,
            }
        )

    def test_property_names_pattern(self) -> None:
        """Test propertyNames with pattern."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "propertyNames": {
                "pattern": "^[a-z_]+$",
            },
            "additionalProperties": {"type": "string"},
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        instance = model({"valid_name": "test", "another_name": "value"})  # type: ignore[call-arg]
        assert instance.model_dump() == snapshot(
            {
                "valid_name": "test",
                "another_name": "value",
            }
        )


def _user_document(user_type: str) -> Schema:
    return Schema.model_validate(
        {
            "type": "object",
            "$defs": {"User": {"type": user_type}},
            "properties": {
                "holder": {
                    "type": "object",
                    "properties": {"user": {"$ref": "#/$defs/User"}},
                },
            },
        }
    )


def _recursive_document(value_type: str) -> Schema:
    # `next` refers to `Node` while it is built, so its `oneOf` branch is bound after conversion.
    return Schema.model_validate(
        {
            "$defs": {
                "Node": {
                    "type": "object",
                    "properties": {
                        "value": {"type": value_type},
                        "next": {"oneOf": [{"$ref": "#/$defs/Node"}, {"type": "null"}]},
                    },
                },
            },
            "$ref": "#/$defs/Node",
        }
    )


class TestConverterPerDocument:
    """Tests that a reused converter keeps nothing of an earlier document."""

    def test_earlier_def_does_not_resolve(self) -> None:
        """Test that a `$ref` to a def only an earlier document declared raises."""
        converter = SchemaConverter()
        converter.convert_schema(_user_document("string"))

        with pytest.raises(SchemaReferenceError):
            converter.convert_schema(_UNDECLARED_USER)

    def test_earlier_def_does_not_resolve_after_a_failed_conversion(self) -> None:
        """Test that a conversion that raised leaves no def for the next one."""
        converter = SchemaConverter()
        failing = Schema.model_validate(
            {
                "type": "object",
                "$defs": {"User": {"type": "string"}},
                "properties": {"user": {"$ref": "#/$defs/Missing"}},
            }
        )

        with pytest.raises(SchemaReferenceError):
            converter.convert_schema(failing)

        with pytest.raises(SchemaReferenceError):
            converter.convert_schema(_UNDECLARED_USER)

    def test_nested_model_follows_its_own_document(self) -> None:
        """Test that an inline object equal to an earlier one resolves its `$ref` anew."""
        converter = SchemaConverter()
        converter.convert_schema(_user_document("string"))

        model = converter.convert_schema(_user_document("integer"))

        assert model.model_validate({"holder": {"user": 1}}).model_dump() == snapshot(
            {"holder": {"user": 1}}
        )

    def test_earlier_model_keeps_its_forward_refs(self) -> None:
        """Test that a later conversion does not rebind the branches of an earlier model."""
        converter = SchemaConverter()
        model = converter.convert_schema(_recursive_document("string"))
        converter.convert_schema(_recursive_document("integer"))

        node = {"value": "a", "next": {"value": "b", "next": None}}

        assert model.model_validate(node).model_dump() == snapshot(
            {"value": "a", "next": {"value": "b", "next": None}}
        )

    def test_second_conversion_takes_its_own_model_name(self) -> None:
        """Test that a reused converter names the model of each call after that call."""
        schema = Schema.model_validate(
            {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                },
            }
        )
        converter = SchemaConverter()
        first = converter.convert_schema(schema, model_name="First")

        model = converter.convert_schema(schema, model_name="Second")

        assert model is not first
        assert model.__name__ == "Second"


class TestConverterCaching:
    """Tests for model caching in converter."""

    def test_different_schemas_return_different_models(self) -> None:
        """Test that two inline objects of one document get a model each."""
        schema = Schema.model_validate(
            {
                "type": "object",
                "properties": {
                    "person": {"type": "object", "properties": {"name": {"type": "string"}}},
                    "pet": {"type": "object", "properties": {"age": {"type": "integer"}}},
                },
                "required": ["person", "pet"],
            }
        )
        model = SchemaConverter().convert_schema(schema)

        assert model.model_fields["person"].annotation is not model.model_fields["pet"].annotation

    def test_ref_model_cached_in_get_model(self) -> None:
        """Test that `_get_model` properly caches resolved reference models."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "$defs": {
                "User": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "age": {"type": "integer"},
                    },
                    "required": ["name"],
                },
            },
            "properties": {
                "user1": {"$ref": "#/$defs/User"},
                "user2": {"$ref": "#/$defs/User"},
            },
            "required": ["user1", "user2"],
        }

        converter = SchemaConverter()
        schema = Schema.model_validate(schema_raw)
        model = converter.convert_schema(schema)

        # `required` keeps the bare model annotation: both fields share the `$ref`
        #  cache, so the annotation is the same model object. Optional fields would
        #  wrap it as `User | MISSING`, whose identity is not stable across Python
        #  versions (`X | Y` is no longer interned on 3.15+), making `is` fail there.
        assert model.model_fields["user1"].annotation is model.model_fields["user2"].annotation

    def test_model_generation_with_uncached_ref(self) -> None:
        """Test model generation fallback when ref exists but model not yet cached.

        This tests the fallback path in _get_model through a controlled scenario
        using a custom converter subclass that simulates the uncached state.
        """

        class TestableConverter(SchemaConverter):
            """Converter that allows testing of model generation fallback."""

            def trigger_uncached_ref_scenario(self) -> type[BaseModel]:
                """Simulate scenario where ref exists in defs_cache but model not cached."""
                test_schema = Schema(
                    type="object",
                    properties={"value": Schema(type="string")},
                )
                ref: str = "#/$defs/TestType"
                # A def is registered with the name that declares its schema; its nodes are
                #  addressed by that name, so both halves are filled together.
                self._defs_cache[ref] = test_schema
                self._def_names[ref] = "TestType"

                return self._get_model(ref)

        converter = TestableConverter()
        model = converter.trigger_uncached_ref_scenario()

        instance = model(value="test")
        assert instance.model_dump() == snapshot({"value": "test"})
