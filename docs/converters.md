# Creating Models from Schemas

This guide shows how to convert JSON Schema into Pydantic models for type-safe validation.

## Basic Conversion

Convert a simple schema to a Pydantic model:

```python title="basic_conversion.py"
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
|------------------------------|----------------------------------------------|---------------------------------------------|
| `Schema(...)`                | Python code that builds schemas directly     | `Schema(type=DataType.OBJECT)`              |
| `Schema.model_validate(...)` | JSON-like data from files, APIs, or literals | `Schema.model_validate({"type": "object"})` |

Both approaches are equivalent after validation.

### Using `Schema`

```python title="schema_class.py"
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

```python title="schema_dict.py"
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

| JSON Schema input                           | Pydantic result                             | Example result                      |
|---------------------------------------------|---------------------------------------------|-------------------------------------|
| root `{"type": "object"}`                   | generated `BaseModel` subclass              | empty model with extra handling     |
| object property without `properties`        | untyped dictionary field                    | `metadata: dict[str, Any]`          |
| `{"type": "string"}`                        | `str`                                       | `name: str`                         |
| `{"type": "integer"}`                       | `int`                                       | `age: int`                          |
| `{"type": "number"}`                        | `float`                                     | `score: float`                      |
| `{"type": "boolean"}`                       | `bool`                                      | `is_active: bool`                   |
| `{"type": "null"}`                          | `None` type                                 | `value: None`                       |
| `{"type": ["string", "integer"]}`           | union annotation                            | `str` or `int`                      |
| `{"type": "array", "items": {...}}`         | typed `list[...]`                           | `tags: list[str]`                   |
| `{"enum": [...]}`                           | `Literal[...]`                              | `Literal["draft", "published"]`     |
| `{"const": "active"}`                       | single-value `Literal[...]`                 | `Literal["active"]`                 |
| `anyOf` or `oneOf`                          | union annotation                            | `str` or `int`                      |
| `allOf`                                     | generated model inheritance or nested model | combined Pydantic model             |
| nested object property                      | nested generated model                      | `post.author.name`                  |
| property with `$ref: "#/$defs/Person"`      | model generated from `$defs.Person`         | shared `Person` field type          |
| `$ref` passed through `refs`                | existing Pydantic model                     | existing `Address` class            |
| root `additionalProperties: false`          | generated model forbids extra fields        | `extra_forbidden` validation        |
| field `additionalProperties: {...}`         | typed mapping values                        | `dict[str, int]`                    |
| `required` entry                            | required Pydantic field                     | `Field required` validation         |
| `default`                                   | field default                               | omitted input uses default value    |
| `minimum`, `maximum`, `multipleOf`          | numeric constraints                         | `ge`, `le`, `multiple_of`           |
| `minLength`, `maxLength`                    | string length constraints                   | `min_length`, `max_length`          |
| `minItems`, `maxItems`                      | list length constraints                     | `min_length`, `max_length`          |
| `format` with validators                    | configured format validation                | see [Format Validators](formats.md) |
| `title`, `model_name`, `default_model_name` | generated class name                        | `User`, `CustomUser`, `Model`       |

## Common Conversions

The sections below show the most common conversions in runnable examples.

### Object Schemas

Object conversion depends on where the schema appears.

| Schema position | Input                                               | Result                                |
|-----------------|-----------------------------------------------------|---------------------------------------|
| root schema     | `{"type": "object"}`                                | generated model with no fields        |
| root schema     | `{"type": "object", "properties": ...}`             | generated model with fields           |
| root schema     | `{"type": "object", "additionalProperties": false}` | generated model with `extra="forbid"` |
| property schema | `{"type": "object"}`                                | `dict[str, Any]` field                |
| property schema | `{"type": "object", "properties": ...}`             | nested generated model                |

For a property schema, plain `{"type": "object"}` means the value must be a JSON object, so the
field becomes `dict[str, Any]`. It is not `Any`, because non-object values like strings, numbers,
arrays, and `null` are rejected.

!!! warning "Current behavior"
    A property schema with `{"type": "object", "additionalProperties": false}` currently also
    becomes `dict[str, Any]`. It validates that the value is a dictionary, but it does not enforce
    an empty dictionary.

### Objects

Object schemas with `properties` become Pydantic models:

```python title="object_schema.py"
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

```python title="array_schema.py"
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

```python title="enum_schema.py"
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

```python title="union_schema.py"
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

## Nested Objects

Nested schemas automatically create nested models:

```python title="nested_objects.py"
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

```python title="schema_references.py"
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

Pass existing Pydantic models through `refs` when a `$ref` should resolve to a model you already
have:

```python title="prebuilt_references.py"
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

```python title="validation_constraints.py"
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

```python title="additional_properties.py"
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
|---------:|-----------------------|-----------------------------------------------|-----------------------------------------------|
|        1 | `model_name` argument | passed to `to_model()` or `convert_schema()`  | `to_model(schema, model_name="User")`         |
|        2 | schema `title`        | no `model_name` is provided                   | `{"title": "User"}`                           |
|        3 | `default_model_name`  | neither `model_name` nor `title` is available | `SchemaConverter(default_model_name="Model")` |

This matters because the model name appears in validation errors, `repr()`, and debugging output.

```python title="model_names.py"
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

```python title="schema_converter.py"
from pydantic_jsonschema import Schema, SchemaConverter

converter = SchemaConverter(
    default_model_name="MyModel",
    refs={},
    format_validators={},
)
schema = Schema.model_validate({})

Model = converter.convert_schema(schema, model_name="SpecificName")
print(Model.__name__)
#> SpecificName
```

!!! warning "Caching Behavior"
    Be careful using `SchemaConverter` directly. The converter maintains state for caching and
    reference resolution across multiple schema conversions.

## Common Patterns

| Need                                      | Use                                  | Why                                                          |
|-------------------------------------------|--------------------------------------|--------------------------------------------------------------|
| One generated model                       | `to_model(schema, model_name="...")` | Shortest path and clear class name                           |
| Existing model for a `$ref`               | `refs={"#/$defs/Name": Model}`       | Keeps generated models connected to your own classes         |
| Repeated conversions with shared settings | `SchemaConverter(...)`               | Reuses `refs`, `format_validators`, and `default_model_name` |
| Clear validation errors                   | `model_name` or schema `title`       | Avoids generic `Model` in error output                       |
| Custom `format` handling                  | `format_validators`                  | Adds validation for strings or domain-specific values        |

## Next Steps

- [Format Validators](formats.md) - Add custom validation for special formats
- [Examples](examples.md) - See real-world applications
