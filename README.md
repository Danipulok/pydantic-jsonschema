# pydantic-jsonschema

A library for converting JSON Schema / OpenAPI schemas to Pydantic models and back.

## Features

- **Schema Conversion**: Convert JSON Schema / OpenAPI schemas to Pydantic models
- **Lax Validation**: LLM-friendly validation mode with optional fields
- **Format Validators**: Built-in validators for dates, emails, URIs, UUIDs, IPs, etc.
- **Before Validators**: Custom preprocessing/coercion support
- **Schema Dumping**: Export Pydantic models back to JSON Schema with reference support
- **Composition Support**: Handle `allOf`, `anyOf`, `oneOf`, `$refs`, and `$defs`

## Installation

```bash
pip install pydantic-jsonschema
```

## Quick Start

### Basic Conversion

```python
from pydantic_jsonschema import convert_schema
from openapi_pydantic import Schema

schema = Schema(
    type="object",
    properties={
        "name": Schema(type="string"),
        "age": Schema(type="integer"),
    },
    required=["name"],
)

Model = convert_schema(schema)
instance = Model(name="Alice", age=30)
```

### Lax Conversion for LLMs

```python
from pydantic_jsonschema import convert_schema_lax

# All fields become optional with sensible defaults
Model = convert_schema_lax(schema)
instance = Model()  # Valid! Fields default to None, lists to [], dicts to {}
```

### Schema Dumping

```python
from pydantic_jsonschema import model_dump_json_schema
from pydantic import BaseModel

class User(BaseModel):
    name: str
    age: int

schema = model_dump_json_schema(User)
```

### Custom Before Validators

```python
from pydantic_jsonschema import SchemaConverter

def str_to_int(value):
    if isinstance(value, str):
        return int(value)
    return value

converter = SchemaConverter(
    before_validators={"custom-int": str_to_int}
)

schema = Schema(
    type="object",
    properties={"age": Schema(type="integer", format="custom-int")}
)

Model = converter.convert_schema(schema)
instance = Model(age="25")  # Coerced to int(25)
```

## Format Validators

Built-in validators for JSON Schema formats:
- Date/Time: `date`, `time`, `date-time`, `duration`
- Network: `email`, `hostname`, `ipv4`, `ipv6`
- Identifiers: `uuid`, `uri`, `uri-reference`, `iri`, `iri-reference`

## Testing

```bash
pytest tests/
```

All 40 tests passing ✓