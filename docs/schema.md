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

`Schema` fields map directly to JSON Schema keywords. Names convert between `snake_case` and
`camelCase` automatically (via `alias_generator`). Only fields used by the converter are declared
explicitly; unknown keywords are preserved via `extra="allow"`.

Fields by category:

- **Type & values:** `type`, `enum`, `const`
- **Composition:** `all_of`, `any_of`, `one_of`
- **Subschemas:** `properties`, `items`, `additional_properties`
- **Numeric:** `multiple_of`, `maximum`, `exclusive_maximum`, `minimum`, `exclusive_minimum`
- **String:** `min_length`, `max_length`, `pattern`
- **Array:** `min_items`, `max_items`
- **Object:** `required`
- **Format:** `format`
- **Metadata:** `title`, `description`, `default`, `examples`
- **Definitions:** `defs` (`$defs`)

See the [API reference](api/types.md) for each field's description and JSON Schema spec link.

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
- [Format Validators](formats.md) - Add validation for `format` values
- [API Reference](api/types.md) - Full API docs for schema types
