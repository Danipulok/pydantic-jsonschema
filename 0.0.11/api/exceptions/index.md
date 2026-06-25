Custom exceptions for schema conversion, reference resolution, and format validation.

Classes:

| Name                          | Description                  |
| ----------------------------- | ---------------------------- |
| `BasePydanticJsonSchemaError` | Base schema exception.       |
| `SchemaConversionError`       | Schema conversion failed.    |
| `SchemaReferenceError`        | Reference resolution failed. |
| `FormatValidationError`       | Format validation failed.    |

## BasePydanticJsonSchemaError

```python
BasePydanticJsonSchemaError(message: str)
```

Bases: `Exception`

Base schema exception.

Methods:

| Name            | Description                                                     |
| --------------- | --------------------------------------------------------------- |
| `__post_init__` | Pass all dataclass field values to Exception.__init__ for args. |
| `__str__`       | Delegate to repr for consistent error display.                  |

### __post_init__

```python
__post_init__() -> None
```

Pass all dataclass field values to `Exception.__init__` for `args`.

### __str__

```python
__str__() -> str
```

Delegate to `repr` for consistent error display.

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
