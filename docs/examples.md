# Examples

Real-world examples showing how to use Pydantic JSON Schema in practice.

!!! tip "Runnable Examples"
    Files in `examples/` are complete scripts. They are also executed by the test suite, so the
    commands and output below stay in sync with the project.

## Overview

| Example                         | Shows                                                     | Run command                                   |
|---------------------------------|-----------------------------------------------------------|-----------------------------------------------|
| `examples/nested_schemas.py`    | Nested objects, arrays, `$defs`, and `$ref` reuse         | `uv run python examples/nested_schemas.py`    |
| `examples/custom_formats.py`    | Custom `formats`, normalization, and validation           | `uv run python examples/custom_formats.py`    |
| `examples/loading_rules.py`     | `rules` for per-node input coercion and output dumping    | `uv run python examples/loading_rules.py`     |

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

## Custom Formats

Use this example when JSON Schema `format` values need project-specific validation.

It demonstrates:

- Registering `formats` with `to_model()`.
- Normalizing input values before storing them.
- Raising `ValueError` from custom validators.
- Combining built-in schema types with domain-specific checks.

Run it with:

```bash
uv run python examples/custom_formats.py
```

Expected output:

```text
WDG-1234-PRO
19.99
```

```python
--8<-- "examples/custom_formats.py"
```

## Loading Rules

Use this example when the input arrives in a shape the schema does not describe — a packed cell,
a value that needs normalizing — or when the output has to go back in that shape.

It demonstrates:

- Coercing raw input with `Before` before the schema type is parsed.
- Normalizing a single node picked by its JSON Pointer with `ByPath`.
- Matching every node of one Python type with `ByType`.
- Pairing a load rule with a `Dump` rule for a round-trip.

Run it with:

```bash
uv run python examples/loading_rules.py
```

Expected output:

```text
WDG-1234-PRO
['sale', 'clearance']
{'sku': 'WDG-1234-PRO', 'tags': 'sale,clearance'}
```

```python
--8<-- "examples/loading_rules.py"
```

## Next Steps

- [Converters](converters.md) - Learn about creating models
- [Formats](formats.md) - Add custom validation
- [Rules](rules.md) - Customize loading and dumping per node
- [Contributing](contributing.md) - Help improve the library
