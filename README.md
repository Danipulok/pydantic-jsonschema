# Pydantic JSON Schema

[![CI](https://github.com/danipulok/pydantic-jsonschema/workflows/CI/badge.svg)](https://github.com/danipulok/pydantic-jsonschema/actions)
[![Coverage](https://img.shields.io/codecov/c/github/danipulok/pydantic-jsonschema)](https://codecov.io/gh/danipulok/pydantic-jsonschema)
[![PyPI](https://img.shields.io/pypi/v/pydantic-jsonschema.svg)](https://pypi.org/project/pydantic-jsonschema/)
[![Python Versions](https://img.shields.io/pypi/pyversions/pydantic-jsonschema.svg)](https://pypi.org/project/pydantic-jsonschema/)
[![License](https://img.shields.io/github/license/danipulok/pydantic-jsonschema)](https://github.com/danipulok/pydantic-jsonschema/blob/main/LICENSE)

*Convert JSON Schema to Pydantic models, bringing type safety to schema-based validation.*

---

While Pydantic generates JSON Schema from models,
**Pydantic JSON Schema does the reverse** —
it converts JSON Schema definitions into fully typed Pydantic models.

Perfect for working with API specifications, configuration schemas,
or validating LLM-generated data against predefined structures.

## Why use Pydantic JSON Schema?

- **Type-Safe Conversion** — JSON Schema becomes a proper Pydantic model
- **Automatic References** — Handles `$ref` and `$defs` seamlessly
- **Lax Mode** — Type coercion for flexible validation of AI-generated outputs
- **Custom Formats** — Extend with specific validators (email, UUID, etc.)
- **Schema Composition** — Supports `allOf`, `anyOf`, `oneOf` constructs
- **Standards Compliant** — Follows JSON Schema Draft 2020-12

[Full documentation](https://danipulok.github.io/pydantic-jsonschema/)
with examples and API reference.

## Installation

```bash
uv add pydantic-jsonschema
# Or with extra format validators
uv add pydantic-jsonschema[formats]
```

Requires Python 3.12+

## Quick Start

```python
from pydantic_jsonschema import Schema, to_model

# Define your JSON Schema
schema = Schema.model_validate({
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "age": {"type": "integer", "minimum": 0},
        "email": {"type": "string", "format": "email"}
    },
    "required": ["name", "age"]
})

# Convert to Pydantic model
User = to_model(schema, model_name="User")

# Use it like any Pydantic model
user = User(name="Alice", age=30, email="alice@example.com")
print(user.model_dump_json())
#> {"name":"Alice","age":30,"email":"alice@example.com"}
```

## LLM-Friendly Validation

When working with LLM outputs that might return incorrect types,
use lax validation for automatic coercion:

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

# LLM returns strings everywhere
llm_output = {
    "sentiment": "positive",
    "confidence": "0.87",  # String instead of number
    "keywords": "happy, great",  # String instead of array
}

analysis = Analysis.model_validate(llm_output)
print(analysis.confidence)
#> 0.87
print(analysis.keywords)
#> ['happy', 'great']
```

## Learn More

- [Documentation](https://danipulok.github.io/pydantic-jsonschema/)
- [Examples](https://danipulok.github.io/pydantic-jsonschema/examples/)
- [Contributing](https://danipulok.github.io/pydantic-jsonschema/contributing/)

## License

MIT License - see [LICENSE](LICENSE) for details.
