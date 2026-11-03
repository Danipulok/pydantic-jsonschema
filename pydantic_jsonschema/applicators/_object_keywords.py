"""Object keywords on a schema that does not convert to an object model.

JSON Schema object keywords (`properties`, `required`, `minProperties`, ...) assert only on object
instances; every other instance passes them.
See: https://json-schema.org/draft/2020-12/json-schema-core#section-10.3.2
"""

from typing import override

from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler, TypeAdapter
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema, core_schema

from ._base import AnnotationApplicator, AnnotationType

__all__ = ["ObjectKeywords"]


class ObjectKeywords(AnnotationApplicator):
    """Validate mapping inputs against an object annotation, and pass every other input through.

    Carried by an untyped schema (`Any`) and by a `dict[str, ...]` object, whose host type cannot
    express the keywords. The object annotation only checks the input: the host type still
    produces the value. It may hold a `ForwardRef` (a `$ref` to a definition still being built),
    resolved against the bound namespace on first use.
    """

    def __init__(
        self,
        *,
        branch: AnnotationType,
    ) -> None:
        """Initialize with the object annotation every mapping input must validate against.

        :param branch: The object annotation (a model or an annotated `dict[str, ...]`).
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
        """Wrap the host schema with the object check (on the raw input)."""
        return core_schema.no_info_wrap_validator_function(self._validate, handler(source_type))

    @override
    def __get_pydantic_json_schema__(
        self,
        schema: CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        """Dump the host schema unchanged."""
        return handler(schema)

    def _get_adapter(self) -> TypeAdapter[AnnotationType]:
        """Build the object adapter on first use (caches across calls).

        :returns: A `TypeAdapter` for the object annotation.
        """
        if self._adapter is None:
            adapter = self._build_adapter(self._branch)
            adapter.rebuild(_types_namespace=self._namespace)
            self._adapter = adapter
        return self._adapter

    # Pydantic calls a wrap validator positionally.
    def _validate(  # noqa: PLR0917
        self,
        value: AnnotationType,
        handler: core_schema.ValidatorFunctionWrapHandler,
    ) -> AnnotationType:
        """Check a mapping input against the object annotation, then delegate to the host schema.

        :param value: Raw input value.
        :param handler: Wrapped host-type validator.
        :returns: The validated value.
        """
        if isinstance(value, dict):
            self._get_adapter().validate_python(value)
        return handler(value)
