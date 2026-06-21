"""Shared base for marker validators.

Every marker validates values against one or more subschemas via a `TypeAdapter`. A subschema may
be a `ForwardRef` (a keyword pointing at a `$ref`) that only becomes resolvable after the whole
schema — including `$defs` — is converted. Markers therefore build their adapters lazily, and the
converter binds a forward-ref namespace via `bind_namespace` once conversion finishes.
"""

from typing import Any, ForwardRef

from pydantic import BaseModel, TypeAdapter, ValidationError

__all__ = [
    "AnnotationType",
    "SubschemaMarker",
]

# Any annotation Pydantic supports (`type`, `Annotated`, `Union`, `Literal`, `ForwardRef`, ...).
type AnnotationType = Any


class SubschemaMarker:
    """Base for validators that check values against `TypeAdapter`-wrapped subschemas.

    Holds the forward-ref namespace and provides the shared plumbing: resolving a `ForwardRef`
    subschema and building its adapter, and testing whether a value validates against an adapter.
    Subclasses own their adapter caching (single / list / mapping), since the shape differs per
    keyword.
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
        value: AnnotationType,
        /,
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
