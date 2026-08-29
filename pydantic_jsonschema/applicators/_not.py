"""JSON Schema `not` validator.

See: https://json-schema.org/draft/2020-12/json-schema-core#section-10.2.1.4
"""

from typing import override

from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler, TypeAdapter
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema, core_schema

from ._base import AnnotationApplicator, AnnotationType, ObjectApplicator

__all__ = ["Not"]


class Not(AnnotationApplicator, ObjectApplicator):
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
        super().__init__()
        self._branch: AnnotationType = branch
        self._adapter: TypeAdapter[AnnotationType] | None = None

    @override
    def __get_pydantic_core_schema__(
        self,
        source_type: AnnotationType,
        handler: GetCoreSchemaHandler,
    ) -> CoreSchema:
        """Wrap the value schema with the `not` check (on the raw input)."""
        return core_schema.no_info_wrap_validator_function(self._validate, handler(source_type))

    @override
    def __get_pydantic_json_schema__(
        self,
        schema: CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        """Restore the `not` keyword on dump (the wrap-validator drops it otherwise)."""
        json_schema = handler(schema)
        json_schema.update(self.json_schema_keyword(handler))
        return json_schema

    @override
    def json_schema_keyword(
        self,
        handler: GetJsonSchemaHandler,
        /,
    ) -> JsonSchemaValue:
        """Return the `not` keyword fragment for the dumped JSON Schema."""
        return {"not": self._branch_schema(self._get_adapter(), handler=handler)}

    def matches(
        self,
        value: AnnotationType,
        /,
    ) -> bool:
        """Return whether a value validates against the `not` subschema.

        :param value: The raw input value.
        :returns: `True` when the value validates against `not` (and so must be rejected).
        """
        return self._validates(self._get_adapter(), value=value)

    @override
    def validate(
        self,
        value: AnnotationType,
        /,
    ) -> AnnotationType:
        """Reject inputs matching the `not` subschema (whole-value assertion on the raw input).

        :param value: The raw input value.
        :returns: The value unchanged when it does not match the `not` subschema.
        :raises ValueError: When the value matches the `not` subschema.
        """
        if self.matches(value):
            msg = "Value must not match the `not` schema"
            raise ValueError(msg)
        return value

    def _get_adapter(self) -> TypeAdapter[AnnotationType]:
        """Build the `not` adapter on first use (caches across calls).

        :returns: A `TypeAdapter` for the `not` subschema.
        """
        if self._adapter is None:
            self._adapter = self._build_adapter(self._branch)
        return self._adapter

    def _validate(
        self,
        value: AnnotationType,
        handler: core_schema.ValidatorFunctionWrapHandler,
    ) -> AnnotationType:
        """Run the `not` check, then delegate to the host schema.

        :param value: Raw input value.
        :param handler: Wrapped host-type validator.
        :returns: The validated value.
        :raises ValueError: When the value matches the `not` subschema.
        """
        self.validate(value)
        return handler(value)
