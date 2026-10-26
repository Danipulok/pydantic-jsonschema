"""Stateless object-keyword checks, and the metadata that runs them on a `dict`.

Each builder turns one object-level keyword into a check of the raw input mapping (`None` when the
keyword is absent). These keywords need no subschema conversion, so they are plain functions; the
converter-aware ones (`dependentSchemas` / `patternProperties` / `propertyNames`) stay on the
`SchemaConverter`. A model runs the checks as `before` model validators; an object mapped to
`dict[str, ...]` runs them, and its object applicators, through `DictKeywords`.
"""

# NOTE: `Schema` fields use `X | MISSING` unions (see `schema/_models.py`). mypy doesn't
#  recognize `MISSING` as a type, so it infers fields without the `Sentinel` branch
#  and flags every `is not MISSING` check as a non-overlapping identity comparison.
# mypy: disable-error-code="comparison-overlap"

from collections.abc import Sequence
from typing import Annotated, Any, Protocol, get_args, get_origin

from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema, core_schema

from pydantic_jsonschema._compat import MISSING
from pydantic_jsonschema.applicators import ObjectApplicator
from pydantic_jsonschema.schema import Schema

from ._utils import unwrap

__all__ = [
    "DictKeywords",
    "ObjectCheck",
    "build_dependent_required",
    "build_property_count_bounds",
    "build_undeclared_required",
    "merge_keyword",
    "strip_dict_keywords",
]

type PythonType = Any


class ObjectCheck(Protocol):
    """A check of the raw input mapping, returning it unchanged or raising `ValueError`."""

    def __call__(self, data: PythonType, /) -> PythonType: ...


def build_property_count_bounds(schema: Schema, /) -> ObjectCheck | None:
    """`minProperties` / `maxProperties`: bound the number of properties of an object model.

    Counts the raw input mapping's keys before field parsing. That key count is exactly the
    JSON Schema "number of properties" (declared fields plus `extra` keys) and is unambiguous
    regardless of which keys map to declared fields (validation §6.5.1 / §6.5.2).

    :param schema: Object schema.
    :returns: The check, or `None` when neither bound is set.
    """
    min_properties = unwrap(schema.min_properties, default=None)
    max_properties = unwrap(schema.max_properties, default=None)
    if min_properties is None and max_properties is None:
        return None

    def _check(data: PythonType) -> PythonType:
        # Non-mapping input is left for the normal type validation to reject.
        if not isinstance(data, dict):
            return data

        count: int = len(data)
        if min_properties is not None and count < min_properties:
            msg = f"Object must have at least `{min_properties}` properties"
            raise ValueError(msg)
        if max_properties is not None and count > max_properties:
            msg = f"Object must have at most `{max_properties}` properties"
            raise ValueError(msg)

        return data

    return _check


def build_dependent_required(schema: Schema, /) -> ObjectCheck | None:
    """`dependentRequired`: when a property is present, the listed properties are required too.

    Checks the raw input mapping keys before field parsing, so it sees every present property
    (declared fields plus `extra` keys) (validation §6.5.4).

    :param schema: Object schema.
    :returns: The check, or `None` when the keyword is absent.
    """
    if schema.dependent_required is MISSING:
        return None

    dependent_required: dict[str, list[str]] = schema.dependent_required

    def _check(data: PythonType) -> PythonType:
        # Non-mapping input is left for the normal type validation to reject.
        if not isinstance(data, dict):
            return data

        for trigger, required in dependent_required.items():
            if trigger not in data:
                continue
            missing = [name for name in required if name not in data]
            if missing:
                missing_list = "`, `".join(missing)
                msg = f"Property `{trigger}` requires `{missing_list}`"
                raise ValueError(msg)

        return data

    return _check


