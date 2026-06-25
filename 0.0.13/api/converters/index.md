# Converters

Turn a Schema into a Pydantic model.

Convert a JSON Schema `Schema` into a Pydantic model (`to_model` / `SchemaConverter`).

## SchemaConverter

```python
SchemaConverter(
    *,
    default_model_name: str = _DEFAULT_MODEL_NAME,
    refs: dict[Ref, type[BaseModel]] | None = None,
    formats: dict[FormatName, FormatType] | None = None
)
```

Stateful converter from JSON Schema to Pydantic models.

Initialize converter with optional pre-built refs and format types.

Parameters:

| Name                 | Type                           | Description                                              | Default                                                                    |
| -------------------- | ------------------------------ | -------------------------------------------------------- | -------------------------------------------------------------------------- |
| `default_model_name` | `str`                          | Fallback name for models without title (default: Model). | `_DEFAULT_MODEL_NAME`                                                      |
| `refs`               | \`dict\[Ref, type[BaseModel]\] | None\`                                                   | Pre-built Pydantic models for $ref resolution.                             |
| `formats`            | \`dict[FormatName, FormatType] | None\`                                                   | Format types (a type or Annotated type) keyed by JSON Schema format value. |

### convert_schema

```python
convert_schema(
    schema: Schema, /, *, model_name: str | None = None
) -> type[BaseModel]
```

Convert JSON Schema (root schema) to Pydantic model.

Parameters:

| Name         | Type     | Description        | Default                       |
| ------------ | -------- | ------------------ | ----------------------------- |
| `schema`     | `Schema` | Schema to convert. | *required*                    |
| `model_name` | \`str    | None\`             | Name for the generated model. |

Returns:

| Type              | Description           |
| ----------------- | --------------------- |
| `type[BaseModel]` | Pydantic model class. |

Raises:

| Type                    | Description                    |
| ----------------------- | ------------------------------ |
| `SchemaConversionError` | If schema cannot be converted. |

## to_model

```python
to_model(
    schema: Schema,
    /,
    *,
    model_name: str | None = None,
    refs: dict[Ref, type[BaseModel]] | None = None,
    formats: dict[FormatName, FormatType] | None = None,
) -> type[BaseModel]
```

Convert schema to Pydantic model.

Parameters:

| Name         | Type                           | Description        | Default                                                                    |
| ------------ | ------------------------------ | ------------------ | -------------------------------------------------------------------------- |
| `schema`     | `Schema`                       | Schema to convert. | *required*                                                                 |
| `refs`       | \`dict\[Ref, type[BaseModel]\] | None\`             | Pre-built reference models.                                                |
| `formats`    | \`dict[FormatName, FormatType] | None\`             | Format types (a type or Annotated type) keyed by JSON Schema format value. |
| `model_name` | \`str                          | None\`             | Name for the generated model.                                              |

Returns:

| Type              | Description           |
| ----------------- | --------------------- |
| `type[BaseModel]` | Pydantic model class. |
