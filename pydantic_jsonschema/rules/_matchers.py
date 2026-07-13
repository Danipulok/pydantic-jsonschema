"""Matchers: the *when* of a loading rule.

A matcher answers one question about a schema node the converter is about to turn into a field:
"does this rule apply here?". The node is described by a `MatchContext` (schema, resolved
annotation, JSON Pointer); the three concrete matchers cover the useful axes:

- `ByType` — match on the resolved Python annotation (`list[str]`, `str`, `datetime`, ...);
- `ByPath` — match on the node's JSON Pointer (`#/properties/created`);
- `ByFunc` — escape hatch: an arbitrary predicate over the `MatchContext`.

All matchers are frozen dataclasses, so they compare, hash, and `repr` as plain data. `ByType`
and `ByPath` hold only data; `ByFunc` holds a callable and is therefore the one matcher that does
not serialize to JSON.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Protocol, override

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


def _normalize_pointer(pointer: str, /) -> str:
    """Normalize a user-supplied pointer to the converter's canonical `/a/b` form.

    Accepts a JSON Pointer (`#/properties/created`), a leading-slash form
    (`/properties/created`), or a bare form (`properties/created`); all normalize identically.

    :param pointer: User-supplied path pointer.
    :returns: Canonical pointer starting with `/`.
    """
    stripped: str = pointer.removeprefix("#")
    return stripped if stripped.startswith("/") else f"/{stripped}"


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
    """Match when the resolved core annotation equals `target`.

    `target` is a Python type or typing form (`list[str]`, `str`, `datetime`). Comparison is
    equality, so parameterized generics match exactly (`list[str]`, not `list[int]`). A node whose
    annotation a `formats` entry already replaced (e.g. `Annotated[str, ...]`) will not match a
    bare `ByType(str)`.
    """

    target: AnnotationType

    @override
    def matches(self, context: MatchContext, /) -> bool:
        """Return whether the resolved annotation equals `target`."""
        return bool(context.annotation == self.target)


@dataclass(frozen=True, slots=True)
class ByPath(Matcher):
    """Match when the node's JSON Pointer equals `pointer`.

    `pointer` accepts `#/properties/created`, `/properties/created`, or `properties/created` —
    all normalize to the same canonical form before comparison.
    """

    pointer: str

    @override
    def matches(self, context: MatchContext, /) -> bool:
        """Return whether the node's canonical pointer equals the normalized `pointer`."""
        return context.path == _normalize_pointer(self.pointer)


@dataclass(frozen=True, slots=True)
class ByFunc(Matcher):
    """Match when `predicate(context)` returns `True`."""

    predicate: SchemaPredicate

    @override
    def matches(self, context: MatchContext, /) -> bool:
        """Delegate the decision to the user predicate."""
        return self.predicate(context)
