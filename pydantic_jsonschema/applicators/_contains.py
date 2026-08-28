"""JSON Schema `contains` validator.

See: https://json-schema.org/draft/2020-12/json-schema-core#section-10.3.1.3
"""

from typing import Final, override

from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler, TypeAdapter
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema, core_schema

from ._base import AnnotationApplicator, AnnotationType

__all__ = ["Contains"]

# `minContains` defaults to 1, so it is only re-emitted when it differs.
_DEFAULT_MIN_CONTAINS: Final[int] = 1


class Contains(AnnotationApplicator):
    """Enforce JSON Schema `contains` / `minContains` / `maxContains` on an array.

    Counts how many array elements validate against the `contains` subschema and requires that
    count to stay within `[min_contains, max_contains]`. Attached as `Annotated` metadata on the
    array's `list[...]` annotation; the subschema may be a `ForwardRef` resolved lazily via
    `bind_namespace` (a `contains` that points at a `$ref`).
    """

    def __init__(
        self,
        *,
        branch: AnnotationType,
        min_contains: int,
        max_contains: int | None,
    ) -> None:
        """Initialize with the `contains` subschema annotation and the match-count bounds.

        :param branch: The `contains` subschema annotation (may be a `ForwardRef`).
        :param min_contains: Minimum number of matching elements (`minContains`, default 1).
        :param max_contains: Maximum number of matching elements (`maxContains`), or `None`.
        """
        super().__init__()

        self._branch: AnnotationType = branch
        self._min_contains: int = min_contains
        self._max_contains: int | None = max_contains
        self._adapter: TypeAdapter[AnnotationType] | None = None

    @override
    def __get_pydantic_core_schema__(
        self,
        source_type: AnnotationType,
        handler: GetCoreSchemaHandler,
    ) -> CoreSchema:
        """Wrap the array schema with the match-count check."""
        return core_schema.no_info_after_validator_function(self._validate, handler(source_type))

    @override
    def __get_pydantic_json_schema__(
        self,
        schema: CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        """Restore the `contains` / `minContains` / `maxContains` keywords on dump."""
        json_schema = handler(schema)

        json_schema["contains"] = self._get_adapter().json_schema()
        if self._min_contains != _DEFAULT_MIN_CONTAINS:
            json_schema["minContains"] = self._min_contains
        if self._max_contains is not None:
            json_schema["maxContains"] = self._max_contains

        return json_schema

    def _get_adapter(self) -> TypeAdapter[AnnotationType]:
        """Build the `contains` adapter on first use (caches across calls).

        :returns: A `TypeAdapter` for the `contains` subschema.
        """
        if self._adapter is None:
            self._adapter = self._build_adapter(self._branch)
        return self._adapter

    def _matches(
        self,
        item: AnnotationType,
        /,
    ) -> bool:
        """Return whether a single element validates against the `contains` subschema.

        :param item: An array element (already parsed by the array's item type).
        :returns: `True` when the element validates against `contains`.
        """
        return self._validates(self._get_adapter(), value=item)

    def _validate(
        self,
        value: AnnotationType,
    ) -> AnnotationType:
        """Count matching elements and enforce the `contains` bounds.

        :param value: The validated array.
        :returns: The array unchanged when the match count is within bounds.
        :raises ValueError: When too few or too many elements match `contains`.
        """
        matched: int = sum(1 for item in value if self._matches(item))

        if matched < self._min_contains:
            msg = f"Array must contain at least `{self._min_contains}` matches, got `{matched}`"
            raise ValueError(msg)
        if self._max_contains is not None and matched > self._max_contains:
            msg = f"Array must contain at most `{self._max_contains}` matches, got `{matched}`"
            raise ValueError(msg)

        return value
