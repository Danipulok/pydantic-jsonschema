"""Public API for the pydantic_jsonschema package."""

from importlib.metadata import version as _metadata_version

from pydantic_jsonschema.converters import SchemaConverter, to_model
from pydantic_jsonschema.exceptions import (
    BasePydanticJsonSchemaError,
    FormatValidationError,
    SchemaConversionError,
    SchemaReferenceError,
)
from pydantic_jsonschema.schema import DataType, Reference, Schema

# NOTE: The rules API (`Rule`, matchers, actions) is intentionally not re-exported here — it lives
# only under `pydantic_jsonschema.rules` to keep the package root focused on the core surface.
__all__ = [
    "BasePydanticJsonSchemaError",
    "DataType",
    "FormatValidationError",
    "Reference",
    "Schema",
    "SchemaConversionError",
    "SchemaConverter",
    "SchemaReferenceError",
    "__version__",
    "to_model",
]

__version__ = _metadata_version("pydantic-jsonschema")
