# Examples

Real-world examples showing how to use Pydantic JSON Schema in practice.

Runnable Examples

Files in `examples/` are complete scripts. They are also executed by the test suite, so the commands and output below stay in sync with the project.

## Overview

| Example                         | Shows                                                     | Run command                                   |
| ------------------------------- | --------------------------------------------------------- | --------------------------------------------- |
| `examples/nested_schemas.py`    | Nested objects, arrays, `$defs`, and `$ref` reuse         | `uv run python examples/nested_schemas.py`    |
| `examples/custom_validators.py` | Custom `format_validators`, normalization, and validation | `uv run python examples/custom_validators.py` |

## Complex Nested Schemas

Use this example when your schema contains reusable definitions and multiple nesting levels.

It demonstrates:

- Defining reusable schemas in `$defs`.
- Referencing shared schemas with `$ref`.
- Creating nested generated models from object properties.
- Validating arrays of referenced objects.

Run it with:

```bash
uv run python examples/nested_schemas.py
```

Expected output:

```text
Getting Started with Pydantic JSON Schema
1
Great article!
```

```python
"""Handle complex schemas with multiple levels of nesting and references."""

from pydantic_jsonschema import Schema, to_model

blog_schema = Schema.model_validate(
    {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "author": {"$ref": "#/$defs/Person"},
            "comments": {"type": "array", "items": {"$ref": "#/$defs/Comment"}},
            "tags": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["title", "author"],
        "$defs": {
            "Person": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "email": {"type": "string", "format": "email"},
                },
                "required": ["name"],
            },
            "Comment": {
                "type": "object",
                "properties": {
                    "author": {"$ref": "#/$defs/Person"},
                    "text": {"type": "string"},
                    "timestamp": {"type": "string"},
                },
                "required": ["author", "text"],
            },
        },
    },
)

BlogPost = to_model(blog_schema, model_name="BlogPost")

# Create a blog post with nested data
post = BlogPost(
    title="Getting Started with Pydantic JSON Schema",
    author={"name": "Alice", "email": "alice@example.com"},
    comments=[
        {
            "author": {"name": "Bob"},
            "text": "Great article!",
            "timestamp": "2024-01-15T10:30:00Z",
        },
    ],
    tags=["python", "pydantic", "json-schema"],
)

# NOTE: `ruff format` rewrites `#>` to `# >`, breaking `pytest-examples` output markers.
# fmt: off
print(post.title)  # type: ignore[attr-defined]
#> Getting Started with Pydantic JSON Schema
print(len(post.comments))  # type: ignore[attr-defined]
#> 1
print(post.comments[0].text)  # type: ignore[attr-defined]
#> Great article!
# fmt: on
```

## Custom Format Validators

Use this example when JSON Schema `format` values need project-specific validation.

It demonstrates:

- Registering `format_validators` with `to_model()`.
- Normalizing input values before storing them.
- Raising `ValueError` from custom validators.
- Combining built-in schema types with domain-specific checks.

Run it with:

```bash
uv run python examples/custom_validators.py
```

Expected output:

```text
WDG-1234-PRO
19.99
```

```python
"""Add domain-specific validation with custom format validators."""

import re

from pydantic_jsonschema import Schema, to_model


def validate_sku(value: str) -> str:
    """Validate product SKU format: ABC-1234-XYZ."""
    value = value.upper()
    pattern = r"^[A-Z]{3}-\d{4}-[A-Z]{3}$"

    if not re.match(pattern, value):
        msg = "SKU must be in format ABC-1234-XYZ"
        raise ValueError(msg)

    return value


def validate_price(value: float) -> float:
    """Validate price is positive with max 2 decimals."""
    if value <= 0:
        msg = "Price must be positive"
        raise ValueError(msg)

    if round(value, 2) != value:
        msg = "Price can have at most 2 decimal places"
        raise ValueError(msg)

    return value


product_schema = Schema.model_validate(
    {
        "type": "object",
        "properties": {
            "sku": {"type": "string", "format": "sku"},
            "name": {"type": "string"},
            "price": {"type": "number", "format": "price"},
        },
        "required": ["sku", "name", "price"],
    },
)

Product = to_model(
    product_schema,
    format_validators={
        "sku": validate_sku,
        "price": validate_price,
    },
)

product = Product(
    sku="wdg-1234-pro",  # Normalized to uppercase
    name="Widget Pro",
    price=19.99,
)

# NOTE: `ruff format` rewrites `#>` to `# >`, breaking `pytest-examples` output markers.
# fmt: off
print(product.sku)  # type: ignore[attr-defined]
#> WDG-1234-PRO
print(product.price)  # type: ignore[attr-defined]
#> 19.99
# fmt: on
```

## Next Steps

- [Converters](https://danipulok.github.io/pydantic-jsonschema/0.0.9/converters/index.md) - Learn about creating models
- [Format Validators](https://danipulok.github.io/pydantic-jsonschema/0.0.9/formats/index.md) - Add custom validation
- [Contributing](https://danipulok.github.io/pydantic-jsonschema/0.0.9/contributing/index.md) - Help improve the library
