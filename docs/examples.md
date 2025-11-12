# Examples

Real-world examples showing how to use Pydantic JSON Schema in practice.

!!! tip "Runnable Examples"
    All examples in the [`examples/`](https://github.com/danipulok/pydantic-jsonschema/tree/main/examples) folder are complete and can be run as-is. Try them out!

## Validating LLM Outputs

Extract structured data from LLM responses with automatic type coercion.

[:material-file-code: examples/llm_validation.py](https://github.com/danipulok/pydantic-jsonschema/blob/main/examples/llm_validation.py){ .md-button }

```python
--8<-- "examples/llm_validation.py"
```

## CSV Import with Type Conversion

Import CSV data with automatic type coercion for all fields.

[:material-file-code: examples/csv_import.py](https://github.com/danipulok/pydantic-jsonschema/blob/main/examples/csv_import.py){ .md-button }

```python
--8<-- "examples/csv_import.py"
```

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

- [Converters](converters.md) — Learn about creating models and validation modes
- [Lax Validation](lax.md) — Understand type coercion for flexible validation
- [Format Validators](formats.md) — Add custom validation
- [Contributing](contributing.md) — Help improve the library
