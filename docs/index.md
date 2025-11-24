# Pydantic JSON Schema

Convert JSON Schema to type-safe Pydantic models.

---

While Pydantic can generate JSON Schema from models, **Pydantic JSON Schema does the reverse** — it takes JSON Schema definitions and creates fully typed Pydantic models with validation.

This is particularly useful when:

- You have existing JSON Schema definitions (OpenAPI specs, configuration schemas)
- You need to validate LLM outputs against predefined structures
- You're building tools that consume JSON Schema

## Installation

```bash
uv add pydantic-jsonschema
```

Requires Python 3.12+

[Full installation guide](install.md)

## Hello World

Convert a simple JSON Schema to a Pydantic model:

```python
from pydantic_jsonschema import Schema, to_model

# Define your schema
schema = Schema.model_validate({
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "age": {"type": "integer", "minimum": 0}
    },
    "required": ["name"]
})

# Convert to Pydantic model
User = to_model(schema, model_name="User")

# Use it like any Pydantic model
user = User(name="Alice", age=30)
print(user.model_dump_json())
#> {"name":"Alice","age":30}
```

*This example is complete and can be run as-is.*

## Working with LLM Outputs

LLMs often return data with incorrect types (strings instead of numbers, etc.). Use lax validation for automatic type coercion:

```python
from pydantic_jsonschema import Schema, to_lax_model

schema = Schema.model_validate({
    "type": "object",
    "properties": {
        "sentiment": {"type": "string", "enum": ["positive", "negative", "neutral"]},
        "confidence": {"type": "number"},
        "keywords": {"type": "array", "items": {"type": "string"}}
    },
    "required": ["sentiment", "confidence"]
})

Analysis = to_lax_model(schema, model_name="Analysis")

# LLM returns everything as strings
llm_output = {
    "sentiment": "positive",
    "confidence": "0.87",  # String, not number
    "keywords": '["happy", "great"]',  # String, not array
}

# Lax validation coerces to correct types
analysis = Analysis.model_validate(llm_output)
print(analysis.confidence)
#> 0.87
print(analysis.keywords)
#> ['happy', 'great']
```

*This example is complete and can be run as-is.*

[Learn more about lax validation](lax.md)

## Schema References

Handle complex schemas with `$ref` and `$defs`:

```python
from pydantic_jsonschema import Schema, to_model

schema = Schema.model_validate({
    "type": "object",
    "properties": {
        "author": {"$ref": "#/$defs/Person"}
    },
    "$defs": {
        "Person": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "email": {"type": "string", "format": "email"}
            },
            "required": ["name"]
        }
    }
})

BlogPost = to_model(schema, model_name="BlogPost")
```

*This example is complete and can be run as-is.*

References are resolved automatically, creating nested Pydantic models.

[See advanced examples](examples.md)

## Key Features

**Model Conversion** — JSON Schema becomes a proper Pydantic model with all restrictions enforced

**Lax Mode** — Type coercion for flexible validation of external data sources (LLMs, CSVs, APIs)

**Custom Formats** — Extend with validators for email, UUID, dates, or custom formats

**Standards Compliant** — Fully follows and supports all specifications from [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12/json-schema-core)

## Next Steps

- [Installation](install.md) — Installation and setup
- [Converters](converters.md) — Convert schemas and choose validation mode
- [Format Validators](formats.md) — Email, UUID, dates, and custom formats
- [Examples](examples.md) — Real-world use cases
- [Contributing](contributing.md) — Help improve the library
