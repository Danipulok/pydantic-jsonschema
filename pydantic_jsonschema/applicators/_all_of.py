"""JSON Schema `allOf` validator for the branches not combined as an object model.

See: https://json-schema.org/draft/2020-12/json-schema-core#section-10.2.1.1
"""

from typing import override

from pydantic import GetJsonSchemaHandler, TypeAdapter
from pydantic.json_schema import JsonSchemaValue

from ._base import AnnotationType, ObjectApplicator

__all__ = ["AllOf"]


class AllOf(ObjectApplicator):
    """Enforce JSON Schema `allOf` beside the branch that produces the value.

    Object branches combine natively, as model inheritance. Any other value is produced by one
    branch's model, so the remaining branches (and the keywords beside `allOf`) are checked here,
    against the raw input, from a `before` validator on that model.
    """

    def __init__(
        self,
        *,
        branches: dict[str, AnnotationType],
    ) -> None:
        """Initialize with the subschemas the value must also validate against.

        :param branches: Subschema annotations keyed by the label an error names them by.
        """
        super().__init__()
        self._branches: dict[str, AnnotationType] = branches
        self._adapters: dict[str, TypeAdapter[AnnotationType]] | None = None

    def _get_adapters(self) -> dict[str, TypeAdapter[AnnotationType]]:
        """Build the subschema adapters on first use (caches across calls).

        :returns: A `TypeAdapter` per subschema, keyed like the branches.
        """
        if self._adapters is None:
            self._adapters = {
                label: self._build_adapter(branch) for label, branch in self._branches.items()
            }
        return self._adapters

    @override
    def json_schema_keyword(
        self,
        handler: GetJsonSchemaHandler,
        /,
    ) -> JsonSchemaValue:
        """Return the `allOf` keyword fragment for the dumped JSON Schema."""
        return {
            "allOf": [
                self._branch_schema(adapter, handler=handler)
                for adapter in self._get_adapters().values()
            ]
        }

    @override
    def validate(
        self,
        data: AnnotationType,
        /,
    ) -> AnnotationType:
        """Validate the raw input against every subschema.

        :param data: The raw input value.
        :returns: The input unchanged when every subschema validates it.
        :raises ValueError: When a subschema does not validate the input.
        """
        for label, adapter in self._get_adapters().items():
            try:
                matches = self._validates(adapter, value=data)
            # A bound without `type` (`{"minimum": 5}` -> `Annotated[Any, Ge(5)]`) raises on a value
            #  it cannot compare, where the spec ignores the keyword: `allOf: [{"type": "string"},
            #  {"minimum": 5}]` on `"a"` raised `TypeError: Unable to apply constraint 'ge' to
            #  supplied value a`. https://json-schema.org/draft/2020-12/json-schema-validation#section-6.2
            #  This skips the whole subschema, so its other keywords go unchecked for that value.
            except TypeError:
                matches = True

            if not matches:
                msg = f"Value does not match {label}"
                raise ValueError(msg)

        return data
