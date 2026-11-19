"""Type-specific keywords, and whether a schema's `type` pins them to their own type.

A keyword family asserts only on instances of its type, so it becomes a `Field` constraint only
when the schema's single `type` is that type; otherwise an `IfType` gate checks it.
See: https://json-schema.org/draft/2020-12/json-schema-validation#section-6
"""

from typing import Final

from pydantic_jsonschema._compat import MISSING
from pydantic_jsonschema.schema import DataType, Schema

__all__ = [
    "pins_type",
    "unpinned_keywords",
]

_KEYWORD_FIELDS: Final[dict[DataType, tuple[str, ...]]] = {
    DataType.NUMBER: (
        "minimum",
        "maximum",
        "exclusive_minimum",
        "exclusive_maximum",
        "multiple_of",
    ),
    DataType.STRING: (
        "min_length",
        "max_length",
        "pattern",
    ),
    DataType.ARRAY: (
        "items",
        "prefix_items",
        "contains",
        "min_items",
        "max_items",
        "unique_items",
        "min_contains",
        "max_contains",
    ),
}

_FAMILY_TYPES: Final[dict[DataType, frozenset[DataType]]] = {
    DataType.NUMBER: frozenset({DataType.INTEGER, DataType.NUMBER}),
    DataType.STRING: frozenset({DataType.STRING}),
    DataType.ARRAY: frozenset({DataType.ARRAY}),
}


def pins_type(
    schema: Schema,
    /,
    *,
    data_type: DataType,
) -> bool:
    """Tell whether the schema's single `type` is of the `data_type` family.

    A `type` list never pins: its union host cannot carry the keywords as `Field` constraints, nor
    dump them under their JSON Schema names.

    :param schema: Schema to inspect.
    :param data_type: `number` (with `integer`), `string` or `array`.
    :returns: `False` when the schema declares no `type` or a list of them.
    """
    return isinstance(schema.type, DataType) and schema.type in _FAMILY_TYPES[data_type]


def unpinned_keywords(schema: Schema, /) -> dict[DataType, Schema]:
    """Collect the keyword families the schema's `type` does not pin, each typed to its family.

    :param schema: Schema to inspect.
    :returns: Per family, a schema holding only its keywords and the family's `type`.
    """
    branches: dict[DataType, Schema] = {}
    for data_type, fields in _KEYWORD_FIELDS.items():
        keywords = {
            name: getattr(schema, name) for name in fields if getattr(schema, name) is not MISSING
        }

        if not keywords or pins_type(schema, data_type=data_type):
            continue

        branches[data_type] = Schema().model_copy(update={**keywords, "type": data_type})

    return branches
