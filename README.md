# Pydantic JSON Schema

[![CI](https://github.com/danipulok/pydantic-jsonschema/workflows/CI/badge.svg)](https://github.com/danipulok/pydantic-jsonschema/actions)
[![Coverage](https://img.shields.io/codecov/c/github/danipulok/pydantic-jsonschema)](https://codecov.io/gh/danipulok/pydantic-jsonschema)
[![PyPI](https://img.shields.io/pypi/v/pydantic-jsonschema.svg)](https://pypi.org/project/pydantic-jsonschema/)
[![Python Versions](https://img.shields.io/pypi/pyversions/pydantic-jsonschema.svg)](https://pypi.org/project/pydantic-jsonschema/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/danipulok/pydantic-jsonschema/blob/main/LICENSE)
[![Docs](https://img.shields.io/badge/docs-latest-blue.svg)](https://danipulok.github.io/pydantic-jsonschema/)

Convert JSON Schema definitions into Pydantic models with runtime validation.

## Installation

```bash
uv add pydantic-jsonschema
```

Requires Python 3.12+.
See the [installation guide](https://danipulok.github.io/pydantic-jsonschema/install/) for optional format validator extras.

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

## Documentation

[https://danipulok.github.io/pydantic-jsonschema/](https://danipulok.github.io/pydantic-jsonschema/)

## License

MIT License - see [LICENSE](LICENSE) for details.
