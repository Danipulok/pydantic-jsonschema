# Schema Models

The `Schema` and `Reference` classes are Pydantic models that represent JSON Schema objects in Python. They are used as the input to the [converter](https://danipulok.github.io/pydantic-jsonschema/0.0.11/converters/index.md).

## Overview

| Class       | Represents                     | Spec                                                                                    |
| ----------- | ------------------------------ | --------------------------------------------------------------------------------------- |
| `Schema`    | A JSON Schema object           | [core](https://json-schema.org/draft/2020-12/json-schema-core)                          |
| `Reference` | A `$ref` reference to a schema | [core §8.2.3.1](https://json-schema.org/draft/2020-12/json-schema-core#section-8.2.3.1) |
| `DataType`  | JSON Schema primitive types    | [core §4.2.1](https://json-schema.org/draft/2020-12/json-schema-core#section-4.2.1)     |

## Creating a Schema

There are two equivalent ways to create a `Schema` instance.

### From a dict

Parse a JSON-like dict (e.g. loaded from a file or API response):

schema_from_dict.py

```python
from pydantic_jsonschema import Schema

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

print(schema.type)
#> object
print(schema.required)
#> ['name']
```

Keys use the original JSON Schema names (`minLength`, `anyOf`, `$defs`). Pydantic handles `camelCase` to `snake_case` conversion automatically via `alias_generator`.

### From Python

Build a schema directly in Python code:

schema_from_python.py

```python
from pydantic_jsonschema import DataType, Schema

schema = Schema(
    type=DataType.OBJECT,
    properties={
        "name": Schema(type=DataType.STRING),
        "age": Schema(
            type=DataType.INTEGER,
            minimum=0,
        ),
    },
    required=["name"],
)

print(schema.type)
#> object
print(schema.properties["name"].type)
#> string
```

Use snake_case field names (`min_length`, `any_of`, `all_of`) and the `DataType` enum.

## Serialization

`Schema` serializes back to valid JSON Schema with `camelCase` keys:

schema_serialization.py

```python
from pydantic_jsonschema import DataType, Schema

schema = Schema(
    type=DataType.STRING,
    min_length=1,
    max_length=100,
)

print(schema.model_dump_json(indent=4))
"""
{
    "type": "string",
    "minLength": 1,
    "maxLength": 100
}
"""
```

Fields that were not set are excluded automatically — no `None` values leak into the output.

## References and Definitions

JSON Schema uses `$ref` and `$defs` to define reusable schemas.

### `$defs` — shared definitions

Place shared schemas in `$defs` at the root level:

schema_defs.py

```python
from pydantic_jsonschema import Schema

schema = Schema.model_validate(
    {
        "type": "object",
        "properties": {
            "home": {"$ref": "#/$defs/Address"},
            "work": {"$ref": "#/$defs/Address"},
        },
        "$defs": {
            "Address": {
                "type": "object",
                "properties": {
                    "city": {"type": "string"},
                    "zip": {"type": "string"},
                },
                "required": ["city"],
            }
        },
    }
)

print(schema.defs["Address"].type)
#> object
```

### `$ref` — reference to a definition

A `$ref` in a property becomes a `Reference` instance:

schema_ref.py

```python
from pydantic_jsonschema import Reference, Schema

schema = Schema.model_validate(
    {
        "type": "object",
        "properties": {
            "author": {"$ref": "#/$defs/Person"},
        },
    }
)

author_field = schema.properties["author"]
print(isinstance(author_field, Reference))
#> True
print(author_field.ref)
#> #/$defs/Person
```

## DataType Enum

`DataType` maps JSON Schema type names to Python:

datatype_enum.py

```python
from pydantic_jsonschema import DataType

print(DataType.STRING)
#> string
print(DataType.INTEGER)
#> integer
print(DataType.OBJECT)
#> object
```

All members: `NULL`, `STRING`, `NUMBER`, `INTEGER`, `BOOLEAN`, `ARRAY`, `OBJECT`.

## Field Reference

`Schema` fields map directly to JSON Schema keywords. Only fields used by the converter are declared explicitly. Unknown keywords are preserved via `extra="allow"`.

### Composition

| Python field | JSON Schema | Spec                                                                                      |
| ------------ | ----------- | ----------------------------------------------------------------------------------------- |
| `all_of`     | `allOf`     | [core §10.2.1.1](https://json-schema.org/draft/2020-12/json-schema-core#section-10.2.1.1) |
| `any_of`     | `anyOf`     | [core §10.2.1.2](https://json-schema.org/draft/2020-12/json-schema-core#section-10.2.1.2) |
| `one_of`     | `oneOf`     | [core §10.2.1.3](https://json-schema.org/draft/2020-12/json-schema-core#section-10.2.1.3) |

### Subschemas

| Python field            | JSON Schema            | Spec                                                                                      |
| ----------------------- | ---------------------- | ----------------------------------------------------------------------------------------- |
| `items`                 | `items`                | [core §10.3.1.2](https://json-schema.org/draft/2020-12/json-schema-core#section-10.3.1.2) |
| `properties`            | `properties`           | [core §10.3.2.1](https://json-schema.org/draft/2020-12/json-schema-core#section-10.3.2.1) |
| `additional_properties` | `additionalProperties` | [core §10.3.2.3](https://json-schema.org/draft/2020-12/json-schema-core#section-10.3.2.3) |

### Type and constants

| Python field | JSON Schema | Spec                                                                                            |
| ------------ | ----------- | ----------------------------------------------------------------------------------------------- |
| `type`       | `type`      | [validation §6.1.1](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.1.1) |
| `enum`       | `enum`      | [validation §6.1.2](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.1.2) |
| `const`      | `const`     | [validation §6.1.3](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.1.3) |

### Numeric constraints

| Python field        | JSON Schema        | Spec                                                                                            |
| ------------------- | ------------------ | ----------------------------------------------------------------------------------------------- |
| `multiple_of`       | `multipleOf`       | [validation §6.2.1](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.2.1) |
| `maximum`           | `maximum`          | [validation §6.2.2](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.2.2) |
| `exclusive_maximum` | `exclusiveMaximum` | [validation §6.2.3](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.2.3) |
| `minimum`           | `minimum`          | [validation §6.2.4](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.2.4) |
| `exclusive_minimum` | `exclusiveMinimum` | [validation §6.2.5](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.2.5) |

### String constraints

| Python field | JSON Schema | Spec                                                                                            |
| ------------ | ----------- | ----------------------------------------------------------------------------------------------- |
| `min_length` | `minLength` | [validation §6.3.2](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.3.2) |
| `max_length` | `maxLength` | [validation §6.3.1](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.3.1) |
| `pattern`    | `pattern`   | [validation §6.3.3](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.3.3) |

### Array constraints

| Python field | JSON Schema | Spec                                                                                            |
| ------------ | ----------- | ----------------------------------------------------------------------------------------------- |
| `min_items`  | `minItems`  | [validation §6.4.2](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.4.2) |
| `max_items`  | `maxItems`  | [validation §6.4.1](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.4.1) |

### Object constraints

| Python field | JSON Schema | Spec                                                                                            |
| ------------ | ----------- | ----------------------------------------------------------------------------------------------- |
| `required`   | `required`  | [validation §6.5.3](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.5.3) |

### Format

| Python field | JSON Schema | Spec                                                                                    |
| ------------ | ----------- | --------------------------------------------------------------------------------------- |
| `format`     | `format`    | [validation §7](https://json-schema.org/draft/2020-12/json-schema-validation#section-7) |

### Metadata

| Python field  | JSON Schema   | Spec                                                                                        |
| ------------- | ------------- | ------------------------------------------------------------------------------------------- |
| `title`       | `title`       | [validation §9.1](https://json-schema.org/draft/2020-12/json-schema-validation#section-9.1) |
| `description` | `description` | [validation §9.1](https://json-schema.org/draft/2020-12/json-schema-validation#section-9.1) |
| `default`     | `default`     | [validation §9.2](https://json-schema.org/draft/2020-12/json-schema-validation#section-9.2) |
| `examples`    | `examples`    | [validation §9.5](https://json-schema.org/draft/2020-12/json-schema-validation#section-9.5) |

### Definitions

| Python field | JSON Schema | Spec                                                                                |
| ------------ | ----------- | ----------------------------------------------------------------------------------- |
| `defs`       | `$defs`     | [core §8.2.4](https://json-schema.org/draft/2020-12/json-schema-core#section-8.2.4) |

## Extra Keywords

`Schema` preserves unknown keywords via `extra="allow"`, per JSON Schema spec [§4.3.1](https://json-schema.org/draft/2020-12/json-schema-core#section-4.3.1) and [§6.5](https://json-schema.org/draft/2020-12/json-schema-core#section-6.5):

schema_extra.py

```python
from pydantic_jsonschema import Schema

schema = Schema.model_validate(
    {
        "type": "string",
        "x-custom-flag": True,
        "x-order": 5,
    }
)

dumped = schema.model_dump()
print(dumped["x-custom-flag"])
#> True
print(dumped["x-order"])
#> 5
```

## Next Steps

- [Converters](https://danipulok.github.io/pydantic-jsonschema/0.0.11/converters/index.md) - Convert schemas to Pydantic models
- [Format Validators](https://danipulok.github.io/pydantic-jsonschema/0.0.11/formats/index.md) - Add validation for `format` values
- [API Reference](https://danipulok.github.io/pydantic-jsonschema/0.0.11/api/types/index.md) - Full API docs for schema types
