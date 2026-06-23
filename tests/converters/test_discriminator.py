"""Tests for discriminated `oneOf` unions."""

from typing import TYPE_CHECKING

import pytest
from inline_snapshot import snapshot
from pydantic import ValidationError

from pydantic_jsonschema import (
    to_model,
)
from pydantic_jsonschema.schema import Schema
from tests.conftest import dump_errors

if TYPE_CHECKING:
    from tests.conftest import SchemaRaw

__all__: list[str] = []


class TestDiscriminatedOneOf:
    """`oneOf` branches sharing a const tag map to a Pydantic discriminated union."""

    def test_routes_by_tag(self) -> None:
        """A const-tagged `oneOf` validates each branch by its discriminator value."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "pet": {
                    "oneOf": [
                        {
                            "type": "object",
                            "title": "Cat",
                            "properties": {
                                "type": {"const": "cat"},
                                "meow": {"type": "boolean"},
                            },
                            "required": ["type", "meow"],
                        },
                        {
                            "type": "object",
                            "title": "Dog",
                            "properties": {
                                "type": {"const": "dog"},
                                "bark": {"type": "boolean"},
                            },
                            "required": ["type", "bark"],
                        },
                    ],
                },
            },
            "required": ["pet"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        cat = model(pet={"type": "cat", "meow": True})
        assert cat.model_dump() == snapshot({"pet": {"type": "cat", "meow": True}})

        dog = model(pet={"type": "dog", "bark": False})
        assert dog.model_dump() == snapshot({"pet": {"type": "dog", "bark": False}})

    def test_root_level_discriminated_union(self) -> None:
        """A root `oneOf` of tagged objects becomes a discriminated `RootModel`."""
        schema_raw: SchemaRaw = {
            "oneOf": [
                {
                    "type": "object",
                    "title": "Cat",
                    "properties": {"type": {"const": "cat"}, "meow": {"type": "boolean"}},
                    "required": ["type", "meow"],
                },
                {
                    "type": "object",
                    "title": "Dog",
                    "properties": {"type": {"const": "dog"}, "bark": {"type": "boolean"}},
                    "required": ["type", "bark"],
                },
            ],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        pet = model.model_validate({"type": "cat", "meow": True})
        assert pet.model_dump() == snapshot({"type": "cat", "meow": True})

        assert model.model_json_schema() == snapshot(
            {
                "$defs": {
                    "Cat": {
                        "additionalProperties": True,
                        "properties": {
                            "type": {"const": "cat", "title": "Type", "type": "string"},
                            "meow": {"title": "Meow", "type": "boolean"},
                        },
                        "required": ["type", "meow"],
                        "title": "Cat",
                        "type": "object",
                    },
                    "Dog": {
                        "additionalProperties": True,
                        "properties": {
                            "type": {"const": "dog", "title": "Type", "type": "string"},
                            "bark": {"title": "Bark", "type": "boolean"},
                        },
                        "required": ["type", "bark"],
                        "title": "Dog",
                        "type": "object",
                    },
                },
                "discriminator": {
                    "mapping": {"cat": "#/$defs/Cat", "dog": "#/$defs/Dog"},
                    "propertyName": "type",
                },
                "oneOf": [{"$ref": "#/$defs/Cat"}, {"$ref": "#/$defs/Dog"}],
                "title": "Model",
            }
        )

        with pytest.raises(ValidationError) as exc_info:
            model.model_validate({"type": "fish"})

        assert dump_errors(exc_info.value) == snapshot(
            [
                {
                    "type": "union_tag_invalid",
                    "loc": (),
                    "msg": "Input tag 'fish' found using 'type' does not match any of the expected tags: 'cat', 'dog'",
                    "input": {"type": "fish"},
                }
            ]
        )

    def test_unknown_tag_rejected(self) -> None:
        """A value whose tag matches no branch is rejected as an invalid tag."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "pet": {
                    "oneOf": [
                        {
                            "type": "object",
                            "title": "Cat",
                            "properties": {"type": {"const": "cat"}},
                            "required": ["type"],
                        },
                        {
                            "type": "object",
                            "title": "Dog",
                            "properties": {"type": {"const": "dog"}},
                            "required": ["type"],
                        },
                    ],
                },
            },
            "required": ["pet"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        with pytest.raises(ValidationError) as exc_info:
            model(pet={"type": "fish"})

        assert dump_errors(exc_info.value) == snapshot(
            [
                {
                    "type": "union_tag_invalid",
                    "loc": ("pet",),
                    "msg": "Input tag 'fish' found using 'type' does not match any of the expected tags: 'cat', 'dog'",
                    "input": {"type": "fish"},
                }
            ]
        )

    def test_routing_uses_tag_not_structure(self) -> None:
        """Validation routes by the tag value, then checks that one branch's shape."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "pet": {
                    "oneOf": [
                        {
                            "type": "object",
                            "title": "Cat",
                            "properties": {
                                "type": {"const": "cat"},
                                "meow": {"type": "boolean"},
                            },
                            "required": ["type", "meow"],
                        },
                        {
                            "type": "object",
                            "title": "Dog",
                            "properties": {
                                "type": {"const": "dog"},
                                "bark": {"type": "boolean"},
                            },
                            "required": ["type", "bark"],
                        },
                    ],
                },
            },
            "required": ["pet"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        # Tag says `cat`, so the `cat` branch is checked: its required `meow` is missing.
        # The error is branch-specific (`pet.cat.meow`), not "matches N oneOf branches".
        with pytest.raises(ValidationError) as exc_info:
            model(pet={"type": "cat", "bark": True})

        assert dump_errors(exc_info.value) == snapshot(
            [
                {
                    "type": "missing",
                    "loc": ("pet", "cat", "meow"),
                    "msg": "Field required",
                    "input": {"type": "cat", "bark": True},
                }
            ]
        )

    def test_dump_round_trips_one_of_with_discriminator(self) -> None:
        """A discriminated union dumps back as `oneOf` plus a `discriminator`."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "pet": {
                    "oneOf": [
                        {
                            "type": "object",
                            "title": "Cat",
                            "properties": {"type": {"const": "cat"}},
                            "required": ["type"],
                        },
                        {
                            "type": "object",
                            "title": "Dog",
                            "properties": {"type": {"const": "dog"}},
                            "required": ["type"],
                        },
                    ],
                },
            },
            "required": ["pet"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        assert model.model_json_schema() == snapshot(
            {
                "$defs": {
                    "Cat": {
                        "additionalProperties": True,
                        "properties": {"type": {"const": "cat", "title": "Type", "type": "string"}},
                        "required": ["type"],
                        "title": "Cat",
                        "type": "object",
                    },
                    "Dog": {
                        "additionalProperties": True,
                        "properties": {"type": {"const": "dog", "title": "Type", "type": "string"}},
                        "required": ["type"],
                        "title": "Dog",
                        "type": "object",
                    },
                },
                "additionalProperties": True,
                "properties": {
                    "pet": {
                        "discriminator": {
                            "mapping": {"cat": "#/$defs/Cat", "dog": "#/$defs/Dog"},
                            "propertyName": "type",
                        },
                        "oneOf": [{"$ref": "#/$defs/Cat"}, {"$ref": "#/$defs/Dog"}],
                        "title": "Pet",
                    }
                },
                "required": ["pet"],
                "title": "Model",
                "type": "object",
            }
        )

    def test_from_references(self) -> None:
        """`oneOf` of `$ref` branches with a shared tag becomes discriminated."""
        schema_raw: SchemaRaw = {
            "$defs": {
                "Cat": {
                    "type": "object",
                    "properties": {"kind": {"const": "cat"}},
                    "required": ["kind"],
                },
                "Dog": {
                    "type": "object",
                    "properties": {"kind": {"const": "dog"}},
                    "required": ["kind"],
                },
            },
            "type": "object",
            "properties": {
                "pet": {"oneOf": [{"$ref": "#/$defs/Cat"}, {"$ref": "#/$defs/Dog"}]},
            },
            "required": ["pet"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        assert model(pet={"kind": "dog"}).model_dump() == snapshot({"pet": {"kind": "dog"}})

        with pytest.raises(ValidationError) as exc_info:
            model(pet={"kind": "bird"})

        assert dump_errors(exc_info.value) == snapshot(
            [
                {
                    "type": "union_tag_invalid",
                    "loc": ("pet",),
                    "msg": "Input tag 'bird' found using 'kind' does not match any of the expected tags: 'cat', 'dog'",
                    "input": {"kind": "bird"},
                }
            ]
        )

    def test_single_value_enum_tag(self) -> None:
        """A single-value `enum` acts as a const tag for discrimination."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "shape": {
                    "oneOf": [
                        {
                            "type": "object",
                            "title": "Circle",
                            "properties": {"kind": {"enum": ["circle"]}},
                            "required": ["kind"],
                        },
                        {
                            "type": "object",
                            "title": "Square",
                            "properties": {"kind": {"enum": ["square"]}},
                            "required": ["kind"],
                        },
                    ],
                },
            },
            "required": ["shape"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        assert model(shape={"kind": "circle"}).model_dump() == snapshot(
            {"shape": {"kind": "circle"}}
        )

        with pytest.raises(ValidationError) as exc_info:
            model(shape={"kind": "triangle"})

        assert dump_errors(exc_info.value) == snapshot(
            [
                {
                    "type": "union_tag_invalid",
                    "loc": ("shape",),
                    "msg": "Input tag 'triangle' found using 'kind' does not match any of the expected tags: 'circle', 'square'",
                    "input": {"kind": "triangle"},
                }
            ]
        )

    def test_untagged_branches_fall_back_to_one_of(self) -> None:
        """Without a required const tag, `oneOf` keeps the wrap-validator semantics."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "value": {
                    "oneOf": [
                        {
                            "type": "object",
                            "properties": {"tag": {"const": "a"}, "x": {"type": "integer"}},
                        },
                        {
                            "type": "object",
                            "properties": {"tag": {"const": "b"}, "y": {"type": "integer"}},
                        },
                    ],
                },
            },
            "required": ["value"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        # No tag field: both untagged branches match, so the `OneOf` validator
        # reports the multi-branch match instead of routing by a discriminator.
        with pytest.raises(ValidationError) as exc_info:
            model(value={"x": 1})

        assert dump_errors(exc_info.value) == snapshot(
            [
                {
                    "type": "value_error",
                    "loc": ("value",),
                    "msg": "Value error, Input matches 2 `oneOf` branches, expected exactly 1",
                    "input": {"x": 1},
                }
            ]
        )

    def test_non_distinct_tag_falls_back_to_one_of(self) -> None:
        """A const shared with the same value across branches is not a discriminator."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "value": {
                    "oneOf": [
                        {
                            "type": "object",
                            "properties": {"tag": {"const": "same"}, "x": {"type": "integer"}},
                            "required": ["tag"],
                        },
                        {
                            "type": "object",
                            "properties": {"tag": {"const": "same"}, "y": {"type": "integer"}},
                            "required": ["tag"],
                        },
                    ],
                },
            },
            "required": ["value"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        with pytest.raises(ValidationError) as exc_info:
            model(value={"tag": "same"})

        assert dump_errors(exc_info.value) == snapshot(
            [
                {
                    "type": "value_error",
                    "loc": ("value",),
                    "msg": "Value error, Input matches 2 `oneOf` branches, expected exactly 1",
                    "input": {"tag": "same"},
                }
            ]
        )

    def test_non_scalar_tag_falls_back_to_one_of(self) -> None:
        """A non-scalar const (only `str` / `int` / `bool` / `None` tag) is not a discriminator."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "value": {
                    "oneOf": [
                        {
                            "type": "object",
                            "properties": {"kind": {"const": 1.5}},
                            "required": ["kind"],
                        },
                        {
                            "type": "object",
                            "properties": {"kind": {"const": 2.5}},
                            "required": ["kind"],
                        },
                    ],
                },
            },
            "required": ["value"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema)

        with pytest.raises(ValidationError) as exc_info:
            model(value={"kind": 9.9})

        assert dump_errors(exc_info.value) == snapshot(
            [
                {
                    "type": "value_error",
                    "loc": ("value",),
                    "msg": "Value error, Input matches 0 `oneOf` branches, expected exactly 1",
                    "input": {"kind": 9.9},
                }
            ]
        )
