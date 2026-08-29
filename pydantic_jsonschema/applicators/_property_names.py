"""JSON Schema `propertyNames` validator.

See: https://json-schema.org/draft/2020-12/json-schema-core#section-10.3.2.4
"""

from typing import override

from pydantic import TypeAdapter
from pydantic.json_schema import JsonSchemaValue

from ._base import AnnotationType, ObjectApplicator

__all__ = ["PropertyNames"]


class PropertyNames(ObjectApplicator):
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
        super().__init__()
        self._branch: AnnotationType = branch
        self._adapter: TypeAdapter[AnnotationType] | None = None

    def _get_adapter(self) -> TypeAdapter[AnnotationType]:
        """Build the subschema adapter on first use (caches across calls).

        :returns: A `TypeAdapter` for the `propertyNames` subschema.
        """
        if self._adapter is None:
            self._adapter = self._build_adapter(self._branch)
        return self._adapter

    @override
    def json_schema_keyword(self) -> JsonSchemaValue:
        """Return the `propertyNames` keyword fragment for the dumped JSON Schema."""
        return {"propertyNames": self._get_adapter().json_schema()}

    @override
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
            if not self._validates(adapter, value=name):
                msg = f"Property name `{name}` does not satisfy the `propertyNames` schema"
                raise ValueError(msg)

        return data
