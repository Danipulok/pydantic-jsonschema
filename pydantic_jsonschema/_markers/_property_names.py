"""JSON Schema `propertyNames` validator.

See: https://json-schema.org/draft/2020-12/json-schema-core#section-10.3.2.4
"""

from typing import ForwardRef

from pydantic import (
    BaseModel,
    TypeAdapter,
    ValidationError,
)

from pydantic_jsonschema._types import AnnotationType

__all__ = ["PropertyNames"]


class PropertyNames:
    """Enforce JSON Schema `propertyNames`: every property name must match the subschema.

    Property names are always strings, so the subschema typically constrains the string (a
    `pattern`, `maxLength`, `enum`, ...). Used from a `before` model validator on object models;
    the subschema may be a `ForwardRef` (pointing at a `$ref`), resolved lazily via
    `bind_namespace`.
    """

    def __init__(
        self,
        *,
        branch: AnnotationType,
    ) -> None:
        """Initialize with the `propertyNames` subschema annotation.

        :param branch: The subschema every property name must validate against (may be a
            `ForwardRef`).
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

    def _get_adapter(self) -> TypeAdapter[AnnotationType]:
        """Build the subschema adapter, resolving a `ForwardRef` on first use.

        :returns: A `TypeAdapter` for the `propertyNames` subschema.
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

    def validate(
        self,
        data: AnnotationType,
        /,
    ) -> AnnotationType:
        """Validate every property name against the subschema.

        :param data: The raw input mapping (other input is left for type validation to reject).
        :returns: The input unchanged when every name validates.
        :raises ValueError: When a property name does not validate against the subschema.
        """
        if not isinstance(data, dict):
            return data

        adapter = self._get_adapter()
        for name in data:
            try:
                adapter.validate_python(name)
            except ValidationError:
                msg = f"Property name `{name}` does not satisfy the `propertyNames` schema"
                raise ValueError(msg) from None

        return data
