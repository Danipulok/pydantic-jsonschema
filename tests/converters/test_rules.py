"""Tests for the `rules` parameter: per-node loading via matchers and actions."""

from typing import TYPE_CHECKING, Annotated, Any, Final

import pytest
from inline_snapshot import snapshot
from pydantic import AfterValidator, ValidationError

from pydantic_jsonschema import formats, to_model
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

# Mirrors `ByType.target`: any type or typing form a rule can be aimed at.
type ByTypeTargetType = Any

# The value of whatever field a rule happens to wrap, whichever format it carries.
type FieldValueType = Any

# User-declared aliases: `ByType` must resolve them to what they name, at any nesting depth.
type Tags = list[str]
type Timestamps = Tags

# Every type exported from `pydantic_jsonschema.formats`, with the JSON Schema `format` keyword it
# serves and a value that satisfies it. `test_every_exported_format_type_is_covered` keeps it whole.
_FORMAT_CASES: Final[list[tuple[str, ByTypeTargetType, str]]] = [
    ("date-time", formats.DateTime, "2024-01-15T10:30:00Z"),
    ("time", formats.Time, "10:30:00"),
    ("date", formats.Date, "2024-01-15"),
    ("duration", formats.Duration, "P1D"),
    ("email", formats.Email, "user@example.com"),
    ("idn-email", formats.IdnEmail, "user@example.com"),
    ("hostname", formats.Hostname, "example.com"),
    ("idn-hostname", formats.IdnHostname, "example.com"),
    ("uuid", formats.UUID, "00000000-0000-7000-8000-000000000000"),
    ("regex", formats.Regex, "^a+$"),
    ("ipv4", formats.IPv4, "192.0.2.1"),
    ("ipv6", formats.IPv6, "2001:db8::1"),
    ("uri", formats.Uri, "https://example.com"),
    ("uri-reference", formats.UriReference, "/path"),
    ("iri", formats.Iri, "https://example.com"),
    ("iri-reference", formats.IriReference, "/path"),
    ("uri-template", formats.UriTemplate, "https://example.com/{id}"),
    ("json-pointer", formats.JsonPointer, "/a/b"),
    ("relative-json-pointer", formats.RelativeJsonPointer, "1/a"),
]

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


def exclaim(value: str) -> str:
    """Append an exclamation mark, marking that a rule ran after the format substitution."""
    return f"{value}!"


def reverse_items[ItemType](value: list[ItemType]) -> list[ItemType]:
    """Reverse a list, marking which arrays a `ByType` target reached."""
    return list(reversed(value))


def sorted_keys[ValueType](value: dict[str, ValueType]) -> dict[str, ValueType]:
    """Sort a map by key, marking that a `ByType` target reached the map itself."""
    return dict(sorted(value.items()))


def annotation_is_str(context: MatchContext, /) -> bool:
    """Predicate: match when the resolved annotation is exactly `str`."""
    return context.annotation is str


class TestBefore:
    """`Before` -> `BeforeValidator`: coerce raw input before core parsing."""

    def test_csv_string_to_list(self) -> None:
        """A comma-separated string is split into a list before list parsing."""
        schema = Schema.model_validate(_TAGS_SCHEMA)
        model = to_model(
            schema,
            rules=[
                Rule(ByType(list[str]), Before(csv_to_list)),
            ],
        )

        instance = model(tags="a,b,c", created="x")
        assert instance.model_dump() == snapshot({"tags": ["a", "b", "c"], "created": "x"})

    def test_list_input_passes_through(self) -> None:
        """A list input is left unchanged (the coercion is idempotent)."""
        schema = Schema.model_validate(_TAGS_SCHEMA)
        model = to_model(
            schema,
            rules=[
                Rule(ByType(list[str]), Before(csv_to_list)),
            ],
        )

        instance = model(tags=["a", "b"], created="x")
        assert instance.model_dump() == snapshot({"tags": ["a", "b"], "created": "x"})