def build_undeclared_required(schema: Schema, /) -> ObjectCheck | None:
    """Require the keys that `required` names but `properties` does not declare.

    A declared property is required through its field; an undeclared one has no field, so the raw
    input mapping is checked for the key (validation §6.5.3).

    :param schema: Object schema.
    :returns: The check, or `None` when every required property is declared.
    """
    declared: dict[str, Any] = unwrap(schema.properties, default={})
    undeclared = [name for name in unwrap(schema.required, default=[]) if name not in declared]
    if not undeclared:
        return None

    def _check(data: PythonType) -> PythonType:
        # Non-mapping input is left for the normal type validation to reject.
        if not isinstance(data, dict):
            return data

        missing = [name for name in undeclared if name not in data]
        if missing:
            missing_list = "`, `".join(missing)
            msg = f"Object must have the properties `{missing_list}`"
            raise ValueError(msg)

        return data

    return _check


class DictKeywords:
    """`Annotated` metadata running object keyword checks and applicators on a `dict` mapping.

    A `dict[str, ...]` annotation carries no `required`, `dependentRequired`, `dependentSchemas`,
    `propertyNames` or `patternProperties`, so this metadata checks the raw mapping before the
    `dict` validation and adds those keywords to the dumped JSON Schema.
    """

    def __init__(
        self,
        *,
        checks: Sequence[ObjectCheck],
        applicators: Sequence[ObjectApplicator],
        keywords: JsonSchemaValue,
    ) -> None:
        """Store what to run and emit.

        :param checks: Checks of the raw mapping.
        :param applicators: Object applicators run on the raw mapping.
        :param keywords: Keywords without an applicator, emitted into the dump as they are.
        """
        self._checks: tuple[ObjectCheck, ...] = tuple(checks)
        self._applicators: tuple[ObjectApplicator, ...] = tuple(applicators)
        self._keywords: JsonSchemaValue = keywords

    # Pydantic calls both hooks positionally.
    def __get_pydantic_core_schema__(  # noqa: PLR0917
        self,
        source_type: PythonType,
        handler: GetCoreSchemaHandler,
    ) -> CoreSchema:
        """Run the checks before the `dict` validation."""
        return core_schema.no_info_before_validator_function(self._validate, handler(source_type))

    def __get_pydantic_json_schema__(  # noqa: PLR0917
        self,
        schema: CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        """Add the checked keywords to the `dict` JSON Schema."""
        json_schema = merge_keyword(handler(schema), keyword=self._keywords)
        for applicator in self._applicators:
            json_schema = merge_keyword(
                json_schema,
                keyword=applicator.json_schema_keyword(handler),
            )

        return json_schema

    def _validate(self, data: PythonType, /) -> PythonType:
        for check in self._checks:
            data = check(data)

        for applicator in self._applicators:
            data = applicator.validate(data)

        return data


def merge_keyword(
    json_schema: JsonSchemaValue,
    /,
    *,
    keyword: JsonSchemaValue,
) -> JsonSchemaValue:
    """Add a keyword fragment to a JSON Schema without overwriting.

    A model wrapped twice can emit the same keyword twice (an inner and an outer `not`); the later
    fragment then goes under `allOf`, which keeps both in force.

    :param json_schema: The JSON Schema.
    :param keyword: The fragment to add.
    :returns: The JSON Schema carrying the fragment.
    """
    if keyword.keys().isdisjoint(json_schema.keys()):
        return {**json_schema, **keyword}

    if keyword.keys() == {"allOf"} and "allOf" in json_schema:
        return {**json_schema, "allOf": [*json_schema["allOf"], *keyword["allOf"]]}

    return {"allOf": [json_schema, keyword]}


def strip_dict_keywords(annotation: PythonType, /) -> PythonType:
    """Return the `dict` annotation under a `DictKeywords`, so a rule matches it by type.

    :param annotation: A node's annotation.
    :returns: The `dict[str, ...]` when `DictKeywords` is its only metadata, else `annotation`.
    """
    if get_origin(annotation) is not Annotated:
        return annotation

    origin, *metadata = get_args(annotation)
    if not all(isinstance(item, DictKeywords) for item in metadata):
        return annotation

    return origin
