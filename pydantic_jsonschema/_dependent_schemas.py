"""JSON Schema `dependentSchemas` validator.

See: https://json-schema.org/draft/2020-12/json-schema-core#section-10.2.2.4
"""

from typing import Any, ForwardRef

from pydantic import (
    BaseModel,
    TypeAdapter,
    ValidationError,
)

__all__ = ["DependentSchemas"]

# Type aliases
type AnnotationType = (
    Any  # Any annotation Pydantic supports (`type`, `Annotated`, `ForwardRef`, ...)
)


class DependentSchemas:
    """Enforce JSON Schema `dependentSchemas`: a present property triggers a whole-object schema.

    For each `{property: subschema}` pair, when the property is present in the object the entire
    instance must also validate against the subschema. Used from a `before` model validator on
    object models; subschemas may be `ForwardRef` (pointing at a `$ref`), resolved lazily via
    `bind_namespace`.
    """

    def __init__(
        self,
        *,
        branches: dict[str, AnnotationType],
    ) -> None:
        """Initialize with the property-to-subschema mapping.

        :param branches: Mapping of trigger property name to its subschema annotation (each may
            be a `ForwardRef`).
        """
        self._branches: dict[str, AnnotationType] = dict(branches)
        self._namespace: dict[str, type[BaseModel]] = {}
        self._adapters: dict[str, TypeAdapter[AnnotationType]] | None = None

    def bind_namespace(
        self,
        namespace: dict[str, type[BaseModel]],
        /,
    ) -> None:
        """Provide the namespace used to resolve `ForwardRef` subschemas.

        :param namespace: Mapping of sanitized reference names to models.
        """
        self._namespace = namespace

    def _get_adapters(self) -> dict[str, TypeAdapter[AnnotationType]]:
        """Build the per-trigger adapters, resolving `ForwardRef` subschemas on first use.

        :returns: Mapping of trigger property name to its subschema `TypeAdapter`.
        """
        # NOTE: Built lazily: at conversion time subschemas may be `ForwardRef`s that only become
        #       resolvable after the whole schema (including `$defs`) is converted and the
        #       namespace is bound via `bind_namespace`.
        if self._adapters is None:
            self._adapters = {
                trigger: TypeAdapter(
                    self._namespace[branch.__forward_arg__]
                    if isinstance(branch, ForwardRef)
                    else branch
                )
                for trigger, branch in self._branches.items()
            }
        return self._adapters

    def validate(
        self,
        data: AnnotationType,
        /,
    ) -> AnnotationType:
        """Apply each triggered subschema to the whole instance.

        :param data: The raw input mapping (other input is left for type validation to reject).
        :returns: The input unchanged when every triggered subschema validates.
        :raises ValueError: When a present property's subschema does not validate the instance.
        """
        if not isinstance(data, dict):
            return data

        for trigger, adapter in self._get_adapters().items():
            if trigger not in data:
                continue
            try:
                adapter.validate_python(data)
            except ValidationError:
                msg = f"Property `{trigger}` does not satisfy its `dependentSchemas` schema"
                raise ValueError(msg) from None

        return data
