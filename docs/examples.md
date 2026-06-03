# Examples

Real-world examples showing how to use Pydantic JSON Schema in practice.

!!! tip "Runnable Examples"
    Files in `examples/` are complete scripts. They are also executed by the test suite, so the
    commands and output below stay in sync with the project.

## Overview

| Example                         | Shows                                                     | Run command                                   |
|---------------------------------|-----------------------------------------------------------|-----------------------------------------------|
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
--8<-- "examples/nested_schemas.py"
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
--8<-- "examples/custom_validators.py"
```

## Next Steps

- [Converters](converters.md) - Learn about creating models
- [Format Validators](formats.md) - Add custom validation
- [Contributing](contributing.md) - Help improve the library
