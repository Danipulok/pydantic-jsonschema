# Pydantic JSON Schema

Convert JSON Schema definitions into type-safe Pydantic models.

Pydantic can generate JSON Schema from models. Pydantic JSON Schema does the opposite: it takes JSON Schema definitions and creates Pydantic models with runtime validation.

Use it when you need to:

- Validate data against existing JSON Schema definitions.
- Convert API, configuration, or tool schemas into Pydantic models.
- Validate LLM-generated data against predefined schemas.
- Reuse `$defs`, `$ref`, `anyOf`, `oneOf`, and `allOf` in generated models.

## Installation

```bash
uv add pydantic-jsonschema
```

```bash
pip install pydantic-jsonschema
```

(Requires Python 3.12+)

See the [installation guide](https://danipulok.github.io/pydantic-jsonschema/0.0.13/install/index.md) for third-party validator libraries.

## Quick Start

Convert a JSON Schema object into a Pydantic model:

quick_start.py

```python
from pydantic_jsonschema import Schema, to_model

schema = Schema.model_validate(
    {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer", "minimum": 0},
        },
        "required": ["name"],
    }
)

User = to_model(schema, model_name="User")

user = User(name="Alice", age=30)
print(user.model_dump())
#> {'name': 'Alice', 'age': 30}
```

## References

Reuse schemas with JSON Schema `$defs` and `$ref`:

references.py

```python
from pydantic_jsonschema import Schema, to_model

schema = Schema.model_validate(
    {
        "type": "object",
        "properties": {
            "author": {"$ref": "#/$defs/Person"},
        },
        "$defs": {
            "Person": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                },
                "required": ["name"],
            }
        },
    }
)

BlogPost = to_model(schema, model_name="BlogPost")

post = BlogPost(author={"name": "Alice"})
print(post.author.name)
#> Alice
```

## Key Features

- **Model conversion** - JSON Schema objects become Pydantic models.
- **Reference resolution** - `$ref` and `$defs` create reusable nested models.
- **Schema composition** - `anyOf`, `oneOf`, and `allOf` are converted into Python annotations and models.
- **Validation constraints** - string, number, array, and object constraints become Pydantic validation.
- **Custom formats** - JSON Schema `format` values can use built-in or custom validators.

## Next Steps

- [Installation](https://danipulok.github.io/pydantic-jsonschema/0.0.13/install/index.md) - Install the package and third-party validator libraries
- [Schema](https://danipulok.github.io/pydantic-jsonschema/0.0.13/schema/index.md) - Schema models, fields, and serialization
- [Converters](https://danipulok.github.io/pydantic-jsonschema/0.0.13/converters/index.md) - Learn how schema conversion works
- [Applicators](https://danipulok.github.io/pydantic-jsonschema/0.0.13/applicators/index.md) - Validate `not`, `oneOf`, `if`/`then`/`else`, and other subschema keywords
- [Formats](https://danipulok.github.io/pydantic-jsonschema/0.0.13/formats/index.md) - Add validation for JSON Schema `format` values
- [Examples](https://danipulok.github.io/pydantic-jsonschema/0.0.13/examples/index.md) - Run complete examples
- [Contributing](https://danipulok.github.io/pydantic-jsonschema/0.0.13/contributing/index.md) - Help improve the library
