"""Actions: the *what* and *how* of a loading rule.

An action pairs a callable (the *what*) with a Pydantic slot (the *how*). Each concrete action
maps to exactly one Pydantic wrapper, so a rule that holds one action performs exactly one thing:

- `Before` -> `BeforeValidator` — coerce raw input before core parsing (e.g. `"a,b,c"` -> list);
- `After` -> `AfterValidator` — normalize / validate the parsed value;
- `Override` -> `PlainValidator` — replace core parsing entirely;
- `Dump` -> `PlainSerializer` — transform the value on serialization (model -> output).

Actions are frozen dataclasses: they compare, hash, and `repr` as data. Their only non-data field
is the held callable.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Protocol, override

from pydantic import AfterValidator, BeforeValidator, PlainSerializer, PlainValidator

__all__ = [
    "Action",
    "After",
    "Before",
    "Dump",
    "Loader",
    "Override",
    "Serializer",
]

# The Pydantic metadata object an action contributes to an `Annotated` annotation.
type MetadataType = Any
# A loaded / dumped value; genuinely unconstrained, so aliased to keep it out of `ANN401`.
type ValueType = Any


class Loader(Protocol):
    """A callable that transforms a value during loading (input -> value)."""

    def __call__(self, value: ValueType, /) -> ValueType: ...


class Serializer(Protocol):
    """A callable that transforms a value during dumping (value -> output)."""

    def __call__(self, value: ValueType, /) -> ValueType: ...


class Action(ABC):
    """Base for the *what* + *how* of a rule: contributes one Pydantic metadata object."""

    @abstractmethod
    def metadata(self) -> MetadataType:
        """Return the Pydantic wrapper to attach as `Annotated` metadata."""


@dataclass(frozen=True, slots=True)
class Before(Action):
    """Run `func` before core parsing, on the raw input (`BeforeValidator`)."""

    func: Loader

    @override
    def metadata(self) -> MetadataType:
        """Wrap `func` as a `BeforeValidator`."""
        return BeforeValidator(self.func)


@dataclass(frozen=True, slots=True)
class After(Action):
    """Run `func` after core parsing, on the parsed value (`AfterValidator`)."""

    func: Loader

    @override
    def metadata(self) -> MetadataType:
        """Wrap `func` as an `AfterValidator`."""
        return AfterValidator(self.func)


@dataclass(frozen=True, slots=True)
class Override(Action):
    """Replace core parsing with `func` entirely (`PlainValidator`)."""

    func: Loader

    @override
    def metadata(self) -> MetadataType:
        """Wrap `func` as a `PlainValidator`."""
        return PlainValidator(self.func)


@dataclass(frozen=True, slots=True)
class Dump(Action):
    """Transform the value on serialization with `func` (`PlainSerializer`)."""

    func: Serializer

    @override
    def metadata(self) -> MetadataType:
        """Wrap `func` as a `PlainSerializer`."""
        return PlainSerializer(self.func)
