"""JSON Schema `if` / `then` / `else` validator.

See: https://json-schema.org/draft/2020-12/json-schema-core#section-10.2.2
"""

from typing import Any, ForwardRef

from pydantic import (
    BaseModel,
    GetCoreSchemaHandler,
    TypeAdapter,
    ValidationError,
)
from pydantic_core import CoreSchema, core_schema

__all__ = ["IfThenElse"]

# Type aliases
type AnnotationType = (
    Any  # Any annotation Pydantic supports (`type`, `Annotated`, `ForwardRef`, ...)
)


class IfThenElse:
    """Enforce JSON Schema `if` / `then` / `else` conditional application.

    If the instance validates against `if`, it must also validate against `then`; otherwise it
    must validate against `else`. `then` / `else` are optional (a missing branch imposes no
    constraint). All checks run on the *raw* input. Used both as `Annotated` metadata (a
    wrap-validator) on value annotations and via `check` from a `before` model validator on a
    root object model. Subschemas may be `ForwardRef` (pointing at a `$ref`), resolved lazily
    via `bind_namespace`.
    """

    def __init__(
        self,
        *,
        if_branch: AnnotationType,
        then_branch: AnnotationType | None,
        else_branch: AnnotationType | None,
    ) -> None:
        """Initialize with the `if` / `then` / `else` subschema annotations.

        :param if_branch: The `if` condition subschema (may be a `ForwardRef`).
        :param then_branch: The `then` subschema applied on a match, or `None`.
        :param else_branch: The `else` subschema applied on no match, or `None`.
        """
        self._if: AnnotationType = if_branch
        self._then: AnnotationType | None = then_branch
        self._else: AnnotationType | None = else_branch
        self._namespace: dict[str, type[BaseModel]] = {}
        self._if_adapter: TypeAdapter[AnnotationType] | None = None
        self._then_adapter: TypeAdapter[AnnotationType] | None = None
        self._else_adapter: TypeAdapter[AnnotationType] | None = None

    def bind_namespace(
        self,
        namespace: dict[str, type[BaseModel]],
        /,
    ) -> None:
        """Provide the namespace used to resolve `ForwardRef` subschemas.

        :param namespace: Mapping of sanitized reference names to models.
        """
        self._namespace = namespace

    def __get_pydantic_core_schema__(
        self,
        source_type: AnnotationType,
        handler: GetCoreSchemaHandler,
    ) -> CoreSchema:
        """Wrap the value schema with the conditional check (on the raw input)."""
        return core_schema.no_info_wrap_validator_function(self._validate, handler(source_type))

    def _resolve(
        self,
        branch: AnnotationType,
        /,
    ) -> AnnotationType:
        """Resolve a `ForwardRef` subschema against the bound namespace.

        :param branch: A subschema annotation, possibly a `ForwardRef`.
        :returns: The resolved model, or the annotation unchanged.
        """
        return self._namespace[branch.__forward_arg__] if isinstance(branch, ForwardRef) else branch

    def _build_adapters(self) -> TypeAdapter[AnnotationType]:
        """Build the `if` / `then` / `else` adapters, resolving `ForwardRef`s on first use.

        :returns: The `if` adapter (always present).
        """
        # NOTE: Built lazily: at conversion time subschemas may be `ForwardRef`s that only become
        #       resolvable after the whole schema (including `$defs`) is converted and the
        #       namespace is bound via `bind_namespace`.
        if self._if_adapter is not None:
            return self._if_adapter

        if_adapter: TypeAdapter[AnnotationType] = TypeAdapter(self._resolve(self._if))
        self._if_adapter = if_adapter
        if self._then is not None:
            self._then_adapter = TypeAdapter(self._resolve(self._then))
        if self._else is not None:
            self._else_adapter = TypeAdapter(self._resolve(self._else))
        return if_adapter

    @staticmethod
    def _matches(
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

    def check(
        self,
        value: AnnotationType,
        /,
    ) -> AnnotationType:
        """Apply the `then` / `else` branch selected by the `if` condition.

        :param value: The raw input value.
        :returns: The value unchanged when the selected branch validates.
        :raises ValueError: When the selected branch does not validate the value.
        """
        if_adapter = self._build_adapters()

        if self._matches(if_adapter, value):
            if self._then_adapter is not None and not self._matches(self._then_adapter, value):
                msg = "Value matches `if` but not `then`"
                raise ValueError(msg)
        elif self._else_adapter is not None and not self._matches(self._else_adapter, value):
            msg = "Value does not match `if` and not `else`"
            raise ValueError(msg)

        return value

    def _validate(
        self,
        value: AnnotationType,
        handler: core_schema.ValidatorFunctionWrapHandler,
    ) -> AnnotationType:
        """Run the conditional check, then delegate to the host schema.

        :param value: Raw input value.
        :param handler: Wrapped host-type validator.
        :returns: The validated value.
        :raises ValueError: When the conditional check fails.
        """
        self.check(value)
        return handler(value)
