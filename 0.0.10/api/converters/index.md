JSON Schema to Pydantic model converter.

Classes:

| Name              | Description                                             |
| ----------------- | ------------------------------------------------------- |
| `SchemaConverter` | Stateful converter from JSON Schema to Pydantic models. |

Functions:

| Name       | Description                       |
| ---------- | --------------------------------- |
| `to_model` | Convert schema to Pydantic model. |

## FormatValidator

Bases: `Protocol`

Protocol for format validator callables.

Can be:

- Callable: validation function
- type: Pydantic type class (e.g., from pydantic-extra-types)
- Annotated type with validators (e.g., Annotated[int, AfterValidator(...)])

Accepts any JSON Schema type: string, number, integer, boolean, null, array, object. Callables receive the raw input and run before Pydantic's standard validation.

See: https://json-schema.org/draft/2020-12/json-schema-validation#section-7.1

For Pydantic validation details, see: https://docs.pydantic.dev/latest/concepts/validators/#annotated-validators https://docs.pydantic.dev/latest/concepts/validators/#after-validators

Methods:

| Name       | Description                                                  |
| ---------- | ------------------------------------------------------------ |
| `__call__` | Process the raw value before Pydantic's standard validation. |

### __call__

```python
__call__(value: PythonType) -> PythonType
```

Process the raw value before Pydantic's standard validation.

## SchemaConverter

```python
SchemaConverter(
    *,
    default_model_name: str = _DEFAULT_MODEL_NAME,
    refs: dict[Ref, type[BaseModel]] | None = None,
    format_validators: dict[FormatName, FormatValidatorType] | None = None
)
```

Stateful converter from JSON Schema to Pydantic models.

Initialize converter with optional pre-built refs and format validators.

Parameters:

| Name                 | Type                                    | Description                             | Default                                        |
| -------------------- | --------------------------------------- | --------------------------------------- | ---------------------------------------------- |
| `default_model_name` | `str`                                   | Fallback name for models without title. | `_DEFAULT_MODEL_NAME`                          |
| `refs`               | \`dict\[Ref, type[BaseModel]\]          | None\`                                  | Pre-built Pydantic models for $ref resolution. |
| `format_validators`  | \`dict[FormatName, FormatValidatorType] | None\`                                  | Validators keyed by JSON Schema format value.  |

Methods:

| Name             | Description                                          |
| ---------------- | ---------------------------------------------------- |
| `convert_schema` | Convert JSON Schema (root schema) to Pydantic model. |

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
    format_validators: dict[FormatName, FormatValidatorType] | None = None,
) -> type[BaseModel]
```

Convert schema to Pydantic model.

Parameters:

| Name                | Type                                    | Description        | Default                                                    |
| ------------------- | --------------------------------------- | ------------------ | ---------------------------------------------------------- |
| `schema`            | `Schema`                                | Schema to convert. | *required*                                                 |
| `refs`              | \`dict\[Ref, type[BaseModel]\]          | None\`             | Pre-built reference models.                                |
| `format_validators` | \`dict[FormatName, FormatValidatorType] | None\`             | Custom format validators (callables, types, or Annotated). |
| `model_name`        | \`str                                   | None\`             | Name for the generated model.                              |

Returns:

| Type              | Description           |
| ----------------- | --------------------- |
| `type[BaseModel]` | Pydantic model class. |
