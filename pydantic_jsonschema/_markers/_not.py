"""JSON Schema `not` validator.

See: https://json-schema.org/draft/2020-12/json-schema-core#section-10.2.1.4
"""

from typing import Any, ForwardRef

from pydantic import (
    BaseModel,
    GetCoreSchemaHandler,
    TypeAdapter,
    ValidationError,
)
from pydantic_core import CoreSchema, core_schema

__all__ = ["Not"]

# Type aliases
type AnnotationType = (
    Any  # Any annotation Pydantic supports (`type`, `Annotated`, `ForwardRef`, ...)
)


class Not:
    """Enforce JSON Schema `not`: the instance must NOT validate against the subschema.

    Used two ways, both checking the *raw* input (before the host type coerces it):

    - as `Annotated` metadata on a value annotation (a wrap-validator), for non-object values
      and nested objects/dicts;
    - via `matches`, from a `before` model validator on a root object model (which bypasses the
      annotation path).

    The subschema may be a `ForwardRef` (a `not` pointing at a `$ref`), resolved lazily through
    `bind_namespace`.
    """

    def __init__(
        self,
        *,
        branch: AnnotationType,
    ) -> None:
        """Initialize with the `not` subschema annotation.

        :param branch: The `not` subschema annotation (may be a `ForwardRef`).
        """
        self._branch: AnnotationType = branch
        self._namespace: dict[str, type[BaseModel]] = {}
        self._adapter: TypeAdapter[AnnotationType] | None = None

    def bind_namespace(
        self,
        namespace: dict[str, type[BaseModel]],
        /,
    ) -> None:
        """Provide the namespace used to resolve a `ForwardRef` subschema.

        :param namespace: Mapping of sanitized reference names to models.
        """
        self._namespace = namespace

    def __get_pydantic_core_schema__(
        self,
        source_type: AnnotationType,
        handler: GetCoreSchemaHandler,
    ) -> CoreSchema:
        """Wrap the value schema with the `not` check (on the raw input)."""
        return core_schema.no_info_wrap_validator_function(self._validate, handler(source_type))

    def matches(
        self,
        value: AnnotationType,
        /,
    ) -> bool:
        """Return whether a value validates against the `not` subschema.

        :param value: The raw input value.
        :returns: `True` when the value validates against `not` (and so must be rejected).
        """
        try:
            self._get_adapter().validate_python(value)
        except ValidationError:
            return False
        return True

    def _get_adapter(self) -> TypeAdapter[AnnotationType]:
        """Build the `not` adapter, resolving a `ForwardRef` subschema on first use.

        :returns: A `TypeAdapter` for the `not` subschema.
        """
        # NOTE: Built lazily: at conversion time the subschema may be a `ForwardRef` that only
        #       becomes resolvable after the whole schema (including `$defs`) is converted and
        #       the namespace is bound via `bind_namespace`.
        if self._adapter is None:
            branch = (
                self._namespace[self._branch.__forward_arg__]
                if isinstance(self._branch, ForwardRef)
                else self._branch
            )
            self._adapter = TypeAdapter(branch)
        return self._adapter

    def _validate(
        self,
        value: AnnotationType,
        handler: core_schema.ValidatorFunctionWrapHandler,
    ) -> AnnotationType:
        """Reject inputs matching the `not` subschema, then delegate to the host schema.

        :param value: Raw input value.
        :param handler: Wrapped host-type validator.
        :returns: The validated value.
        :raises ValueError: When the value matches the `not` subschema.
        """
        if self.matches(value):
            msg = "Value must not match the `not` schema"
            raise ValueError(msg)
        return handler(value)