class TestAfter:
    """`After` -> `AfterValidator`: normalize / validate the parsed value."""

    def test_normalizes_value(self) -> None:
        """The parsed string is normalized after core parsing."""
        schema = Schema.model_validate(_TAGS_SCHEMA)
        model = to_model(
            schema,
            rules=[
                Rule(ByPath("/properties/created"), After(strip_upper)),
            ],
        )

        instance = model(tags=[], created="  hi  ")
        assert instance.model_dump() == snapshot({"tags": [], "created": "HI"})

    def test_rejects_invalid_value(self) -> None:
        """An `After` validator that raises surfaces as a `ValidationError`."""
        schema = Schema.model_validate(_TAGS_SCHEMA)
        model = to_model(
            schema,
            rules=[
                Rule(ByType(list[str]), After(reject_empty)),
            ],
        )

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
        model = to_model(
            schema,
            rules=[
                Rule(ByType(list[str]), Override(csv_to_list)),
            ],
        )

        instance = model(tags="a,b", created="x")
        assert instance.model_dump() == snapshot({"tags": ["a", "b"], "created": "x"})


class TestDump:
    """`Dump` -> `PlainSerializer`: transform the value on serialization."""

    def test_serializes_value(self) -> None:
        """The list is joined into a string on `model_dump`."""
        schema = Schema.model_validate(_TAGS_SCHEMA)
        model = to_model(
            schema,
            rules=[
                Rule(ByType(list[str]), Dump(",".join)),
            ],
        )

        instance = model(tags=["x", "y"], created="z")
        assert instance.model_dump() == snapshot({"tags": "x,y", "created": "z"})


class TestMatchers:
    """Matcher selection: `ByType`, `ByPath`, `ByFunc`."""

    def test_by_type_no_match_leaves_field_untouched(self) -> None:
        """A `ByType` mismatch does not wrap the field, so raw input fails validation."""
        schema = Schema.model_validate(_TAGS_SCHEMA)
        model = to_model(
            schema,
            rules=[
                Rule(ByType(list[int]), Before(csv_to_list)),
            ],
        )

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
        model = to_model(
            schema,
            rules=[
                Rule(ByPath("/properties/created"), After(strip_upper)),
            ],
        )

        instance = model(tags=[], created="hi")
        assert instance.model_dump() == snapshot({"tags": [], "created": "HI"})

    def test_by_func_predicate(self) -> None:
        """`ByFunc` matches every node whose predicate returns `True`."""
        schema = Schema.model_validate(_TAGS_SCHEMA)
        model = to_model(
            schema,
            rules=[
                Rule(ByFunc(annotation_is_str), After(strip_upper)),
            ],
        )

        instance = model(tags=[], created="  hi ")
        assert instance.model_dump() == snapshot({"tags": [], "created": "HI"})


class TestByTypeParameterization:
    """`ByType` compares annotations exactly, except that a bare generic covers every parameter.

    The converter never produces an unparameterized annotation — an array is `list[str]` or
    `list[Any]`, a typed map is `dict[str, T]` — so a bare target that compared by equality would
    match nothing at all.
    """

    @pytest.mark.parametrize(
        ("target", "expected"),
        [
            (list, {"names": ["B", "A"], "counts": [2, 1], "loose": [False, True]}),
            (list[str], {"names": ["B", "A"], "counts": [1, 2], "loose": [True, False]}),
            (list[int], {"names": ["A", "B"], "counts": [2, 1], "loose": [True, False]}),
            (list[Any], {"names": ["A", "B"], "counts": [1, 2], "loose": [False, True]}),
        ],
        ids=["bare", "of-str", "of-int", "of-any"],
    )
    def test_bare_generic_covers_every_parameterization(
        self,
        target: ByTypeTargetType,
        expected: dict[str, Any],
    ) -> None:
        """A bare `list` matches all three arrays; a parameterized target matches only its own."""
        schema = Schema.model_validate(
            {
                "type": "object",
                "properties": {
                    "names": {"type": "array", "items": {"type": "string"}},
                    "counts": {"type": "array", "items": {"type": "integer"}},
                    "loose": {"type": "array"},
                },
                "required": ["names", "counts", "loose"],
            }
        )
        model = to_model(
            schema,
            rules=[
                Rule(ByType(target), After(reverse_items)),
            ],
        )

        instance = model(names=["A", "B"], counts=[1, 2], loose=[True, False])
        assert instance.model_dump() == expected

    def test_bare_dict_matches_a_typed_map(self) -> None:
        """The same holds for a map: the converter emits `dict[str, T]`, never a bare `dict`."""
        schema = Schema.model_validate(
            {
                "type": "object",
                "properties": {
                    "meta": {"type": "object", "additionalProperties": {"type": "string"}}
                },
                "required": ["meta"],
            }
        )
        model = to_model(
            schema,
            rules=[
                Rule(ByType(dict), After(sorted_keys)),
            ],
        )

        instance = model(meta={"b": "2", "a": "1"})
        assert instance.model_dump() == snapshot({"meta": {"a": "1", "b": "2"}})


