"""Public API for the pydantic_jsonschema package."""

from importlib.metadata import version as _metadata_version

from pydantic_jsonschema.converters import SchemaConverter, to_model
from pydantic_jsonschema.exceptions import (
    BasePydanticJsonSchemaError,
    FormatValidationError,
    SchemaConversionError,
    SchemaReferenceError,
)
from pydantic_jsonschema.rules import (
    After,
    Before,
    ByFunc,
    ByPath,
    ByType,
    Dump,
    MatchContext,
    Override,
    Rule,
)
from pydantic_jsonschema.schema import DataType, Reference, Schema

__all__ = [
    "After",
    "BasePydanticJsonSchemaError",
    "Before",
    "ByFunc",
    "ByPath",
    "ByType",
    "DataType",
    "Dump",
    "FormatValidationError",
    "MatchContext",
    "Override",
    "Reference",
    "Rule",
    "Schema",
    "SchemaConversionError",
    "SchemaConverter",
    "SchemaReferenceError",
    "__version__",
    "to_model",
]

__version__ = _metadata_version("pydantic-jsonschema")
