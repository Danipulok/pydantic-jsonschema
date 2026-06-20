"""JSON Schema `contains` validator.

See: https://json-schema.org/draft/2020-12/json-schema-core#section-10.3.1.3
"""

from typing import Any, ForwardRef

from pydantic import (
    BaseModel,
    GetCoreSchemaHandler,
    TypeAdapter,
    ValidationError,
)
from pydantic_core import CoreSchema, core_schema

__all__ = ["Contains"]

# Type aliases
type AnnotationType = (
    Any  # Any annotation Pydantic supports (`type`, `Annotated`, `ForwardRef`, ...)
)


class Contains:
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
        self._branch: AnnotationType = branch
        self._min_contains: int = min_contains
        self._max_contains: int | None = max_contains
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
        """Wrap the array schema with the match-count check."""
        return core_schema.no_info_after_validator_function(self._validate, handler(source_type))

    def _get_adapter(self) -> TypeAdapter[AnnotationType]:
        """Build the `contains` adapter, resolving a `ForwardRef` subschema on first use.

        :returns: A `TypeAdapter` for the `contains` subschema.
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

    def _matches(
        self,
        item: AnnotationType,
        /,
    ) -> bool:
        """Return whether a single element validates against the `contains` subschema.

        :param item: An array element (already parsed by the array's item type).
        :returns: `True` when the element validates against `contains`.
        """
        try:
            self._get_adapter().validate_python(item)
        except ValidationError:
            return False
        return True

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
