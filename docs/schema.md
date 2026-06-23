# Schema Models

The `Schema` and `Reference` classes are Pydantic models that represent JSON Schema objects in Python.
They are used as the input to the [converter](converters.md).

## Overview

| Class       | Represents                     | Spec                                                                                    |
|-------------|--------------------------------|-----------------------------------------------------------------------------------------|
| `Schema`    | A JSON Schema object           | [core](https://json-schema.org/draft/2020-12/json-schema-core)                          |
| `Reference` | A `$ref` reference to a schema | [core §8.2.3.1](https://json-schema.org/draft/2020-12/json-schema-core#section-8.2.3.1) |
| `DataType`  | JSON Schema primitive types    | [core §4.2.1](https://json-schema.org/draft/2020-12/json-schema-core#section-4.2.1)     |

## Creating a Schema

There are two equivalent ways to create a `Schema` instance.

### From a dict

Parse a JSON-like dict (e.g. loaded from a file or API response):

```python title="schema_from_dict.py"
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

Keys use the original JSON Schema names (`minLength`, `anyOf`, `$defs`).
Pydantic handles `camelCase` to `snake_case` conversion automatically via `alias_generator`.

### From Python

Build a schema directly in Python code:

```python title="schema_from_python.py"
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

```python title="schema_serialization.py"
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

```python title="schema_defs.py"
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

```python title="schema_ref.py"
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

```python title="datatype_enum.py"
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

`Schema` fields map directly to JSON Schema keywords. Other or custom keywords are preserved via `extra="allow"`.
Some declared keywords round-trip through parsing and serialization but are not yet consumed by the converter.

### Composition

| Python field | JSON Schema | Spec                                                                                        |
|--------------|-------------|---------------------------------------------------------------------------------------------|
| `all_of`     | `allOf`     | [core §10.2.1.1](https://json-schema.org/draft/2020-12/json-schema-core#section-10.2.1.1)   |
| `any_of`     | `anyOf`     | [core §10.2.1.2](https://json-schema.org/draft/2020-12/json-schema-core#section-10.2.1.2)   |
| `one_of`     | `oneOf`     | [core §10.2.1.3](https://json-schema.org/draft/2020-12/json-schema-core#section-10.2.1.3)   |
| `not_`       | `not`       | [core §10.2.1.4](https://json-schema.org/draft/2020-12/json-schema-core#section-10.2.1.4)   |

### Conditional

`if` / `else` are Python reserved words, so the fields use a trailing underscore with an alias.
`populate_by_name=True` keeps both forms loadable (`Schema(if_=...)` and `{"if": ...}`).

| Python field | JSON Schema | Spec                                                                                        |
|--------------|-------------|---------------------------------------------------------------------------------------------|
| `if_`        | `if`        | [core §10.2.2.1](https://json-schema.org/draft/2020-12/json-schema-core#section-10.2.2.1)   |
| `then`       | `then`      | [core §10.2.2.2](https://json-schema.org/draft/2020-12/json-schema-core#section-10.2.2.2)   |
| `else_`      | `else`      | [core §10.2.2.3](https://json-schema.org/draft/2020-12/json-schema-core#section-10.2.2.3)   |

### Subschemas

| Python field            | JSON Schema            | Spec                                                                                        |
|-------------------------|------------------------|---------------------------------------------------------------------------------------------|
| `items`                 | `items`                | [core §10.3.1.2](https://json-schema.org/draft/2020-12/json-schema-core#section-10.3.1.2)   |
| `prefix_items`          | `prefixItems`          | [core §10.3.1.1](https://json-schema.org/draft/2020-12/json-schema-core#section-10.3.1.1)   |
| `contains`              | `contains`             | [core §10.3.1.3](https://json-schema.org/draft/2020-12/json-schema-core#section-10.3.1.3)   |
| `properties`            | `properties`           | [core §10.3.2.1](https://json-schema.org/draft/2020-12/json-schema-core#section-10.3.2.1)   |
| `additional_properties` | `additionalProperties` | [core §10.3.2.3](https://json-schema.org/draft/2020-12/json-schema-core#section-10.3.2.3)   |
| `pattern_properties`    | `patternProperties`    | [core §10.3.2.2](https://json-schema.org/draft/2020-12/json-schema-core#section-10.3.2.2)   |

### Type and constants

| Python field | JSON Schema | Spec                                                                                                |
|--------------|-------------|-----------------------------------------------------------------------------------------------------|
| `type`       | `type`      | [validation §6.1.1](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.1.1)     |
| `enum`       | `enum`      | [validation §6.1.2](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.1.2)     |
| `const`      | `const`     | [validation §6.1.3](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.1.3)     |

### Numeric constraints

| Python field         | JSON Schema        | Spec                                                                                            |
|----------------------|--------------------|-------------------------------------------------------------------------------------------------|
| `multiple_of`        | `multipleOf`       | [validation §6.2.1](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.2.1) |
| `maximum`            | `maximum`          | [validation §6.2.2](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.2.2) |
| `exclusive_maximum`  | `exclusiveMaximum` | [validation §6.2.3](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.2.3) |
| `minimum`            | `minimum`          | [validation §6.2.4](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.2.4) |
| `exclusive_minimum`  | `exclusiveMinimum` | [validation §6.2.5](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.2.5) |

### String constraints

| Python field | JSON Schema | Spec                                                                                            |
|--------------|-------------|-------------------------------------------------------------------------------------------------|
| `min_length` | `minLength` | [validation §6.3.2](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.3.2) |
| `max_length` | `maxLength` | [validation §6.3.1](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.3.1) |
| `pattern`    | `pattern`   | [validation §6.3.3](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.3.3) |

### Array constraints

| Python field   | JSON Schema   | Spec                                                                                            |
|----------------|---------------|-------------------------------------------------------------------------------------------------|
| `min_items`    | `minItems`    | [validation §6.4.2](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.4.2) |
| `max_items`    | `maxItems`    | [validation §6.4.1](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.4.1) |
| `unique_items` | `uniqueItems` | [validation §6.4.3](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.4.3) |
| `max_contains` | `maxContains` | [validation §6.4.4](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.4.4) |
| `min_contains` | `minContains` | [validation §6.4.5](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.4.5) |

### Object constraints

| Python field         | JSON Schema         | Spec                                                                                            |
|----------------------|---------------------|-------------------------------------------------------------------------------------------------|
| `required`           | `required`          | [validation §6.5.3](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.5.3) |
| `min_properties`     | `minProperties`     | [validation §6.5.2](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.5.2) |
| `max_properties`     | `maxProperties`     | [validation §6.5.1](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.5.1) |
| `dependent_required` | `dependentRequired` | [validation §6.5.4](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.5.4) |
| `dependent_schemas`  | `dependentSchemas`  | [core §10.2.2.4](https://json-schema.org/draft/2020-12/json-schema-core#section-10.2.2.4)       |

### Format

| Python field | JSON Schema | Spec                                                                                    |
|--------------|-------------|-----------------------------------------------------------------------------------------|
| `format`     | `format`    | [validation §7](https://json-schema.org/draft/2020-12/json-schema-validation#section-7) |

### Metadata

| Python field  | JSON Schema   | Spec                                                                                        |
|---------------|---------------|---------------------------------------------------------------------------------------------|
| `title`       | `title`       | [validation §9.1](https://json-schema.org/draft/2020-12/json-schema-validation#section-9.1) |
| `description` | `description` | [validation §9.1](https://json-schema.org/draft/2020-12/json-schema-validation#section-9.1) |
| `default`     | `default`     | [validation §9.2](https://json-schema.org/draft/2020-12/json-schema-validation#section-9.2) |
| `examples`    | `examples`    | [validation §9.5](https://json-schema.org/draft/2020-12/json-schema-validation#section-9.5) |

### Definitions

| Python field | JSON Schema | Spec                                                                                      |
|--------------|-------------|-------------------------------------------------------------------------------------------|
| `defs`       | `$defs`     | [core §8.2.4](https://json-schema.org/draft/2020-12/json-schema-core#section-8.2.4)       |

## Extra Keywords

`Schema` preserves unknown keywords via `extra="allow"`, per JSON Schema spec
[§4.3.1](https://json-schema.org/draft/2020-12/json-schema-core#section-4.3.1) and
[§6.5](https://json-schema.org/draft/2020-12/json-schema-core#section-6.5):

```python title="schema_extra.py"
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

- [Converters](converters.md) - Convert schemas to Pydantic models
- [Formats](formats.md) - Add validation for `format` values
- [API Reference](api/schema.md) - Full API docs for schema types
