"""Actions: the *what* and *how* of a loading rule.

An action pairs a callable (the *what*) with the mechanism that runs it (the *how*). Actions come
in two families, distinguished by what they attach to:

*Annotation actions* wrap the matched node's field annotation with one Pydantic metadata object:

- `Before` -> `BeforeValidator` — coerce raw input before core parsing (e.g. `"a,b,c"` -> list);
- `After` -> `AfterValidator` — normalize / validate the parsed value;
- `Override` -> `PlainValidator` — replace core parsing entirely;
- `Dump` -> `PlainSerializer` — transform the value on serialization (model -> output).

*Model actions* attach a whole-object `model_validator` to the matched object model's class (root
or nested), the only way to reach the root model — its value has no field annotation to wrap:

- `ModelBefore` -> `model_validator(mode="before")` — transform the raw mapping before parsing;
- `ModelAfter` -> `model_validator(mode="after")` — validate / adjust the built model (cross-field);
- `ModelWrap` -> `model_validator(mode="wrap")` — wrap construction, calling `handler` to build.

Actions are frozen dataclasses: they compare, hash, and `repr` as data. Their only non-data field
is the held callable.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Protocol, override

from pydantic import (
    AfterValidator,
    BeforeValidator,
    PlainSerializer,
    PlainValidator,
    model_validator,
)

__all__ = [
    "Action",
    "After",
    "AnnotationAction",
    "Before",
    "Dump",
    "Loader",
    "ModelAction",
    "ModelAfter",
    "ModelBefore",
    "ModelWrap",
    "ModelWrapper",
    "Override",
    "Serializer",
]

# The Pydantic metadata object an annotation action contributes to an `Annotated` annotation.
type MetadataType = Any
# The Pydantic `model_validator` descriptor a model action attaches to an object model's class.
type ModelValidatorType = Any
# A loaded / dumped value; genuinely unconstrained, so aliased to keep it out of `ANN401`.
type ValueType = Any


class Loader(Protocol):
    """A callable that transforms a value during loading (input -> value)."""

    def __call__(self, value: ValueType, /) -> ValueType: ...


class Serializer(Protocol):
    """A callable that transforms a value during dumping (value -> output)."""

    def __call__(self, value: ValueType, /) -> ValueType: ...


class ModelWrapper(Protocol):
    """A wrap-mode model validator: transform raw input, calling `handler` to build the model."""

    def __call__(self, data: ValueType, handler: ValueType, /) -> ValueType: ...


# NOTE: `Action` is an abstract marker with no abstract method of its own — the two families
# (`AnnotationAction` / `ModelAction`) declare different contracts (`metadata` vs `validator`). It
# exists so `Rule.action` has one common type and the converter can `isinstance`-dispatch families.
class Action(ABC):  # noqa: B024
    """Base for a rule's effect — either an annotation action or a model action."""


class AnnotationAction(Action, ABC):
    """An action that wraps the matched node's field annotation with Pydantic metadata."""

    @abstractmethod
    def metadata(self) -> MetadataType:
        """Return the Pydantic wrapper to attach as `Annotated` metadata."""


class ModelAction(Action, ABC):
    """An action that attaches a whole-object `model_validator` to the matched object model."""

    @abstractmethod
    def validator(self) -> ModelValidatorType:
        """Return the Pydantic `model_validator` descriptor to attach to the model class."""


@dataclass(frozen=True, slots=True)
class Before(AnnotationAction):
    """Run `func` before core parsing, on the raw input (`BeforeValidator`)."""

    func: Loader

    @override
    def metadata(self) -> MetadataType:
        """Wrap `func` as a `BeforeValidator`."""
        return BeforeValidator(self.func)


@dataclass(frozen=True, slots=True)
class After(AnnotationAction):
    """Run `func` after core parsing, on the parsed value (`AfterValidator`)."""

    func: Loader

    @override
    def metadata(self) -> MetadataType:
        """Wrap `func` as an `AfterValidator`."""
        return AfterValidator(self.func)


@dataclass(frozen=True, slots=True)
class Override(AnnotationAction):
    """Replace core parsing with `func` entirely (`PlainValidator`)."""

    func: Loader

    @override
    def metadata(self) -> MetadataType:
        """Wrap `func` as a `PlainValidator`."""
        return PlainValidator(self.func)


@dataclass(frozen=True, slots=True)
class Dump(AnnotationAction):
    """Transform the value on serialization with `func` (`PlainSerializer`)."""

    func: Serializer

    @override
    def metadata(self) -> MetadataType:
        """Wrap `func` as a `PlainSerializer`."""
        return PlainSerializer(self.func)


@dataclass(frozen=True, slots=True)
class ModelBefore(ModelAction):
    """Run `func` on the raw mapping before field parsing (`model_validator(mode="before")`).

    `func` receives the raw input (usually a `dict`) and returns the mapping to parse.
    """

    func: Loader

    @override
    def validator(self) -> ModelValidatorType:
        """Wrap `func` as a `before` model validator."""
        return model_validator(mode="before")(self.func)


@dataclass(frozen=True, slots=True)
class ModelAfter(ModelAction):
    """Run `func` on the built model (`model_validator(mode="after")`).

    `func` receives the constructed model instance and returns it — the slot for cross-field
    validation, where every field is already populated.
    """

    func: Loader

    @override
    def validator(self) -> ModelValidatorType:
        """Wrap `func` as an `after` model validator."""
        return model_validator(mode="after")(self.func)


@dataclass(frozen=True, slots=True)
class ModelWrap(ModelAction):
    """Wrap model construction with `func` (`model_validator(mode="wrap")`).

    `func` receives the raw input and a `handler`; calling `handler(data)` builds the model, so
    `func` can act both before and after construction and short-circuit it entirely.
    """

    func: ModelWrapper

    @override
    def validator(self) -> ModelValidatorType:
        """Wrap `func` as a `wrap` model validator."""
        # NOTE: Pydantic's `model_validator(mode="wrap")` overloads type the callable as
        # `(cls, value, handler)`, but accept a plain `(value, handler)` at runtime — which keeps
        # `cls` out of the user-facing `ModelWrapper`. mypy can't see that, so ignore the arg type.
        # `TestModelWrap` in `tests/converters/test_rules.py` exercises the 2-arg form end to end.
        return model_validator(mode="wrap")(self.func)  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]
