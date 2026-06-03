# Creating Models from Schemas

This guide shows how to convert JSON Schema into Pydantic models for type-safe validation.

## Basic Conversion

Convert a simple schema to a Pydantic model:

```python title="basic_conversion.py"
from pydantic_jsonschema import Schema, to_model

schema = Schema.model_validate({
    "type": "object",
    "properties": {
        "username": {"type": "string"},
        "email": {"type": "string"}
    },
    "required": ["username"]
})

User = to_model(schema, model_name="User")

# Use it like any Pydantic model
user = User(username="alice", email="alice@example.com")
print(user.username)
#> alice
```

The `to_model()` function is a convenience wrapper that creates a model with strict validation.

## Defining Schemas

There are two ways to define schemas:

### Using Schema class

```python
from pydantic_jsonschema import DataType, Schema

schema = Schema(
    type=DataType.OBJECT,
    properties={
        "name": Schema(type=DataType.STRING),
        "age": Schema(type=DataType.INTEGER, minimum=0),
    },
    required=["name"],
)
```

### From dict with `model_validate`

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

Both approaches are equivalent.

## Schema Types

### Objects

Object schemas become Pydantic models:

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
```

### Arrays

Arrays become typed lists:

```python
from pydantic_jsonschema import Schema, to_model

schema = Schema.model_validate({
    "type": "object",
    "properties": {
        "tags": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1
        }
    }
})

Model = to_model(schema)

data = Model(tags=["python", "pydantic"])
print(data.tags)
#> ['python', 'pydantic']
```

### Enums

Enums become Literal types:

```python
from pydantic import ValidationError

from pydantic_jsonschema import Schema, to_model

schema = Schema.model_validate({
    "type": "object",
    "properties": {
        "status": {
            "type": "string",
            "enum": ["draft", "published", "archived"]
        }
    }
})

Article = to_model(schema, model_name="Article")

article = Article(status="published")

try:
    Article(status="invalid")
except ValidationError as e:
    print(e)
    """
    1 validation error for Article
    status
      Input should be 'draft', 'published' or 'archived' [type=literal_error, input_value='invalid', input_type=str]
        For further information visit https://errors.pydantic.dev/2.12/v/literal_error
    """
```

### Unions (anyOf/oneOf)

Union schemas become Union types:

```python
from pydantic_jsonschema import Schema, to_model

schema = Schema.model_validate({
    "type": "object",
    "properties": {
        "value": {
            "anyOf": [
                {"type": "string"},
                {"type": "integer"}
            ]
        }
    }
})

Model = to_model(schema)

m1 = Model(value="hello")  # ✓
m2 = Model(value=42)  # ✓
```

## Nested Objects

Nested schemas automatically create nested models:

```python
from pydantic_jsonschema import Schema, to_model

schema = Schema.model_validate({
    "type": "object",
    "properties": {
        "author": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "email": {"type": "string"}
            },
            "required": ["name"]
        }
    }
})

BlogPost = to_model(schema, model_name="BlogPost")

post = BlogPost(author={"name": "Alice", "email": "alice@example.com"})
print(post.author.name)
#> Alice
```

## Schema References

Use `$ref` to reuse schema definitions:

```python
from pydantic_jsonschema import Schema, to_model

schema = Schema.model_validate({
    "type": "object",
    "properties": {
        "author": {"$ref": "#/$defs/Person"},
        "editor": {"$ref": "#/$defs/Person"}
    },
    "$defs": {
        "Person": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "email": {"type": "string"}
            },
            "required": ["name"]
        }
    }
})

Document = to_model(schema, model_name="Document")

doc = Document(
    author={"name": "Alice", "email": "alice@example.com"},
    editor={"name": "Bob", "email": "bob@example.com"},
)
```

Both `author` and `editor` reference the same `Person` model definition.

## Pre-built References

Provide existing Pydantic models for references:

```python
from pydantic import BaseModel

from pydantic_jsonschema import Schema, to_model


class Address(BaseModel):
    street: str
    city: str
    country: str


schema = Schema.model_validate({
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "address": {"$ref": "#/$defs/Address"}
    }
})

# Use the pre-built Address model
Person = to_model(schema, refs={"#/$defs/Address": Address})

person = Person(
    name="Alice",
    address=Address(street="123 Main St", city="NYC", country="USA")
)
print(type(person.address))
#> <class '__main__.Address'>
```

## Validation Constraints

Schema constraints map to Pydantic validators:

```python
from pydantic import ValidationError

