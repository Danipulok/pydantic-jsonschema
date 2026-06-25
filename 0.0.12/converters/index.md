# Creating Models from Schemas

This guide shows how to convert JSON Schema into Pydantic models for type-safe validation.

## Basic Conversion

Convert a simple schema to a Pydantic model:

basic_conversion.py

```python
from pydantic_jsonschema import Schema, to_model

schema = Schema.model_validate(
    {
        "type": "object",
        "properties": {
            "username": {"type": "string"},
            "email": {"type": "string"},
        },
        "required": ["username"],
    }
)

User = to_model(schema, model_name="User")

user = User(username="alice", email="alice@example.com")
print(user.username)
#> alice
```

The `to_model()` function is a convenience wrapper that creates a model with strict validation.

## Defining Schemas

You can define schemas with the `Schema` class or validate a plain `dict` into `Schema`.

| Input style                  | Best for                                     | Example                                     |
| ---------------------------- | -------------------------------------------- | ------------------------------------------- |
| `Schema(...)`                | Python code that builds schemas directly     | `Schema(type=DataType.OBJECT)`              |
| `Schema.model_validate(...)` | JSON-like data from files, APIs, or literals | `Schema.model_validate({"type": "object"})` |

Both approaches are equivalent after validation.

### Using `Schema`

schema_class.py

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
```

### Using `model_validate()`

schema_dict.py

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
```

## Conversion Map

Use this table as the quick reference for what each JSON Schema feature becomes.

