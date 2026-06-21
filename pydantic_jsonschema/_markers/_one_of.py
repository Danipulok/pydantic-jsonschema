"""JSON Schema `oneOf` validator.

See: https://json-schema.org/draft/2020-12/json-schema-core#section-10.2.1.3
"""

from collections.abc import Iterable
from typing import Annotated, Any, ForwardRef, Union

from pydantic import (
    BaseModel,
    GetCoreSchemaHandler,
    GetJsonSchemaHandler,
    TypeAdapter,
    ValidationError,
)
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema, core_schema

__all__ = ["OneOf"]

# Type aliases
type AnnotationType = (
    Any  # Any annotation Pydantic supports (`type`, `Annotated`, `ForwardRef`, ...)
)


class OneOf:
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
        self._branches: tuple[AnnotationType, ...] = tuple(branches)
        self._namespace: dict[str, type[BaseModel]] = {}
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

    def bind_namespace(
        self,
        namespace: dict[str, type[BaseModel]],
        /,
    ) -> None:
        """Provide the namespace used to resolve `ForwardRef` branches.

        :param namespace: Mapping of sanitized reference names to models.
        """
        self._namespace = namespace

    def __get_pydantic_core_schema__(
        self,
        source_type: AnnotationType,
        handler: GetCoreSchemaHandler,
    ) -> CoreSchema:
        """Wrap the union schema with the exactly-one-branch check."""
        return core_schema.no_info_wrap_validator_function(self._validate, handler(source_type))

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
        """Build branch adapters, resolving `ForwardRef` branches on first use.

        :returns: One `TypeAdapter` per `oneOf` branch.
        """
        # NOTE: Adapters are built lazily: at conversion time branches may contain
        #       `ForwardRef` entries that only become resolvable after the whole
        #       schema (including `$defs`) has been converted and the namespace
        #       has been bound via `bind_namespace`.
        if self._adapters is None:
            resolved_branches = [
                self._namespace[branch.__forward_arg__]
                if isinstance(branch, ForwardRef)
                else branch
                for branch in self._branches
            ]
            self._adapters = [TypeAdapter(branch) for branch in resolved_branches]
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
        matched_count: int = 0
        for adapter in self._get_adapters():
            try:
                adapter.validate_python(value)
            except ValidationError:
                continue
            else:
                matched_count += 1

        if matched_count != 1:
            msg = f"Input matches {matched_count} `oneOf` branches, expected exactly 1"
            raise ValueError(msg)

        return handler(value)
