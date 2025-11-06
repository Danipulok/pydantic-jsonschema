"""
pydantic-jsonschema: JSON Schema to Pydantic model conversion library.

Main features:
- Convert JSON Schema / OpenAPI schemas to Pydantic models
- Support for $defs, allOf, anyOf, oneOf, references
- Custom format validators
- Lax conversion for LLM-friendly validation
- Schema dumping with references
"""

from pydantic_jsonschema.converters import (
    SchemaConverter,
    convert_schema,
)
from pydantic_jsonschema.lax import (
    LaxSchemaConverter,
    convert_schema_lax,
)
from pydantic_jsonschema.schema import (
    model_dump_json_schema,
)
from pydantic_jsonschema.exceptions import (
    ParsingError,
    ReferenceError,
    SchemaError,
)
from pydantic_jsonschema.formats import (
    DATE,
    DATE_TIME,
    DURATION,
    EMAIL,
    HOSTNAME,
    IPV_4,
    IPV_6,
    IRI,
    IRI_REFERENCE,
    ISO_4217,
    ISO_639_1_ALPHA_2,
    TIME,
    URI,
    URI_REFERENCE,
    UUID,
    SchemaFormat,
)
from pydantic_jsonschema.utils import sanitize_identifier

__version__ = "0.1.0"

__all__ = [
    # Version
    "__version__",
    # Converters
    "SchemaConverter",
    "convert_schema",
    "LaxSchemaConverter",
    "convert_schema_lax",
    # Schema dumping
    "model_dump_json_schema",
    # Exceptions
    "SchemaError",
    "ParsingError",
    "ReferenceError",
    # Formats
    "SchemaFormat",
    "DATE",
    "TIME",
    "DATE_TIME",
    "DURATION",
    "EMAIL",
    "HOSTNAME",
    "IPV_4",
    "IPV_6",
    "UUID",
    "URI",
    "URI_REFERENCE",
    "IRI",
    "IRI_REFERENCE",
    "ISO_4217",
    "ISO_639_1_ALPHA_2",
    # Utils
    "sanitize_identifier",
]
