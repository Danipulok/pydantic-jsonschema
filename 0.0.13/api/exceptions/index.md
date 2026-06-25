# Exceptions

Errors raised during schema conversion and format validation.

Custom exceptions for schema conversion, reference resolution, and format validation.

## BasePydanticJsonSchemaError

```python
BasePydanticJsonSchemaError(message: str)
```

Bases: `Exception`

Base schema exception.

## SchemaConversionError

```python
SchemaConversionError(message: str)
```

Bases: `BasePydanticJsonSchemaError`

Schema conversion failed.

## SchemaReferenceError

```python
SchemaReferenceError(message: str, path: list[str])
```

Bases: `BasePydanticJsonSchemaError`

Reference resolution failed.

## FormatValidationError

```python
FormatValidationError(message: str, value: Any = None)
```

Bases: `BasePydanticJsonSchemaError`, `ValueError`

Format validation failed.