class TestByTypeFormatTypes:
    """The type passed to `formats` is also the type that targets the nodes it substituted."""

    @pytest.mark.parametrize(
        ("format_name", "format_type", "value"),
        _FORMAT_CASES,
        ids=[format_name for format_name, _, _ in _FORMAT_CASES],
    )
    def test_format_type_targets_its_own_nodes(
        self,
        format_name: str,
        format_type: ByTypeTargetType,
        value: str,
    ) -> None:
        """`ByType(<format type>)` reaches the field that same type was substituted into."""
        matched: list[FieldValueType] = []

        def mark(field_value: FieldValueType) -> FieldValueType:
            matched.append(field_value)
            return field_value

        schema = Schema.model_validate(
            {
                "type": "object",
                "properties": {"value": {"type": "string", "format": format_name}},
                "required": ["value"],
            }
        )
        model = to_model(
            schema,
            formats={format_name: format_type},
            rules=[
                Rule(ByType(format_type), After(mark)),
            ],
        )

        model(value=value)
        assert len(matched) == 1

    def test_every_exported_format_type_is_covered(self) -> None:
        """The case table above spans the whole `formats` export list.

        Without this guard a newly exported format type would be absent from the table rather
        than failing it, and would silently keep the alias bug it was added with.
        """
        covered = {format_type for _, format_type, _ in _FORMAT_CASES}
        exported = {getattr(formats, name) for name in formats.__all__}

        assert covered == exported

    @pytest.mark.parametrize(
        ("target", "expected"),
        [
            (Tags, ["b", "a"]),
            (Timestamps, ["b", "a"]),
        ],
        ids=["alias", "alias-of-alias"],
    )
    def test_user_alias_resolves_to_what_it_names(
        self,
        target: ByTypeTargetType,
        expected: list[str],
    ) -> None:
        """A PEP 695 alias targets whatever it names, however many aliases deep."""
        schema = Schema.model_validate(
            {
                "type": "object",
                "properties": {"tags": {"type": "array", "items": {"type": "string"}}},
                "required": ["tags"],
            }
        )
        model = to_model(
            schema,
            rules=[
                Rule(ByType(target), After(reverse_items)),
            ],
        )

        assert model(tags=["a", "b"]).model_dump() == {"tags": expected}


class TestByPathPointers:
    """`ByPath` addresses nodes by their true JSON Pointer.

    The pointer is built from one token per level, so a union branch index is its own token, a
    definition sits under `$defs`, and a property name keeps whatever characters it has (escaped
    per RFC 6901).
    """

    def test_root_value_is_the_root_pointer(self) -> None:
        """A root scalar has no tokens above it, so its pointer is `/`."""
        schema = Schema.model_validate({"type": "string"})
        model = to_model(
            schema,
            rules=[
                Rule(ByPath("/"), After(strip_upper)),
            ],
        )

        assert model(" ab ").model_dump() == snapshot("AB")  # type: ignore[call-arg]

    def test_object_root_has_no_annotation_at_the_root_pointer(self) -> None:
        """An object root becomes the model class, so `/` has no annotation to wrap.

        Rules attach where a node turns into an annotation — a field, a validated branch, or an
        inline child. A `RootModel` value is a field (`field_kind="root"`), but an object root is
        not: its properties are the fields. Target those instead.
        """
        schema = Schema.model_validate(
            {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            }
        )
        model = to_model(
            schema,
            rules=[
                Rule(ByPath("/"), After(strip_upper)),
            ],
        )

        assert model(name=" ab ").model_dump() == snapshot({"name": " ab "})

    def test_union_branch_index_is_its_own_token(self) -> None:
        """A branch is `anyOf/0`, not `anyOf[0]` — only the string branch is normalized."""
        schema = Schema.model_validate(
            {
                "type": "object",
                "properties": {"value": {"anyOf": [{"type": "string"}, {"type": "integer"}]}},
                "required": ["value"],
            }
        )
        model = to_model(
            schema,
            rules=[
                Rule(ByPath("/properties/value/anyOf/0"), After(strip_upper)),
            ],
        )

        assert model(value=" ab ").model_dump() == snapshot({"value": "AB"})
        assert model(value=7).model_dump() == snapshot({"value": 7})

    def test_definition_node_does_not_claim_the_root_pointer(self) -> None:
        """A def's nodes live under `$defs/<name>`, so they never collide with root properties."""
        schema = Schema.model_validate(
            {
                "type": "object",
                "$defs": {
                    "User": {
                        "type": "object",
                        "properties": {"name": {"type": "string"}},
                        "required": ["name"],
                    }
                },
                "properties": {"user": {"$ref": "#/$defs/User"}, "name": {"type": "string"}},
                "required": ["user", "name"],
            }
        )
        model = to_model(
            schema,
            rules=[
                Rule(ByPath("/$defs/User/properties/name"), After(strip_upper)),
            ],
        )

        instance = model(user={"name": " nested "}, name=" root ")
        # Only the def's `name` is normalized; the same-named root property is untouched.
        assert instance.model_dump() == snapshot({"user": {"name": "NESTED"}, "name": " root "})

    @pytest.mark.parametrize(
        ("property_name", "pointer"),
        [
            ("a.b", "/properties/a.b"),
            ("a/b", "/properties/a~1b"),
            ("a~b", "/properties/a~0b"),
        ],
        ids=["dotted", "slash-escaped", "tilde-escaped"],
    )
    def test_special_characters_in_property_name(
        self,
        property_name: str,
        pointer: str,
    ) -> None:
        """A dot stays part of the name; `/` and `~` are escaped as `~1` / `~0`."""
        schema = Schema.model_validate(
            {
                "type": "object",
                "properties": {property_name: {"type": "string"}},
                "required": [property_name],
            }
        )
        model = to_model(
            schema,
            rules=[
                Rule(ByPath(pointer), After(strip_upper)),
            ],
        )

        instance = model(**{property_name: " ab "})
        assert instance.model_dump() == {property_name: "AB"}


