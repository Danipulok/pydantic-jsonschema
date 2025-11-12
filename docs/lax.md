# Lax Validation

Lax validation provides automatic type coercion for flexible validation of external data sources like LLMs, CSVs, and APIs.

## Overview

Use `to_lax_model()` when working with data that might have type inconsistencies. Lax validation automatically coerces values to the expected types.

```python
from pydantic_jsonschema import to_lax_model, Schema

schema = Schema.model_validate({
    "type": "object",
    "properties": {
        "age": {"type": "integer"}
    }
})

User = to_lax_model(schema)
user = User(age="30")  # ✓ Coerced to integer 30
print(user.age)  #> 30
```

*This example is complete and can be run as-is.*

## When to Use Lax Validation

**Use lax when:**

- LLM outputs (often return strings)
- CSV/spreadsheet imports (everything is strings)
- External APIs with inconsistent types
- User input that needs normalization

**Use strict when:**

- Validating API requests/responses
- Internal data structures with controlled types
- Configuration files you manage
- When type safety is critical

## Coercion Rules

### String Coercion

```python
from pydantic_jsonschema import to_lax_model, Schema

schema = Schema.model_validate({
    "type": "object",
    "properties": {
        "name": {"type": "string"}
    }
})

Product = to_lax_model(schema)

# None → empty string
Product(name=None)  # name=""

# Any value → str(value)
Product(name=123)   # name="123"
```

### Integer Coercion

```python
# String → int
Product(count="42")   # count=42

# Float → int (truncated)
Product(count=42.9)   # count=42

# Invalid strings raise ValidationError
# Product(count="abc")  # ✗ ValidationError
```

### Float Coercion

```python
# String → float
Product(price="19.99")   # price=19.99

# Integer → float
Product(price=20)        # price=20.0
```

### List Coercion

```python
# None → empty list
Product(tags=None)  # tags=[]

# Comma-separated string → list
Product(tags="python, pydantic, json")  # tags=["python", "pydantic", "json"]

# JSON string → list
Product(tags='["a", "b", "c"]')  # tags=["a", "b", "c"]
```

## Real-World Example: LLM Outputs

LLMs often return data with type inconsistencies:

```python
from pydantic_jsonschema import to_lax_model, Schema

schema = Schema.model_validate({
    "type": "object",
    "properties": {
        "sentiment": {
            "type": "string",
            "enum": ["positive", "negative", "neutral"]
        },
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "keywords": {"type": "array", "items": {"type": "string"}},
        "word_count": {"type": "integer"}
    },
    "required": ["sentiment", "confidence"]
})

Analysis = to_lax_model(schema, model_name="Analysis")

# LLM returns everything as strings
llm_response = {
    "sentiment": "positive",
    "confidence": "0.87",              # Should be float
    "keywords": "innovation, growth",  # Should be array
    "word_count": "342"                # Should be int
}

# Lax validation handles it gracefully
analysis = Analysis.model_validate(llm_response)

print(analysis.confidence)   #> 0.87 (float)
print(analysis.keywords)     #> ["innovation", "growth"] (list)
print(analysis.word_count)   #> 342 (int)
```

*This example is complete and can be run as-is.*

## Real-World Example: CSV Import

CSV data is always strings, but your schema expects various types:

```python
from pydantic_jsonschema import to_lax_model, Schema
import csv
from io import StringIO

schema = Schema.model_validate({
    "type": "object",
    "properties": {
        "id": {"type": "integer"},
        "name": {"type": "string"},
        "price": {"type": "number"},
        "in_stock": {"type": "boolean"}
    }
})

Product = to_lax_model(schema, model_name="Product")

csv_data = """id,name,price,in_stock
1,Widget,19.99,true
2,Gadget,29.99,false"""

reader = csv.DictReader(StringIO(csv_data))
products = [Product.model_validate(row) for row in reader]

for p in products:
    print(f"{p.name}: ${p.price}")
    #> Widget: $19.99
    #> Gadget: $29.99
```

*This example is complete and can be run as-is.*

## Using LaxSchemaConverter

For more control, use the `LaxSchemaConverter` class directly:

```python
from pydantic_jsonschema import Schema, LaxSchemaConverter

converter = LaxSchemaConverter(
    default_model_name="Model",
    refs={},                  # Pre-built models
    format_validators={}      # Custom validators
)

schema = Schema.model_validate({
    "type": "object",
    "properties": {
        "count": {"type": "integer"}
    }
})

Model = converter.convert_schema(schema)

# Type coercion works
data = Model(count="42")  # ✓ Coerced to 42
```

!!! warning "Caching Behavior"
    Caching is used for all refs and models, so be careful when using `LaxSchemaConverter` directly. The converter maintains state for caching and reference resolution across multiple schema conversions.

## Combining with Format Validators

Lax validation works with format validators - coercion happens first, then format validation:

```python
from pydantic_jsonschema import to_lax_model, Schema

schema = Schema.model_validate({
    "type": "object",
    "properties": {
        "email": {"type": "string", "format": "email"}
    }
})

def email_validator(value: str) -> str:
    # Add actual email validation logic
    return value

User = to_lax_model(schema, format_validators={"email": email_validator})

# Value is coerced to string, then validated as email
user = User(email="alice@example.com")  # ✓
```

## Decision Guide

| Scenario                    | Use Lax? |
|-----------------------------|----------|
| API request validation      | No       |
| LLM outputs                 | **Yes**  |
| CSV/spreadsheet import      | **Yes**  |
| Configuration files (yours) | No       |
| External API responses      | **Yes**  |
| Database models             | No       |
| User form input             | **Yes**  |
| Type safety critical        | No       |

## Next Steps

- [Converters](converters.md) — Learn about creating models and strict validation
- [Format Validators](formats.md) — Add custom validation for special formats
- [Examples](examples.md) — See lax validation in real-world scenarios
- [API Reference](api/converters.md) — Full API documentation
