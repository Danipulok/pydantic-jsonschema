"""JSON Schema `oneOf` validator.

See: https://json-schema.org/draft/2020-12/json-schema-core#section-10.2.1.3
"""

from collections.abc import Iterable
from typing import Annotated, Union, override

from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler, TypeAdapter
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema, core_schema

from ._base import AnnotationApplicator, AnnotationType

__all__ = ["OneOf"]


class OneOf(AnnotationApplicator):
    """Enforce JSON Schema `oneOf` semantics: exactly one branch must match.

    Python `Union` accepts a value when *any* branch matches (`anyOf` semantics),
    so this wrap-validator additionally counts matching branches and rejects
    inputs that match zero or more than one branch.
    """

    def __init__(
        self,
        *,
        branches: Iterable[AnnotationType],
    ) -> None:
        """Initialize with union branch annotations.

        :param branches: Union branch annotations (may contain `ForwardRef`).
        """
        super().__init__()
        self._branches: tuple[AnnotationType, ...] = tuple(branches)
        self._adapters: list[TypeAdapter[AnnotationType]] | None = None

    def as_annotation(self) -> AnnotationType:
        """Build the field annotation: union of branches with this validator attached.

        The plain `Union` is required: it drives Pydantic coercion and serialization,
        keeps the field type honest for static checkers, and lets `model_rebuild`
        resolve `ForwardRef` branches (which only works for refs in annotations).

        :returns: `Annotated[Union[...], self]`.
        """
        union_annotation = Union[self._branches]  # type: ignore[name-defined]  # noqa: UP007
        return Annotated[union_annotation, self]

    @override
    def __get_pydantic_core_schema__(
        self,
        source_type: AnnotationType,
        handler: GetCoreSchemaHandler,
    ) -> CoreSchema:
        """Wrap the union schema with the exactly-one-branch check."""
        return core_schema.no_info_wrap_validator_function(self._validate, handler(source_type))

    @override
    def __get_pydantic_json_schema__(
        self,
        schema: CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        """Dump the union back as JSON Schema `oneOf` instead of `anyOf`."""
        json_schema = handler(schema)
        if "anyOf" in json_schema:
            json_schema["oneOf"] = json_schema.pop("anyOf")
        return json_schema

    def _get_adapters(self) -> list[TypeAdapter[AnnotationType]]:
        """Build branch adapters on first use (caches across calls).

        :returns: One `TypeAdapter` per `oneOf` branch.
        """
        if self._adapters is None:
            self._adapters = [self._build_adapter(branch) for branch in self._branches]
        return self._adapters

    def _validate(
        self,
        value: AnnotationType,
        handler: core_schema.ValidatorFunctionWrapHandler,
    ) -> AnnotationType:
        """Count matching branches and delegate to the union schema.

        :param value: Raw input value.
        :param handler: Wrapped union validator.
        :returns: Validated value.
        :raises ValueError: If the value does not match exactly one branch.
        """
        matched_count: int = sum(
            1 for adapter in self._get_adapters() if self._validates(adapter, value=value)
        )

        if matched_count != 1:
            msg = f"Input matches {matched_count} `oneOf` branches, expected exactly 1"
            raise ValueError(msg)

        return handler(value)
