"""Public type exports."""

from pydantic_jsonschema._schema import (
    DataType,
    Reference,
    Schema,
)

__all__ = [
    "DataType",
    "JsonType",
    "Reference",
    "Schema",
]


type JsonType = str | int | float | bool | None | list["JsonType"] | dict[str, "JsonType"]
