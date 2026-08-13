"""Matchers: the *when* of a loading rule.

A matcher answers one question about a schema node the converter is about to turn into a field:
"does this rule apply here?". The node is described by a `MatchContext` (schema, resolved
annotation, JSON Pointer); the three concrete matchers cover the useful axes:

- `ByType` — match on the resolved Python annotation (`list[str]`, `str`, `datetime`, ...);
- `ByPath` — match on the node's JSON Pointer (`/properties/created`);
- `ByFunc` — escape hatch: an arbitrary predicate over the `MatchContext`.

All matchers are frozen dataclasses, so they compare, hash, and `repr` as plain data. `ByType`
and `ByPath` hold only data; `ByFunc` holds a callable and is therefore the one matcher that does
not serialize to JSON.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Protocol, get_origin, override

from pydantic_jsonschema._utils import unwrap_type_alias
from pydantic_jsonschema.schema import Schema

__all__ = [
    "ByFunc",
    "ByPath",
    "ByType",
    "MatchContext",
    "Matcher",
    "SchemaPredicate",
]

# Any annotation Pydantic supports (`type`, `Annotated`, `Union`, `Literal`, ...).
type AnnotationType = Any


@dataclass(frozen=True, slots=True)
class MatchContext:
    """The node a matcher is asked about: its schema, resolved annotation, and JSON Pointer."""

    schema: Schema
    annotation: AnnotationType
    path: str


class SchemaPredicate(Protocol):
    """A user predicate deciding whether a `ByFunc` matcher applies to a node."""

    def __call__(self, context: MatchContext, /) -> bool: ...


class Matcher(ABC):
    """Base for the *when* of a rule: decides whether a rule applies to a schema node."""

    @abstractmethod
    def matches(self, context: MatchContext, /) -> bool:
        """Return whether this matcher applies to the given node.

        :param context: The node's schema, resolved core annotation, and canonical JSON Pointer.
        :returns: `True` when the rule should apply here.
        """


@dataclass(frozen=True, slots=True)
class ByType(Matcher):
    """Match when the resolved core annotation equals `target`, or parameterizes it.

    `target` is a Python type, typing form, or PEP 695 alias (`list[str]`, `str`, `datetime`,
    `Email`). A parameterized target matches exactly (`list[str]`, not `list[int]`); an
    unparameterized generic (`list`, `dict`, `set`) matches every parameterization of itself.

    A node whose annotation a `formats` entry replaced carries the format type, so target it with
    that same type — `ByType(Email)` reaches the email fields, while a bare `ByType(str)` reaches
    only the strings no format touched.
    """

    target: AnnotationType

    @override
    def matches(self, context: MatchContext, /) -> bool:
        """Return whether the resolved annotation equals `target` or is a parameterization of it."""
        # NOTE: Every built-in format type is a PEP 695 alias, and a `TypeAliasType` compares by
        # identity — so without unwrapping, aiming a rule at the very type passed to `formats`
        # matches nothing at all:
        #
        #   to_model(schema, formats={"date-time": DateTime},
        #            rules=[Rule(ByType(DateTime), After(to_utc))])
        #   # -> rule never fires: the node is `datetime.datetime`, and
        #   #    `DateTime == datetime.datetime` is False
        target: AnnotationType = unwrap_type_alias(self.target)

        # NOTE: An unparameterized generic never equals what the converter produces — an array is
        # `list[str]` or `list[Any]`, a typed map is `dict[str, T]` — so under plain equality a
        # rule built as `Rule(ByType(list), After(dedupe))` would silently match nothing at all.
        # `Annotated` is safe here: `get_origin(Annotated[str, ...])` is `Annotated`, not `str`,
        # so a format-substituted node still does not match a bare `ByType(str)`.
        origin: AnnotationType = get_origin(context.annotation)
        if isinstance(target, type) and origin is target:
            return True

        return bool(context.annotation == target)


@dataclass(frozen=True, slots=True)
class ByPath(Matcher):
    """Match when the node's JSON Pointer equals `pointer`.

    `pointer` is a JSON Pointer in exactly the form `MatchContext.path` reports it: a leading `/`,
    one token per level, no `#` prefix (`/properties/created`). Node pointers are RFC 6901 proper:
    an index is its own level (`anyOf/0`), a definition is addressed where it is declared
    (`/$defs/User/...`), and `~` / `/` inside a name are escaped as `~0` / `~1`. See
    `docs/rules.md` for the full list of addressable nodes.

    :raises ValueError: If `pointer` does not start with `/`.
    """

    pointer: str

    def __post_init__(self) -> None:
        """Reject any spelling other than the one the converter itself produces.

        The `#/a/b` fragment form is what a `$ref` looks like, so it is the natural thing to
        paste. Normalizing it instead of rejecting it makes the pointer a user writes differ from
        the one they can observe: the converter reports `/properties/code`, so a predicate
        comparing against the pasted fragment silently never fires while the `ByPath` spelled the
        same way does.

            Rule(ByFunc(lambda context: context.path == "#/properties/code"), After(strip))
            # -> never matches, unlike ByPath("#/properties/code") under normalization

        One accepted spelling keeps the two consistent, and turns a mistyped pointer into an
        error instead of a rule that quietly matches nothing.
        """
        if self.pointer.startswith("/"):
            return

        suggestion: str = f"/{self.pointer.removeprefix('#').lstrip('/')}"
        msg = (
            f"`ByPath` takes a JSON Pointer starting with `/`, got {self.pointer!r}. "
            f"Did you mean {suggestion!r}? This is the form `MatchContext.path` reports."
        )
        raise ValueError(msg)

    @override
    def matches(self, context: MatchContext, /) -> bool:
        """Return whether the node's pointer equals `pointer`."""
        return context.path == self.pointer


@dataclass(frozen=True, slots=True)
class ByFunc(Matcher):
    """Match when `predicate(context)` returns `True`."""

    predicate: SchemaPredicate

    @override
    def matches(self, context: MatchContext, /) -> bool:
        """Delegate the decision to the user predicate."""
        return self.predicate(context)