| JSON Schema input                            | Pydantic result                             | Example result                                                                         |
| -------------------------------------------- | ------------------------------------------- | -------------------------------------------------------------------------------------- |
| root `{"type": "object"}`                    | generated `BaseModel` subclass              | empty model with extra handling                                                        |
| object property without `properties`         | untyped dictionary field                    | `metadata: dict[str, Any]`                                                             |
| `{"type": "string"}`                         | `str`                                       | `name: str`                                                                            |
| `{"type": "integer"}`                        | `int`                                       | `age: int`                                                                             |
| `{"type": "number"}`                         | `float`                                     | `score: float`                                                                         |
| `{"type": "boolean"}`                        | `bool`                                      | `is_active: bool`                                                                      |
| `{"type": "null"}`                           | `None` type                                 | `value: None`                                                                          |
| `{"type": ["string", "integer"]}`            | union annotation                            | `str` or `int`                                                                         |
| `{"type": "array", "items": {...}}`          | typed `list[...]`                           | `tags: list[str]`                                                                      |
| `{"enum": [...]}`                            | `Literal[...]`                              | `Literal["draft", "published"]`                                                        |
| `{"const": "active"}`                        | single-value `Literal[...]`                 | `Literal["active"]`                                                                    |
| `anyOf`                                      | union annotation                            | `str` or `int`                                                                         |
| `oneOf`                                      | discriminated or exactly-one-branch union   | tagged union or ambiguous rejected                                                     |
| `allOf`                                      | generated model inheritance or nested model | combined Pydantic model                                                                |
| nested object property                       | nested generated model                      | `post.author.name`                                                                     |
| property with `$ref: "#/$defs/Person"`       | model generated from `$defs.Person`         | shared `Person` field type                                                             |
| `$ref` passed through `refs`                 | existing Pydantic model                     | existing `Address` class                                                               |
| root object + `additionalProperties: false`  | generated model with `extra="forbid"`       | unknown fields rejected                                                                |
| root object + `additionalProperties: {...}`  | typed dictionary root model                 | `RootModel[dict[str, int]]`                                                            |
| field object + `additionalProperties: false` | generated empty model field                 | only `{}` is valid                                                                     |
| field object + `additionalProperties: {...}` | typed dictionary field                      | `dict[str, int]`                                                                       |
| `required` entry                             | required Pydantic field                     | `Field required` validation                                                            |
| `default`                                    | field default                               | omitted input uses default value                                                       |
| `minimum`, `maximum`, `multipleOf`           | numeric constraints                         | `ge`, `le`, `multiple_of`                                                              |
| `minLength`, `maxLength`                     | string length constraints                   | `min_length`, `max_length`                                                             |
| `pattern`                                    | string regex constraint                     | `pattern`                                                                              |
| `minItems`, `maxItems`                       | list length constraints                     | `min_length`, `max_length`                                                             |
| `uniqueItems: true`                          | array uniqueness constraint                 | `AfterValidator` rejecting dupes                                                       |
| `contains`, `minContains`, `maxContains`     | array match-count constraint                | `Contains` validator                                                                   |
| `prefixItems`                                | positional (tuple-style) array validation   | `PrefixItems` validator                                                                |
| `not`                                        | value must not match the subschema          | `Not` validator                                                                        |
| `if` / `then` / `else`                       | conditional subschema application           | `IfThenElse` validator                                                                 |
| `minProperties`, `maxProperties`             | object property-count constraints           | `before` validator / `dict` length                                                     |
| `dependentRequired`                          | conditionally required properties           | `before` validator                                                                     |
| `dependentSchemas`                           | conditionally applied object subschema      | `DependentSchemas` validator                                                           |
| `patternProperties`                          | regex-keyed property-value subschemas       | `PatternProperties` validator                                                          |
| `propertyNames`                              | schema every property name must match       | `PropertyNames` validator                                                              |
| `format` with validators                     | configured format validation                | see [Formats](https://danipulok.github.io/pydantic-jsonschema/0.0.12/formats/index.md) |
| `title`, `model_name`, `default_model_name`  | generated class name                        | `User`, `CustomUser`, `Model`                                                          |

## Unsupported Keywords

All JSON Schema 2020-12 validation and applicator keywords are now enforced on conversion. Unknown or custom keywords are still parsed and preserved on the `Schema` model (`extra="allow"`) but do not affect the generated model.

## Known Limitations

- `$defs` is only allowed in the root schema — nested `$defs` raises `SchemaConversionError`.
- Only local references (`#/$defs/...`) and pre-built `refs` models are resolved — external `$ref` URLs are not fetched.
- `pattern` is compiled by Pydantic's default Rust regex engine, which does not support ECMA-262 lookarounds — such patterns fail at model build time.
- In a multi-type union (`{"type": ["object", "string"], "properties": {...}}`) the `object` branch is validated as a plain `dict[str, Any]` — sibling `properties` are not applied.
- On objects that declare both `properties` and a schema-valued `additionalProperties`, extra fields are accepted (`extra="allow"`) but their values are not validated against the `additionalProperties` schema.
- `format` is metadata unless a matching entry is passed in `formats` — see [Formats](https://danipulok.github.io/pydantic-jsonschema/0.0.12/formats/index.md). Built-in aliases cover all 19 spec-defined formats; `idn-*` formats use the stdlib IDNA 2003 codec and `regex` uses the Python `re` dialect (see the differences from the specification in [Formats](https://danipulok.github.io/pydantic-jsonschema/0.0.12/formats/index.md)).
- `not` is only as precise as the converter's coverage of its subschema. A subschema that maps to `Any` (an empty schema, or `required` without `type` / `properties`) matches every value, so `not` then rejects everything.
- `patternProperties` validates the values of matching property names, but combined with `additionalProperties: false` a pattern-matched extra key is still rejected by `extra="forbid"` (the generated model cannot express "allow keys matching this regex").

## Common Conversions

The sections below show the most common conversions in runnable examples.

### Object Schemas

Object conversion depends on where the schema appears.

| Schema position | Input                                               | Result                                |
| --------------- | --------------------------------------------------- | ------------------------------------- |
| root schema     | `{"type": "object"}`                                | generated model with no fields        |
| root schema     | `{"type": "object", "properties": ...}`             | generated model with fields           |
| root schema     | `{"type": "object", "additionalProperties": false}` | generated model with `extra="forbid"` |
| root schema     | `{"type": "object", "additionalProperties": {...}}` | typed dictionary root model           |
| property schema | `{"type": "object"}`                                | `dict[str, Any]` field                |
| property schema | `{"type": "object", "properties": ...}`             | nested generated model                |
| property schema | `{"type": "object", "additionalProperties": false}` | only an empty object is valid         |

For a property schema, plain `{"type": "object"}` means the value must be a JSON object, so the field becomes `dict[str, Any]`. It is not `Any`, because non-object values like strings, numbers, arrays, and `null` are rejected.

### Objects

Object schemas with `properties` become Pydantic models:

object_schema.py

```python
from pydantic_jsonschema import Schema, to_model

schema = Schema.model_validate(
    {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "views": {"type": "integer", "minimum": 0},
        },
        "required": ["title"],
    }
)

Post = to_model(schema, model_name="Post")

post = Post(title="Hello World", views=100)
print(post.title)
#> Hello World
```

### Arrays

Arrays become typed lists when `items` is present:

array_schema.py

```python
from pydantic_jsonschema import Schema, to_model

schema = Schema.model_validate(
    {
        "type": "object",
        "properties": {
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
            }
        },
    }
)

Model = to_model(schema)

data = Model(tags=["python", "pydantic"])
print(data.tags)
#> ['python', 'pydantic']
```

### Enums

Enums become `Literal` types:

enum_schema.py

```python
from pydantic import ValidationError

from pydantic_jsonschema import Schema, to_model

schema = Schema.model_validate(
    {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "enum": ["draft", "published", "archived"],
            }
        },
    }
)

Article = to_model(schema, model_name="Article")

article = Article(status="published")
print(article.status)
#> published

try:
    Article(status="invalid")
except ValidationError as er:
    print(type(er).__name__)
    #> ValidationError
```

### Unions

`anyOf`, `oneOf`, and list-valued `type` become union annotations:

union_schema.py

```python
from pydantic_jsonschema import Schema, to_model

schema = Schema.model_validate(
    {
        "type": "object",
        "properties": {
            "value": {
                "anyOf": [
                    {"type": "string"},
                    {"type": "integer"},
                ]
            }
        },
    }
)

Model = to_model(schema)

text_data = Model(value="hello")
number_data = Model(value=42)

print(text_data.value)
#> hello
print(number_data.value)
#> 42
```

`oneOf` requires exactly one matching branch

`anyOf` maps to a plain `Union` and accepts a value when *any* branch matches. `oneOf` additionally enforces JSON Schema semantics: a value matching more than one branch (or none) is rejected. The generated model also dumps the union back as `oneOf` in `model_json_schema()`.

one_of_schema.py

```python
from pydantic import ValidationError

from pydantic_jsonschema import Schema, to_model

schema = Schema.model_validate(
    {
        "type": "object",
        "properties": {
            "value": {
                "oneOf": [
                    {"type": "integer"},
                    {"type": "number"},
                ]
            }
        },
    }
)

Model = to_model(schema)

print(Model(value=1.5).value)
#> 1.5

try:
    # `1` matches both `integer` and `number` -> not exactly one branch
    Model(value=1)
except ValidationError as er:
    print(type(er).__name__)
    #> ValidationError

print(Model.model_json_schema()["properties"]["value"]["oneOf"])
#> [{'type': 'integer'}, {'type': 'number'}]
```

### Discriminated `oneOf`

When every `oneOf` branch is an object schema tagged by a shared property — a required field whose value is a single constant (`const` or single-value `enum`) with a distinct value per branch — the union maps to a native Pydantic [discriminated union](https://docs.pydantic.dev/latest/concepts/unions/#discriminated-unions) via `Field(discriminator=...)`.

Pydantic then routes to a single branch by the tag value instead of probing every branch: validation is faster and errors point at the selected branch rather than reporting an ambiguous match. When the branches do not form a tagged union, the converter falls back to the exactly-one-branch validator above.

discriminated_one_of.py

```python
from pydantic import ValidationError

from pydantic_jsonschema import Schema, to_model

schema = Schema.model_validate(
    {
        "type": "object",
        "properties": {
            "pet": {
                "oneOf": [
                    {
                        "type": "object",
                        "title": "Cat",
                        "properties": {
                            "type": {"const": "cat"},
                            "meow": {"type": "boolean"},
                        },
                        "required": ["type", "meow"],
                    },
                    {
                        "type": "object",
                        "title": "Dog",
                        "properties": {
                            "type": {"const": "dog"},
                            "bark": {"type": "boolean"},
                        },
                        "required": ["type", "bark"],
                    },
                ]
            }
        },
    }
)

Model = to_model(schema)

pet = Model(pet={"type": "cat", "meow": True}).pet
# the `cat` tag routed to the generated `Cat` model
print(type(pet).__name__)
#> Cat

try:
    # `fish` matches no branch tag -> rejected by the discriminator
    Model(pet={"type": "fish"})
except ValidationError as er:
    print(er.errors()[0]["type"])
    #> union_tag_invalid

print(Model.model_json_schema()["properties"]["pet"]["oneOf"])
#> [{'$ref': '#/$defs/Cat'}, {'$ref': '#/$defs/Dog'}]
```

## Nested Objects

Nested schemas automatically create nested models:

nested_objects.py

```python
from pydantic_jsonschema import Schema, to_model

schema = Schema.model_validate(
    {
        "type": "object",
        "properties": {
            "author": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "email": {"type": "string"},
                },
                "required": ["name"],
            }
        },
    }
)

BlogPost = to_model(schema, model_name="BlogPost")

post = BlogPost(author={"name": "Alice", "email": "alice@example.com"})
print(post.author.name)
#> Alice
```

## Schema References

Use `$ref` to reuse schema definitions:

schema_references.py

```python
from pydantic_jsonschema import Schema, to_model

schema = Schema.model_validate(
    {
        "type": "object",
        "properties": {
            "author": {"$ref": "#/$defs/Person"},
            "editor": {"$ref": "#/$defs/Person"},
        },
        "$defs": {
            "Person": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "email": {"type": "string"},
                },
                "required": ["name"],
            }
        },
    }
)

Document = to_model(schema, model_name="Document")

document = Document(
    author={"name": "Alice", "email": "alice@example.com"},
    editor={"name": "Bob", "email": "bob@example.com"},
)

print(document.author.name)
#> Alice
```

Both `author` and `editor` reference the same `Person` model definition.

## Pre-built References

Pass existing Pydantic models through `refs` when a `$ref` should resolve to a model you already have:

prebuilt_references.py

```python
from pydantic import BaseModel

from pydantic_jsonschema import Schema, to_model


class Address(BaseModel):
    street: str
    city: str
    country: str


schema = Schema.model_validate(
    {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "address": {"$ref": "#/$defs/Address"},
        },
    }
)

Person = to_model(schema, refs={"#/$defs/Address": Address})

person = Person(
    name="Alice",
    address=Address(street="123 Main St", city="NYC", country="USA"),
)
print(type(person.address) is Address)
#> True
```

## Validation Constraints

Schema constraints map to Pydantic field validation:

validation_constraints.py

```python
from pydantic import ValidationError

from pydantic_jsonschema import Schema, to_model

schema = Schema.model_validate(
    {
        "type": "object",
        "properties": {
            "username": {
                "type": "string",
                "minLength": 3,
                "maxLength": 20,
            },
            "age": {
                "type": "integer",
                "minimum": 18,
                "maximum": 120,
            },
            "score": {
                "type": "number",
                "multipleOf": 0.5,
            },
        },
    }
)

User = to_model(schema, model_name="User")

user = User(username="alice", age=25, score=4.5)
print(user.score)
#> 4.5

try:
    User(username="ab")
except ValidationError as er:
    print(type(er).__name__)
    #> ValidationError
```

## Additional Properties

Control whether extra fields are allowed:

additional_properties.py

```python
from pydantic import ValidationError

from pydantic_jsonschema import Schema, to_model

strict_schema = Schema.model_validate(
    {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
        },
        "additionalProperties": False,
    }
)

Strict = to_model(strict_schema)

try:
    Strict(name="Alice", age=30)
except ValidationError as er:
    print(type(er).__name__)
    #> ValidationError

flexible_schema = Schema.model_validate(
    {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
        },
        "additionalProperties": True,
    }
)

Flexible = to_model(flexible_schema)
data = Flexible(name="Alice", age=30)
print(data.age)
#> 30
```

## Model Names

Every generated model needs a class name. The name is resolved in this order:

| Priority | Source                | Used when                                     | Example                                       |
| -------- | --------------------- | --------------------------------------------- | --------------------------------------------- |
| 1        | `model_name` argument | passed to `to_model()` or `convert_schema()`  | `to_model(schema, model_name="User")`         |
| 2        | schema `title`        | no `model_name` is provided                   | `{"title": "User"}`                           |
| 3        | `default_model_name`  | neither `model_name` nor `title` is available | `SchemaConverter(default_model_name="Model")` |

This matters because the model name appears in validation errors, `repr()`, and debugging output.

model_names.py

```python
from pydantic_jsonschema import Schema, to_model

schema = Schema.model_validate(
    {
        "title": "User",
        "type": "object",
        "properties": {
            "name": {"type": "string"},
        },
    }
)

UserModel = to_model(schema)
print(UserModel.__name__)
#> User

CustomModel = to_model(schema, model_name="CustomUser")
print(CustomModel.__name__)
#> CustomUser
```

## Using `SchemaConverter`

For more control, use the `SchemaConverter` class directly:

schema_converter.py

```python
from pydantic_jsonschema import Schema, SchemaConverter

converter = SchemaConverter(
    default_model_name="MyModel",
    refs={},
    formats={},
)
schema = Schema.model_validate({})

Model = converter.convert_schema(schema, model_name="SpecificName")
print(Model.__name__)
#> SpecificName
```

Caching Behavior

Be careful using `SchemaConverter` directly. The converter maintains state for caching and reference resolution across multiple schema conversions.

## Common Patterns

| Need                                      | Use                                  | Why                                                   |
| ----------------------------------------- | ------------------------------------ | ----------------------------------------------------- |
| One generated model                       | `to_model(schema, model_name="...")` | Shortest path and clear class name                    |
| Existing model for a `$ref`               | `refs={"#/$defs/Name": Model}`       | Keeps generated models connected to your own classes  |
| Repeated conversions with shared settings | `SchemaConverter(...)`               | Reuses `refs`, `formats`, and `default_model_name`    |
| Clear validation errors                   | `model_name` or schema `title`       | Avoids generic `Model` in error output                |
| Custom `format` handling                  | `formats`                            | Adds validation for strings or domain-specific values |

## Next Steps

- [Formats](https://danipulok.github.io/pydantic-jsonschema/0.0.12/formats/index.md) - Add custom validation for special formats
- [Examples](https://danipulok.github.io/pydantic-jsonschema/0.0.12/examples/index.md) - See real-world applications
