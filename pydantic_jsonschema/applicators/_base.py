"""Shared base and roles for applicator validators.

Every applicator validates values against one or more subschemas via a `TypeAdapter`. A subschema
may be a `ForwardRef` (a keyword pointing at a `$ref`) that only becomes resolvable after the whole
schema — including `$defs` — is converted. Applicators therefore build their adapters lazily, and
the converter binds a forward-ref namespace via `bind_namespace` once conversion finishes.

`Applicator` holds that shared plumbing; two abstract roles extend it and declare the hooks each
kind must implement:

- `AnnotationApplicator` — applied as `Annotated[type, self]` metadata, overriding Pydantic's
  `__get_pydantic_core_schema__` / `__get_pydantic_json_schema__`;
- `ObjectApplicator` — applied to an object model via the converter's model-wrapper, exposing
  `validate` / `json_schema_keyword`.

`Not` and `IfThenElse` fill both roles (used on a field annotation and on a root object).
"""

from abc import ABC, abstractmethod
from typing import Any, ForwardRef

from pydantic import (
    BaseModel,
    GetCoreSchemaHandler,
    GetJsonSchemaHandler,
    TypeAdapter,
    ValidationError,
)
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema

__all__ = [
    "AnnotationApplicator",
    "AnnotationType",
    "Applicator",
    "ObjectApplicator",
]

# Any annotation Pydantic supports (`type`, `Annotated`, `Union`, `Literal`, `ForwardRef`, ...).
type AnnotationType = Any


class Applicator:
    """Plumbing base for validators that check values against `TypeAdapter`-wrapped subschemas.

    Holds the forward-ref namespace and provides the shared plumbing: resolving a `ForwardRef`
    subschema and building its adapter, and testing whether a value validates against an adapter.
    Subclasses own their adapter caching (single / list / mapping), since the shape differs per
    keyword. Concrete applicators extend the abstract roles `AnnotationApplicator` and/or
    `ObjectApplicator` (which carry the required hooks), never this class directly.
    """

    def __init__(self) -> None:
        """Initialize with an empty forward-ref namespace (bound later via `bind_namespace`)."""
        self._namespace: dict[str, type[BaseModel]] = {}

    def bind_namespace(
        self,
        namespace: dict[str, type[BaseModel]],
        /,
    ) -> None:
        """Provide the namespace used to resolve `ForwardRef` subschemas.

        :param namespace: Mapping of sanitized reference names to models.
        """
        self._namespace = namespace

    def _build_adapter(
        self,
        branch: AnnotationType,
        /,
    ) -> TypeAdapter[AnnotationType]:
        """Build a `TypeAdapter` for a subschema, resolving a `ForwardRef` against the namespace.

        :param branch: A subschema annotation, possibly a `ForwardRef`.
        :returns: A `TypeAdapter` for the resolved subschema.
        """
        resolved: AnnotationType = (
            self._namespace[branch.__forward_arg__] if isinstance(branch, ForwardRef) else branch
        )
        return TypeAdapter(resolved)

    @staticmethod
    def _validates(
        adapter: TypeAdapter[AnnotationType],
        /,
        *,
        value: AnnotationType,
    ) -> bool:
        """Return whether a value validates against a subschema adapter.

        :param adapter: The subschema adapter.
        :param value: The raw input value.
        :returns: `True` when the value validates.
        """
        try:
            adapter.validate_python(value)
        except ValidationError:
            return False
        return True


class AnnotationApplicator(Applicator, ABC):
    """An applicator applied as `Annotated[type, self]` metadata on a value annotation.

    It overrides Pydantic's schema hooks: `__get_pydantic_core_schema__` enforces the keyword
    during validation, and `__get_pydantic_json_schema__` re-emits it on `model_json_schema()`.
    """

    @abstractmethod
    def __get_pydantic_core_schema__(
        self,
        source_type: AnnotationType,
        handler: GetCoreSchemaHandler,
    ) -> CoreSchema:
        """Build the core schema wrapping the host type with this applicator's check."""

    @abstractmethod
    def __get_pydantic_json_schema__(
        self,
        schema: CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        """Re-emit this applicator's keyword into the dumped JSON Schema."""


class ObjectApplicator(Applicator, ABC):
    """An applicator applied to an object model via the converter's model-wrapper.

    The wrapper delegates `validate` (raw-mapping check, run as a `before` validator) and
    `json_schema_keyword` (keyword fragment) from the model subclass's Pydantic hooks, so object
    keywords round-trip without riding on an `Annotated` annotation.
    """

    @abstractmethod
    def validate(self, data: AnnotationType, /) -> AnnotationType:
        """Validate the raw mapping, returning it unchanged or raising `ValueError`."""

    @abstractmethod
    def json_schema_keyword(self) -> JsonSchemaValue:
        """Return this applicator's keyword fragment for the dumped JSON Schema."""
