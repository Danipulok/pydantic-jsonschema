"""JSON Schema `dependentSchemas` validator.

See: https://json-schema.org/draft/2020-12/json-schema-core#section-10.2.2.4
"""

from pydantic import TypeAdapter

from ._base import AnnotationType, Applicator

__all__ = ["DependentSchemas"]


class DependentSchemas(Applicator):
    """Enforce JSON Schema `dependentSchemas`: a present property triggers a whole-object schema.

    For each `{property: subschema}` pair, when the property is present in the object the entire
    instance must also validate against the subschema. Used from a `before` model validator on
    object models; subschemas may be `ForwardRef` (pointing at a `$ref`), resolved lazily via
    `bind_namespace`.
    """

    def __init__(
        self,
        *,
        branches: dict[str, AnnotationType],
    ) -> None:
        """Initialize with the property-to-subschema mapping.

        :param branches: Mapping of trigger property name to its subschema annotation (each may
            be a `ForwardRef`).
        """
        super().__init__()
        self._branches: dict[str, AnnotationType] = dict(branches)
        self._adapters: dict[str, TypeAdapter[AnnotationType]] | None = None

    def _get_adapters(self) -> dict[str, TypeAdapter[AnnotationType]]:
        """Build the per-trigger adapters on first use (caches across calls).

        :returns: Mapping of trigger property name to its subschema `TypeAdapter`.
        """
        if self._adapters is None:
            self._adapters = {
                trigger: self._build_adapter(branch) for trigger, branch in self._branches.items()
            }
        return self._adapters

    def validate(
        self,
        data: AnnotationType,
        /,
    ) -> AnnotationType:
        """Apply each triggered subschema to the whole instance.

        :param data: The raw input mapping (other input is left for type validation to reject).
        :returns: The input unchanged when every triggered subschema validates.
        :raises ValueError: When a present property's subschema does not validate the instance.
        """
        if not isinstance(data, dict):
            return data

        for trigger, adapter in self._get_adapters().items():
            if trigger not in data:
                continue
            if not self._validates(adapter, data):
                msg = f"Property `{trigger}` does not satisfy its `dependentSchemas` schema"
                raise ValueError(msg)

        return data
