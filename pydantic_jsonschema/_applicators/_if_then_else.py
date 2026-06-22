"""JSON Schema `if` / `then` / `else` validator.

See: https://json-schema.org/draft/2020-12/json-schema-core#section-10.2.2
"""

from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler, TypeAdapter
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema, core_schema

from ._base import AnnotationType, Applicator

__all__ = ["IfThenElse"]


class IfThenElse(Applicator):
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
        super().__init__()
        self._if: AnnotationType = if_branch
        self._then: AnnotationType | None = then_branch
        self._else: AnnotationType | None = else_branch
        self._if_adapter: TypeAdapter[AnnotationType] | None = None
        self._then_adapter: TypeAdapter[AnnotationType] | None = None
        self._else_adapter: TypeAdapter[AnnotationType] | None = None

    def __get_pydantic_core_schema__(
        self,
        source_type: AnnotationType,
        handler: GetCoreSchemaHandler,
    ) -> CoreSchema:
        """Wrap the value schema with the conditional check (on the raw input)."""
        return core_schema.no_info_wrap_validator_function(self._validate, handler(source_type))

    def __get_pydantic_json_schema__(
        self,
        schema: CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        """Restore the `if` / `then` / `else` keywords on dump."""
        json_schema = handler(schema)
        if_adapter = self._build_adapters()
        json_schema["if"] = if_adapter.json_schema()
        if self._then_adapter is not None:
            json_schema["then"] = self._then_adapter.json_schema()
        if self._else_adapter is not None:
            json_schema["else"] = self._else_adapter.json_schema()
        return json_schema

    def _build_adapters(self) -> TypeAdapter[AnnotationType]:
        """Build the `if` / `then` / `else` adapters on first use (caches across calls).

        :returns: The `if` adapter (always present).
        """
        if self._if_adapter is not None:
            return self._if_adapter

        if_adapter: TypeAdapter[AnnotationType] = self._build_adapter(self._if)
        self._if_adapter = if_adapter
        if self._then is not None:
            self._then_adapter = self._build_adapter(self._then)
        if self._else is not None:
            self._else_adapter = self._build_adapter(self._else)
        return if_adapter

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

        if self._validates(if_adapter, value):
            if self._then_adapter is not None and not self._validates(self._then_adapter, value):
                msg = "Value matches `if` but not `then`"
                raise ValueError(msg)
        elif self._else_adapter is not None and not self._validates(self._else_adapter, value):
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
