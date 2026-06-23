"""Public API for the pydantic_jsonschema package."""

from importlib.metadata import version as _metadata_version

from pydantic_jsonschema.converters import SchemaConverter, to_model
from pydantic_jsonschema.schema import DataType, Reference, Schema

__all__ = [
    "DataType",
    "Reference",
    "Schema",
    "SchemaConverter",
    "__version__",
    "to_model",
]

__version__ = _metadata_version("pydantic-jsonschema")
