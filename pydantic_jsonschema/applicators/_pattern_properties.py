"""JSON Schema `patternProperties` validator.

See: https://json-schema.org/draft/2020-12/json-schema-core#section-10.3.2.2
"""

import re
from typing import override

from pydantic import TypeAdapter
from pydantic.json_schema import JsonSchemaValue

from ._base import AnnotationType, ObjectApplicator

__all__ = ["PatternProperties"]


class PatternProperties(ObjectApplicator):
    """Enforce JSON Schema `patternProperties`: regex-keyed property-value subschemas.

    Every property whose name matches a regex must have a value validating against that regex's
    subschema (a name may match several patterns, and must then satisfy all of them). Used from a
    `before` model validator on object models; subschemas may be `ForwardRef` (pointing at a
    `$ref`), resolved lazily via `bind_namespace`.
    """

    def __init__(
        self,
        *,
        branches: dict[str, AnnotationType],
    ) -> None:
        """Initialize with the pattern-to-subschema mapping.

        :param branches: Mapping of regex (`patternProperties` key) to its value subschema
            annotation (each may be a `ForwardRef`).
        """
        super().__init__()
        self._branches: dict[str, AnnotationType] = dict(branches)
        self._compiled: list[tuple[re.Pattern[str], TypeAdapter[AnnotationType]]] | None = None

    def _get_compiled(self) -> list[tuple[re.Pattern[str], TypeAdapter[AnnotationType]]]:
        """Compile the patterns and build the value adapters on first use (caches across calls).

        :returns: A list of `(compiled regex, value adapter)` pairs.
        """
        if self._compiled is None:
            self._compiled = [
                (re.compile(pattern), self._build_adapter(branch))
                for pattern, branch in self._branches.items()
            ]
        return self._compiled

    @override
    def json_schema_keyword(self) -> JsonSchemaValue:
        """Return the `patternProperties` keyword fragment for the dumped JSON Schema."""
        return {
            "patternProperties": {
                pattern.pattern: adapter.json_schema() for pattern, adapter in self._get_compiled()
            }
        }

    @override
    def validate(
        self,
        data: AnnotationType,
        /,
    ) -> AnnotationType:
        """Validate every matching property's value against its pattern's subschema.

        :param data: The raw input mapping (other input is left for type validation to reject).
        :returns: The input unchanged when every matched value validates.
        :raises ValueError: When a matching property's value does not validate.
        """
        if not isinstance(data, dict):
            return data

        for name, value in data.items():
            for pattern, adapter in self._get_compiled():
                # ECMA-262 `patternProperties` is unanchored; `re.search` matches anywhere.
                if not pattern.search(str(name)):
                    continue
                if not self._validates(adapter, value):
                    msg = f"Property `{name}` does not satisfy its `patternProperties` schema"
                    raise ValueError(msg)

        return data
