# Examples

Real-world examples showing how to use Pydantic JSON Schema in practice.

!!! tip "Runnable Examples"
    All examples in the [`examples/`](https://github.com/danipulok/pydantic-jsonschema/tree/main/examples) folder are complete and can be run as-is. Try them out!

## Complex Nested Schemas

Handle schemas with multiple levels of nesting and references.

[:material-file-code: examples/nested_schemas.py](https://github.com/danipulok/pydantic-jsonschema/blob/main/examples/nested_schemas.py){ .md-button }

```python
--8<-- "examples/nested_schemas.py"
```

## Custom Format Validators

Add domain-specific validation for special formats.

[:material-file-code: examples/custom_validators.py](https://github.com/danipulok/pydantic-jsonschema/blob/main/examples/custom_validators.py){ .md-button }

```python
--8<-- "examples/custom_validators.py"
```

## Next Steps

- [Converters](converters.md) — Learn about creating models
- [Format Validators](formats.md) — Add custom validation
- [Contributing](contributing.md) — Help improve the library
