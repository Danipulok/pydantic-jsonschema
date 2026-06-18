# Pydantic JSON Schema

[![CI](https://github.com/danipulok/pydantic-jsonschema/workflows/CI/badge.svg)](https://github.com/danipulok/pydantic-jsonschema/actions)
[![Coverage](https://img.shields.io/codecov/c/github/danipulok/pydantic-jsonschema)](https://codecov.io/gh/danipulok/pydantic-jsonschema)
[![PyPI](https://img.shields.io/pypi/v/pydantic-jsonschema.svg)](https://pypi.org/project/pydantic-jsonschema/)
[![Python Versions](https://img.shields.io/pypi/pyversions/pydantic-jsonschema.svg)](https://pypi.org/project/pydantic-jsonschema/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/danipulok/pydantic-jsonschema/blob/main/LICENSE)
[![Docs](https://img.shields.io/badge/docs-latest-blue.svg)](https://danipulok.github.io/pydantic-jsonschema/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![mypy](https://img.shields.io/badge/types-mypy-blue.svg)](https://github.com/python/mypy)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)

Convert JSON Schema definitions into Pydantic models with runtime validation.

## Installation

```bash
uv add pydantic-jsonschema
```

Requires Python 3.12+.
See the [installation guide](https://danipulok.github.io/pydantic-jsonschema/latest/install/) for third-party validator libraries.

## Quick Start

```python
from pydantic_jsonschema import Schema, to_model

schema = Schema.model_validate({
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "age": {"type": "integer", "minimum": 0},
    },
    "required": ["name"],
})

User = to_model(schema, model_name="User")

user = User(name="Alice", age=30)
print(user.model_dump())
#> {'name': 'Alice', 'age': 30}
```

## Schema Model

The `Schema` class is a Pydantic model representing a JSON Schema object.
Use it to parse, inspect, and serialize schemas with full type safety:

```python
from pydantic_jsonschema import DataType, Schema

schema = Schema(
    type=DataType.OBJECT,
    properties={
        "name": Schema(type=DataType.STRING),
    },
    required=["name"],
)

print(schema.model_dump_json(indent=4))
"""
{
    "type": "object",
    "properties": {
        "name": {
            "type": "string"
        }
    },
    "required": [
        "name"
    ]
}
"""
```

`Schema` supports `$ref` and `$defs` for reusable definitions — properties referencing a `$ref` are parsed as `Reference` objects and resolved automatically during conversion.

See the [Schema documentation](https://danipulok.github.io/pydantic-jsonschema/latest/schema/)
for field reference and usage examples.

## Documentation

[https://danipulok.github.io/pydantic-jsonschema/](https://danipulok.github.io/pydantic-jsonschema/)

## Roadmap

- [x] Custom JSON Schema implementation (remove `openapi-pydantic` dependency)
- [x] Remove `fqdn` and `rfc3986` dependencies
- [x] Remove `email-validator` dependency
- [x] Logic fixes in schema conversion
- [x] Add `inline_snapshot` for tests
- [ ] Configurable loading by type (inspired by [adaptix](https://github.com/reagento/adaptix))

## Acknowledgments

- [vgavro](https://github.com/vgavro) — initial library idea and early guidance
- [bodlan](https://github.com/bodlan) — early documentation review and feedback

## License

MIT License - see [LICENSE](LICENSE) for details.