class TestByPathPointerForm:
    """`ByPath` takes one pointer spelling: the one `MatchContext.path` reports."""

    @pytest.mark.parametrize(
        ("pointer", "suggestion"),
        [
            ("#/properties/code", "/properties/code"),
            ("#/$defs/User/properties/name", "/$defs/User/properties/name"),
            ("properties/code", "/properties/code"),
            ("", "/"),
        ],
        ids=["fragment", "ref-fragment", "bare", "empty"],
    )
    def test_rejects_other_spellings(self, pointer: str, suggestion: str) -> None:
        """A pointer that does not start with `/` raises, naming the one to use instead."""
        with pytest.raises(ValueError, match="takes a JSON Pointer starting with") as error_info:
            ByPath(pointer)

        assert repr(suggestion) in str(error_info.value)

    def test_reported_paths_are_accepted_verbatim(self) -> None:
        """Every path a matcher observes is a valid `ByPath` pointer, with no rewriting."""
        seen: list[str] = []

        def collect(context: MatchContext) -> bool:
            seen.append(context.path)
            return False

        schema = Schema.model_validate(
            {
                "type": "object",
                "$defs": {
                    "User": {
                        "type": "object",
                        "properties": {"name": {"type": "string"}},
                        "required": ["name"],
                    }
                },
                "properties": {
                    "user": {"$ref": "#/$defs/User"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["user", "tags"],
            }
        )
        to_model(
            schema,
            rules=[
                Rule(ByFunc(collect), After(strip_upper)),
            ],
        )

        assert seen == snapshot(
            [
                "/$defs/User/properties/name",
                "/properties/user",
                "/properties/tags/items",
                "/properties/tags",
            ]
        )
        assert [ByPath(path).pointer for path in seen] == seen


class TestModelCache:
    """Generated models are cached, and rules make that cache path-aware."""

    @pytest.mark.parametrize(
        ("pointer", "expected"),
        [
            (
                "/properties/first/properties/code",
                {"first": {"code": "A"}, "second": {"code": " b "}},
            ),
            (
                "/properties/second/properties/code",
                {"first": {"code": " a "}, "second": {"code": "B"}},
            ),
        ],
        ids=["first", "second"],
    )
    def test_equal_inline_objects_convert_per_path(
        self,
        pointer: str,
        expected: dict[str, Any],
    ) -> None:
        """Two structurally equal inline objects each get their own class, so `ByPath` hits one."""
        schema = Schema.model_validate(
            {
                "type": "object",
                "properties": {
                    "first": {
                        "type": "object",
                        "properties": {"code": {"type": "string"}},
                        "required": ["code"],
                    },
                    "second": {
                        "type": "object",
                        "properties": {"code": {"type": "string"}},
                        "required": ["code"],
                    },
                },
                "required": ["first", "second"],
            }
        )
        model = to_model(
            schema,
            rules=[
                Rule(ByPath(pointer), After(strip_upper)),
            ],
        )

        instance = model(first={"code": " a "}, second={"code": " b "})
        assert instance.model_dump() == expected

    def test_equal_inline_objects_share_a_class_without_rules(self) -> None:
        """Without rules the pointer is irrelevant, so the cache still collapses equal schemas."""
        schema = Schema.model_validate(
            {
                "type": "object",
                "properties": {
                    "first": {
                        "type": "object",
                        "properties": {"code": {"type": "string"}},
                        "required": ["code"],
                    },
                    "second": {
                        "type": "object",
                        "properties": {"code": {"type": "string"}},
                        "required": ["code"],
                    },
                },
                "required": ["first", "second"],
            }
        )
        model = to_model(schema)

        first = model.model_fields["first"].annotation
        assert first is model.model_fields["second"].annotation

    def test_shared_definition_stays_one_class(self) -> None:
        """A def converts once under its own pointer, however many `$ref`s reach it."""
        schema = Schema.model_validate(
            {
                "type": "object",
                "$defs": {
                    "User": {
                        "type": "object",
                        "properties": {"name": {"type": "string"}},
                        "required": ["name"],
                    }
                },
                "properties": {
                    "author": {"$ref": "#/$defs/User"},
                    "reviewer": {"$ref": "#/$defs/User"},
                },
                "required": ["author", "reviewer"],
            }
        )
        model = to_model(
            schema,
            rules=[
                Rule(ByPath("/$defs/User/properties/name"), After(strip_upper)),
            ],
        )

        author = model.model_fields["author"].annotation
        assert author is model.model_fields["reviewer"].annotation

        instance = model(author={"name": " a "}, reviewer={"name": " b "})
        assert instance.model_dump() == snapshot(
            {"author": {"name": "A"}, "reviewer": {"name": "B"}}
        )

    def test_definition_alias_reuses_the_target_class(self) -> None:
        """An alias is another name for the target, so a rule on the target covers it too."""
        schema = Schema.model_validate(
            {
                "type": "object",
                "$defs": {
                    "User": {
                        "type": "object",
                        "properties": {"name": {"type": "string"}},
                        "required": ["name"],
                    },
                    "Author": {"$ref": "#/$defs/User"},
                },
                "properties": {
                    "user": {"$ref": "#/$defs/User"},
                    "author": {"$ref": "#/$defs/Author"},
                },
                "required": ["user", "author"],
            }
        )
        model = to_model(
            schema,
            rules=[
                Rule(ByPath("/$defs/User/properties/name"), After(strip_upper)),
            ],
        )

        user = model.model_fields["user"].annotation
        assert user is model.model_fields["author"].annotation

        instance = model(user={"name": " a "}, author={"name": " b "})
        assert instance.model_dump() == snapshot({"user": {"name": "A"}, "author": {"name": "B"}})

    def test_alias_name_is_not_an_addressable_pointer(self) -> None:
        """An alias has no pointer of its own: only the name declaring the schema addresses it.

        The flip side of the test above. `Author` resolves to `User`'s schema, so the converter
        walks it once under `/$defs/User` and never emits `/$defs/Author`. Aiming a rule at the
        alias name is therefore a no-op — asserted here so the choice of pointer cannot change
        unnoticed.
        """
        schema = Schema.model_validate(
            {
                "type": "object",
                "$defs": {
                    "User": {
                        "type": "object",
                        "properties": {"name": {"type": "string"}},
                        "required": ["name"],
                    },
                    "Author": {"$ref": "#/$defs/User"},
                },
                "properties": {
                    "user": {"$ref": "#/$defs/User"},
                    "author": {"$ref": "#/$defs/Author"},
                },
                "required": ["user", "author"],
            }
        )
        model = to_model(
            schema,
            rules=[
                Rule(ByPath("/$defs/Author/properties/name"), After(strip_upper)),
            ],
        )

        instance = model(user={"name": " a "}, author={"name": " b "})
        assert instance.model_dump() == snapshot(
            {"user": {"name": " a "}, "author": {"name": " b "}}
        )


class TestChildNodes:
    """Rules reach inline child schemas that never become a field of their own."""

    def test_array_items(self) -> None:
        """A rule matching the element type applies to every item of an inline `items`."""
        schema = Schema.model_validate(
            {
                "type": "object",
                "properties": {"tags": {"type": "array", "items": {"type": "string"}}},
                "required": ["tags"],
            }
        )
        model = to_model(
            schema,
            rules=[
                Rule(ByType(str), After(strip_upper)),
            ],
        )

        assert model(tags=[" a ", "b"]).model_dump() == snapshot({"tags": ["A", "B"]})

    def test_map_values(self) -> None:
        """A rule matching the value type applies to every value of a typed map."""
        schema = Schema.model_validate(
            {
                "type": "object",
                "properties": {
                    "meta": {"type": "object", "additionalProperties": {"type": "string"}}
                },
                "required": ["meta"],
            }
        )
        model = to_model(
            schema,
            rules=[
                Rule(ByType(str), After(strip_upper)),
            ],
        )

        assert model(meta={"k": " v "}).model_dump() == snapshot({"meta": {"k": "V"}})

    @pytest.mark.parametrize(
        ("raw_schema", "pointer", "payload", "expected"),
        [
            (
                {
                    "type": "object",
                    "properties": {"tags": {"type": "array", "items": {"type": "string"}}},
                    "required": ["tags"],
                },
                "/properties/tags/items",
                {"tags": [" a "]},
                {"tags": ["A"]},
            ),
            (
                {
                    "type": "object",
                    "properties": {
                        "meta": {"type": "object", "additionalProperties": {"type": "string"}}
                    },
                    "required": ["meta"],
                },
                "/properties/meta/additionalProperties",
                {"meta": {"k": " v "}},
                {"meta": {"k": "V"}},
            ),
        ],
        ids=["items", "additionalProperties"],
    )
    def test_child_is_addressable_by_path(
        self,
        raw_schema: "SchemaRaw",
        pointer: str,
        payload: dict[str, Any],
        expected: dict[str, Any],
    ) -> None:
        """A child node carries its own pointer, so `ByPath` can target it directly."""
        schema = Schema.model_validate(raw_schema)
        model = to_model(
            schema,
            rules=[
                Rule(ByPath(pointer), After(strip_upper)),
            ],
        )

        assert model(**payload).model_dump() == expected

    def test_format_substitution_runs_before_rules(self) -> None:
        """A formatted child is matched on the substituted annotation, and rules wrap it after."""
        schema = Schema.model_validate(
            {
                "type": "object",
                "properties": {
                    "tags": {"type": "array", "items": {"type": "string", "format": "custom"}}
                },
                "required": ["tags"],
            }
        )
        formats: dict[str, Any] = {"custom": Annotated[str, AfterValidator(str.upper)]}

        # `ByType(str)` sees the substituted `Annotated[...]`, so it no longer matches — only the
        # format runs. Same rule as for a formatted field.
        by_type = to_model(
            schema,
            formats=formats,
            rules=[
                Rule(ByType(str), After(exclaim)),
            ],
        )
        assert by_type(tags=["ab"]).model_dump() == snapshot({"tags": ["AB"]})

        # `ByPath` is annotation-independent, so it still matches and layers on top of the format.
        by_path = to_model(
            schema,
            formats=formats,
            rules=[
                Rule(ByPath("/properties/tags/items"), After(exclaim)),
            ],
        )
        assert by_path(tags=["ab"]).model_dump() == snapshot({"tags": ["AB!"]})

    def test_dump_on_items(self) -> None:
        """`Dump` on the element type serializes each item."""
        schema = Schema.model_validate(
            {
                "type": "object",
                "properties": {"tags": {"type": "array", "items": {"type": "string"}}},
                "required": ["tags"],
            }
        )
        model = to_model(
            schema,
            rules=[
                Rule(ByType(str), Dump(str.upper)),
            ],
        )

        assert model(tags=["a", "b"]).model_dump() == snapshot({"tags": ["A", "B"]})


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
        rule = Rule(ByPath("/properties/created"), After(strip_upper))
        # NOTE: A function's `repr` carries its non-deterministic memory address, so match only
        # the stable prefix (`repr(rule) == "..."` would flap across runs).
        assert repr(rule).startswith(
            "Rule(matcher=ByPath(pointer='/properties/created'), action=After(func=<function "
        )
