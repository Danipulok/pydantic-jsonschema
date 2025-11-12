# Creating Models from Schemas

This guide shows how to convert JSON Schema into Pydantic models for type-safe validation.

## Basic Conversion

Convert a simple schema to a Pydantic model:

```python
from pydantic_jsonschema import to_model, Schema

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
print(user.username)  #> alice
```

*This example is complete and can be run as-is.*

The `to_model()` function is a convenience wrapper that creates a model with strict validation.

## Defining Schemas

There are two ways to define schemas:

### Using Schema class

```python
from pydantic_jsonschema import Schema, DataType

schema = Schema(
    type=DataType.OBJECT,
    properties={
        "name": Schema(type=DataType.STRING),
        "age": Schema(type=DataType.INTEGER, minimum=0)
    },
    required=["name"]
)
```

### From dict with `model_validate`

```python
from pydantic_jsonschema import Schema

schema = Schema.model_validate({
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "age": {"type": "integer", "minimum": 0}
    },
    "required": ["name"]
})
```

Both approaches are equivalent. Use whichever suits your workflow.

## Schema Types

### Objects

Object schemas become Pydantic models:

```python
from pydantic_jsonschema import Schema, to_model

schema = Schema.model_validate({
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "views": {"type": "integer", "minimum": 0}
    },
    "required": ["title"]
})

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
print(data.tags)  #> ["python", "pydantic"]
```

### Enums

Enums become Literal types:

```python
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

article = Article(status="published")  # ✓
# Article(status="invalid")  # ✗ ValidationError
```

*This example is complete and can be run as-is.*

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
m2 = Model(value=42)       # ✓
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
print(post.author["name"])  #> Alice
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
    editor={"name": "Bob", "email": "bob@example.com"}
)
```

Both `author` and `editor` reference the same `Person` model definition.

## Pre-built References

Provide existing Pydantic models for references:

```python
from pydantic_jsonschema import Schema, to_model

from pydantic import BaseModel

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
```

## Validation Constraints

Schema constraints map to Pydantic validators:

```python
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

# User(username="ab")  # ✗ Too short
# User(age=17)         # ✗ Below minimum
user = User(username="alice", age=25, score=4.5)  # ✓
```

## Additional Properties

Control whether extra fields are allowed:

```python
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
# Strict(name="Alice", age=30)  # ✗ ValidationError

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

Models are named based on the schema's `title`, or you can provide a custom name:

```python
from pydantic_jsonschema import Schema, to_model

# Using schema title
schema = Schema.model_validate({
    "title": "User",
    "type": "object",
    "properties": {
        "name": {"type": "string"}
    }
})

UserModel = to_model(schema)  # Named "User" from title

# Custom name
CustomModel = to_model(schema, model_name="CustomUser")
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
```

!!! warning "Caching Behavior"
    Caching is used for all refs and models, so be careful when using `SchemaConverter` directly. The converter maintains state for caching and reference resolution across multiple schema conversions.

## Next Steps

- [Lax vs Strict](converters.md) — Choose validation mode for your use case
- [Format Validators](formats.md) — Add custom validation for special formats
- [Examples](examples.md) — See real-world applications