from pydantic_jsonschema import Schema, to_model

schema = Schema.model_validate({
    "type": "object",
    "properties": {
        "username": {
            "type": "string",
            "minLength": 3,
            "maxLength": 20
        },
        "age": {
            "type": "integer",
            "minimum": 18,
            "maximum": 120
        },
        "score": {
            "type": "number",
            "multipleOf": 0.5
        }
    }
})

User = to_model(schema, model_name="User")

user = User(username="alice", age=25, score=4.5)

try:
    User(username="ab")
except ValidationError as e:
    print(e)
    """
    1 validation error for User
    username
      String should have at least 3 characters [type=string_too_short, input_value='ab', input_type=str]
        For further information visit https://errors.pydantic.dev/2.12/v/string_too_short
    """

try:
    User(age=17)
except ValidationError as e:
    print(e)
    """
    1 validation error for User
    age
      Input should be greater than or equal to 18 [type=greater_than_equal, input_value=17, input_type=int]
        For further information visit https://errors.pydantic.dev/2.12/v/greater_than_equal
    """
```

## Additional Properties

Control whether extra fields are allowed:

```python
from pydantic import ValidationError

from pydantic_jsonschema import Schema, to_model

# Forbid extra fields
schema = Schema.model_validate({
    "type": "object",
    "properties": {
        "name": {"type": "string"}
    },
    "additionalProperties": False
})

Strict = to_model(schema)

try:
    Strict(name="Alice", age=30)
except ValidationError as e:
    print(e)
    """
    1 validation error for Model
    age
      Extra inputs are not permitted [type=extra_forbidden, input_value=30, input_type=int]
        For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
    """


# Allow extra fields
schema = Schema.model_validate({
    "type": "object",
    "properties": {
        "name": {"type": "string"}
    },
    "additionalProperties": True
})

Flexible = to_model(schema)
data = Flexible(name="Alice", age=30)  # ✓
```

## Model Names

Every generated model needs a class name. The name is resolved in this order:

1. **`model_name` argument** — explicit name passed to `to_model()` or `convert_schema()`
2. **Schema `title`** — the `"title"` field from the JSON Schema
3. **`default_model_name`** — fallback set on `SchemaConverter` (defaults to `"Model"`)

This matters because the model name appears in validation errors, `repr()`, and debugging output.
Without `model_name`, a schema without `title` produces a generic `Model` — unhelpful when you have several of them.

```python
from pydantic import ValidationError

from pydantic_jsonschema import Schema, to_model

schema = Schema.model_validate({
    "type": "object",
    "properties": {
        "name": {"type": "string"}
    },
    "required": ["name"]
})

# Without model_name — generic "Model" in errors
Generic = to_model(schema)

try:
    Generic()
except ValidationError as e:
    print(e)
    """
    1 validation error for Model
    name
      Field required [type=missing, input_value={}, input_type=dict]
        For further information visit https://errors.pydantic.dev/2.12/v/missing
    """

# With model_name — clear "User" in errors
User = to_model(schema, model_name="User")

try:
    User()
except ValidationError as e:
    print(e)
    """
    1 validation error for User
    name
      Field required [type=missing, input_value={}, input_type=dict]
        For further information visit https://errors.pydantic.dev/2.12/v/missing
    """
```

Schema `title` works the same way — if present, it becomes the model name automatically:

```python
from pydantic_jsonschema import Schema, to_model

schema = Schema.model_validate({
    "title": "User",
    "type": "object",
    "properties": {
        "name": {"type": "string"}
    }
})

UserModel = to_model(schema)  # Named "User" from title
print(UserModel.__name__)
#> User

# model_name overrides title
CustomModel = to_model(schema, model_name="CustomUser")
print(CustomModel.__name__)
#> CustomUser
```

## Using SchemaConverter

For more control, use the `SchemaConverter` class directly:

```python
from pydantic_jsonschema import Schema, SchemaConverter

converter = SchemaConverter(
    default_model_name="MyModel",   # Default for models without title
    refs={},                        # Pre-built reference models
    format_validators={}            # Custom format validators
)
schema = Schema.model_validate({})

Model = converter.convert_schema(schema, model_name="SpecificName")
print(Model.__name__)
#> SpecificName
```

!!! warning "Caching Behavior"
    Be careful using `SchemaConverter` directly. The converter maintains state for caching and reference resolution across multiple schema conversions.

## Next Steps

- [Format Validators](formats.md) - Add custom validation for special formats
- [Examples](examples.md) - See real-world applications
