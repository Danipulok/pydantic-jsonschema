"""JSON Schema `prefixItems` validator.

See: https://json-schema.org/draft/2020-12/json-schema-core#section-10.3.1.1
"""

from collections.abc import Iterable
from typing import override

from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler, TypeAdapter, ValidationError
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema, core_schema

from ._base import AnnotationApplicator, AnnotationType

__all__ = ["PrefixItems"]


class PrefixItems(AnnotationApplicator):
    """Enforce JSON Schema `prefixItems`: positional (tuple-style) array validation.

    Element `i` is validated against `prefixItems[i]`; elements past the prefix are validated
    against the array's `items` schema (the 2020-12 tail), or left unconstrained when `items`
    is absent. Attached as `Annotated` metadata on a `list[Any]` base; prefix / tail subschemas
    may be `ForwardRef` (pointing at a `$ref`), resolved lazily via `bind_namespace`.
    """

    def __init__(
        self,
        *,
        prefixes: Iterable[AnnotationType],
        tail: AnnotationType | None,
    ) -> None:
        """Initialize with the positional subschema annotations and the tail schema.

        :param prefixes: One annotation per `prefixItems` entry (each may be a `ForwardRef`).
        :param tail: The `items` annotation for elements past the prefix, or `None` when `items`
            is absent (extra elements are then unconstrained).
        """
        super().__init__()

        self._prefixes: tuple[AnnotationType, ...] = tuple(prefixes)
        self._tail: AnnotationType | None = tail
        self._prefix_adapters: list[TypeAdapter[AnnotationType]] | None = None
        self._tail_adapter: TypeAdapter[AnnotationType] | None = None

    @override
    def __get_pydantic_core_schema__(
        self,
        source_type: AnnotationType,
        handler: GetCoreSchemaHandler,
    ) -> CoreSchema:
        """Wrap the array schema with positional validation."""
        return core_schema.no_info_after_validator_function(self._validate, handler(source_type))

    @override
    def __get_pydantic_json_schema__(
        self,
        schema: CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        """Restore the `prefixItems` (and tail `items`) keywords on dump."""
        json_schema = handler(schema)
        self._build_adapters()

        json_schema["prefixItems"] = [
            self._branch_schema(adapter, handler=handler) for adapter in self._prefix_adapters or []
        ]
        if self._tail_adapter is not None:
            json_schema["items"] = self._branch_schema(self._tail_adapter, handler=handler)

        return json_schema

    def _build_adapters(self) -> None:
        """Build the per-position and tail adapters on first use (caches across calls)."""
        if self._prefix_adapters is None:
            self._prefix_adapters = [self._build_adapter(branch) for branch in self._prefixes]
            if self._tail is not None:
                self._tail_adapter = self._build_adapter(self._tail)

    def _validate(
        self,
        value: AnnotationType,
    ) -> AnnotationType:
        """Validate each element against its positional subschema.

        :param value: The validated array.
        :returns: The array with each element validated (and coerced) by its position's schema.
        :raises ValueError: When an element does not match its `prefixItems` / `items` schema.
        """
        self._build_adapters()
        prefix_adapters = self._prefix_adapters or []

        result: list[AnnotationType] = []
        for index, item in enumerate(value):
            adapter: TypeAdapter[AnnotationType] | None
            if index < len(prefix_adapters):
                adapter = prefix_adapters[index]
                keyword = "prefixItems"
            else:
                adapter = self._tail_adapter
                keyword = "items"

            # Past the prefix with no `items` schema: the element is unconstrained.
            if adapter is None:
                result.append(item)
                continue

            try:
                result.append(adapter.validate_python(item))
            except ValidationError:
                msg = f"Item at index `{index}` does not match the `{keyword}` schema"
                raise ValueError(msg) from None

        return result
