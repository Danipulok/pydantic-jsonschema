"""Public API for the pydantic_jsonschema package."""

from pydantic_jsonschema._one_of import OneOf
from pydantic_jsonschema._version import __version__
from pydantic_jsonschema.converters import SchemaConverter, to_model
from pydantic_jsonschema.types import DataType, Reference, Schema

__all__ = [
    "DataType",
    "OneOf",
    "Reference",
    "Schema",
    "SchemaConverter",
    "__version__",
    "to_model",
]
