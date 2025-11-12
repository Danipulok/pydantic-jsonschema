# Format Validators

Add validation for schema formats like email, UUID, dates, and custom domain-specific formats.

## What are Formats?

JSON Schema's `format` keyword lets you specify semantic validation beyond basic types:

```python
from pydantic_jsonschema import to_model, Schema

schema = Schema.model_validate({
    "type": "object",
    "properties": {
        "email": {"type": "string", "format": "email"},
        "id": {"type": "string", "format": "uuid"}
    }
})

# Without format validators, these are just strings
User = to_model(schema)
user = User(email="not-an-email", id="not-a-uuid")  # ✓ No validation

# With format validators, they're validated
from pydantic import EmailStr
from uuid import UUID

User = to_model(
    schema,
    format_validators={
        "email": EmailStr,
        "uuid": UUID
    }
)
# User(email="invalid")  # ✗ ValidationError
```

## Built-in Format Validators

Pydantic JSON Schema provides two levels of format validators:

### Base Format Validators

Install standard JSON Schema format validators:

```bash
uv add pydantic-jsonschema[formats-base]
```

This provides validators for formats defined in the JSON Schema specification:

| Format          | Validator     | RFC Standard | Description                                                   |
|-----------------|---------------|--------------|---------------------------------------------------------------|
| `email`         | `EmailStr`    | RFC 5322     | Email addresses                                               |
| `hostname`      | Custom        | RFC 1123     | Internet hostnames (including single labels like `localhost`) |
| `uri`           | Custom        | RFC 3986     | Absolute URIs with required scheme                            |
| `uri-reference` | Custom        | RFC 3986     | URI references (absolute or relative)                         |
| `iri`           | Custom        | RFC 3987     | Internationalized URIs                                        |
| `iri-reference` | Custom        | RFC 3987     | Internationalized URI references                              |
| `date`          | `date`        | RFC 3339     | Date (via Pydantic)                                           |
| `time`          | `time`        | RFC 3339     | Time (via Pydantic)                                           |
| `date-time`     | `datetime`    | RFC 3339     | Date and time (via Pydantic)                                  |
| `duration`      | `timedelta`   | ISO 8601     | Duration (via Pydantic)                                       |
| `uuid`          | `UUID`        | RFC 4122     | UUID (via Pydantic)                                           |
| `ipv4`          | `IPv4Address` | RFC 2673     | IPv4 address (via Pydantic)                                   |
| `ipv6`          | `IPv6Address` | RFC 4291     | IPv6 address (via Pydantic)                                   |

**Example using base formats:**

```python
from datetime import datetime
from ipaddress import IPv4Address

from pydantic import EmailStr
from pydantic_jsonschema import Schema, to_model
from pydantic_jsonschema.formats import EMAIL, URI, DATE_TIME, UUID, IPV4

schema = Schema.model_validate({
    "type": "object",
    "properties": {
        "email": {"type": "string", "format": "email"},
        "website": {"type": "string", "format": "uri"},
        "created_at": {"type": "string", "format": "date-time"},
        "id": {"type": "string", "format": "uuid"},
        "ip": {"type": "string", "format": "ipv4"},
    }
})

User = to_model(schema, format_validators={
    "email": EMAIL,
    "uri": URI,
    "date-time": DATE_TIME,
    "uuid": UUID,
    "ipv4": IPV4
})

user = User(
    email="alice@example.com",
    website="https://example.com/profile",
    created_at="2024-01-15T10:30:00Z",
    id="550e8400-e29b-41d4-a716-446655440000",
    ip="192.168.1.1"
)
```

### Extended Format Validators

Install domain-specific validators:

```bash
uv add pydantic-jsonschema[formats-extra]
```

This adds validators from [`pydantic-extra-types`](https://github.com/pydantic/pydantic-extra-types):

```python
from pydantic_jsonschema import to_model, Schema
from pydantic_extra_types.phone_numbers import PhoneNumber
from pydantic_extra_types.payment import PaymentCardNumber

schema = Schema.model_validate({
    "type": "object",
    "properties": {
        "card": {"type": "string", "format": "payment-card"},
        "phone": {"type": "string", "format": "phone"}
    }
})

User = to_model(
    schema,
    format_validators={
        "payment-card": PaymentCardNumber,
        "phone": PhoneNumber
    }
)

user = User(
    card="4111111111111111",
    phone="+1-202-555-0173"
)
```

**Available validators in `pydantic-extra-types`:**

- **Payment**: `PaymentCardNumber`
- **Phone**: `PhoneNumber`
- **Colors**: `Color` (hex, RGB, HSL, etc.)
- **Countries**: `CountryAlpha2`, `CountryAlpha3`
- **Coordinates**: `Latitude`, `Longitude`
- **MAC Address**: `MacAddress`
- **And many more**: See [pydantic-extra-types docs](https://github.com/pydantic/pydantic-extra-types)

## Custom Format Validators

Create your own validators for domain-specific formats.

### Simple Function Validator

```python
from pydantic_jsonschema import to_model, Schema

def validate_sku(value: str) -> str:
    """Validate SKU format: ABC-1234-XYZ"""
    parts = value.split("-")

    if len(parts) != 3:
        raise ValueError("SKU must have 3 parts")

    if not parts[0].isalpha() or len(parts[0]) != 3:
        raise ValueError("First part must be 3 letters")

    if not parts[1].isdigit() or len(parts[1]) != 4:
        raise ValueError("Second part must be 4 digits")

    if not parts[2].isalpha() or len(parts[2]) != 3:
        raise ValueError("Third part must be 3 letters")

    return value.upper()  # Normalize to uppercase

schema = Schema.model_validate({
    "type": "object",
    "properties": {
        "sku": {"type": "string", "format": "sku"}
    }
})

Product = to_model(schema, format_validators={"sku": validate_sku})

product = Product(sku="abc-1234-xyz")
print(product.sku)  #> ABC-1234-XYZ
```

*This example is complete and can be run as-is.*

### Using Annotated Types

For more complex validation, use Pydantic's `Annotated` types:

```python
from typing import Annotated
from pydantic import Field, AfterValidator
from pydantic_jsonschema import Schema, to_model

def validate_positive(value: float) -> float:
    if value <= 0:
        raise ValueError("Must be positive")
    return value

# Create a custom type
PositivePrice = Annotated[
    float,
    Field(gt=0, description="Product price"),
    AfterValidator(lambda v: round(v, 2))  # Round to 2 decimals
]

schema = Schema.model_validate({
    "type": "object",
    "properties": {
        "price": {"type": "number", "format": "price"}
    }
})

Product = to_model(schema, format_validators={"price": PositivePrice})

product = Product(price=19.999)
print(product.price)  #> 19.99
```

*This example is complete and can be run as-is.*

## Real-World Example: Semantic Version

Validate semantic versioning format:

```python
from pydantic_jsonschema import to_model, Schema
import re

def validate_semver(value: str) -> str:
    """Validate semantic version (e.g., 1.2.3)"""
    pattern = r'^\d+\.\d+\.\d+(-[a-zA-Z0-9]+)?$'

    if not re.match(pattern, value):
        raise ValueError(
            "Must be semantic version format (e.g., 1.2.3 or 1.2.3-beta)"
        )

    return value

schema = Schema.model_validate({
    "type": "object",
    "properties": {
        "version": {"type": "string", "format": "semver"}
    }
})

Package = to_model(schema, format_validators={"semver": validate_semver})

Package(version="1.2.3")       # ✓
Package(version="2.0.0-beta")  # ✓
# Package(version="1.2")  # ✗ ValidationError
```

*This example is complete and can be run as-is.*

## Real-World Example: Hex Color

Validate and normalize hex color codes:

```python
from pydantic_jsonschema import to_model, Schema

def validate_hex_color(value: str) -> str:
    """Validate and normalize hex color (#RRGGBB)"""
    value = value.strip()

    # Add # if missing
    if not value.startswith("#"):
        value = f"#{value}"

    # Check format
    if len(value) != 7:
        raise ValueError("Must be 6 hex digits")

    # Validate hex digits
    try:
        int(value[1:], 16)
    except ValueError:
        raise ValueError("Invalid hex digits") from None

    return value.upper()

schema = Schema.model_validate({
    "type": "object",
    "properties": {
        "color": {"type": "string", "format": "hex-color"}
    }
})

Theme = to_model(schema, format_validators={"hex-color": validate_hex_color})

theme = Theme(color="ff5733")
print(theme.color)  #> #FF5733

theme = Theme(color="#1a2b3c")
print(theme.color)  #> #1A2B3C
```

*This example is complete and can be run as-is.*

## Validator Types

Format validators can be:

### 1. Functions

Simple callables that validate and return the value:

```python
from typing import Any

def is_valid(value: Any) -> bool:
    # Your validation logic here
    return True

def transform(value: Any) -> Any:
    # Your transformation logic here
    return value

def my_validator(value: Any) -> Any:
    if not is_valid(value):
        raise ValueError("Invalid")
    return transform(value)
```

### 2. Pydantic Types

Use Pydantic's built-in or extra types:

```python
from pydantic import EmailStr, HttpUrl
from pydantic_extra_types.color import Color

format_validators={
    "email": EmailStr,
    "url": HttpUrl,
    "color": Color
}
```

### 3. Annotated Types

Types with validators attached:

```python
from typing import Annotated
from pydantic import Field, AfterValidator

def uppercase(v: str) -> str:
    return v.upper()

UpperStr = Annotated[str, AfterValidator(uppercase)]

format_validators={"upper": UpperStr}
```

## Validator Execution Order

Validators run at different stages:

```python
from typing import Annotated, Any
from pydantic import BeforeValidator, AfterValidator

def before_validation(v: Any) -> str:
    """Runs before type validation - for coercion"""
    return str(v)

def after_validation(v: str) -> str:
    """Runs after type validation - for additional checks"""
    return v.strip().upper()

CustomStr = Annotated[
    str,
    BeforeValidator(before_validation),
    AfterValidator(after_validation)
]
```

**Order:**

1. BeforeValidator (coercion)
2. Type validation (Pydantic)
3. AfterValidator (additional checks)
4. Format validator (if specified)

## Working with Lax Validation

Format validators work with both strict and lax converters:

```python
from pydantic_jsonschema import to_lax_model, Schema
from pydantic import EmailStr

schema = Schema.model_validate({
    "type": "object",
    "properties": {
        "email": {"type": "string", "format": "email"}
    }
})

User = to_lax_model(schema, format_validators={"email": EmailStr})

# Value is coerced to string first, then validated as email
user = User(email="alice@example.com")  # ✓
```

*This example is complete and can be run as-is.*

## Common Patterns

### Range Validation

```python
from typing import Annotated
from pydantic import Field

def validate_port(value: int) -> int:
    if not 1 <= value <= 65535:
        raise ValueError("Port must be 1-65535")
    return value

Port = Annotated[int, Field(ge=1, le=65535)]

format_validators={"port": Port}
```

### Multiple Constraints

```python
from typing import Annotated
from pydantic import Field, AfterValidator

def validate_username(value: str) -> str:
    if not value.isalnum():
        raise ValueError("Must be alphanumeric")
    return value.lower()

Username = Annotated[
    str,
    Field(min_length=3, max_length=20),
    AfterValidator(validate_username)
]

format_validators={"username": Username}
```

### Normalization

```python
def normalize_phone(value: str) -> str:
    """Remove all non-digits"""
    digits = ''.join(c for c in value if c.isdigit())

    if len(digits) != 10:
        raise ValueError("Must be 10 digits")

    # Format as (XXX) XXX-XXXX
    return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"

format_validators={"phone": normalize_phone}
```

## Error Handling

Validators should raise `ValueError` with a clear message:

```python
def validate_age(value: int) -> int:
    if value < 0:
        raise ValueError("Age cannot be negative")

    if value > 150:
        raise ValueError("Age seems unrealistic")

    return value
```

Pydantic will convert this to a `ValidationError` with location information.

## Best Practices

1. **Keep validators focused** — Each validator should check one thing
2. **Return the value** — Always return (possibly transformed) value
3. **Clear error messages** — Help users understand what's wrong
4. **Handle edge cases** — Test with None, empty strings, etc.
5. **Document format** — Include examples in error messages

## Next Steps

- [Examples](examples.md) — See format validators in real applications
- [Converters](converters.md) — Learn about model creation and validation modes
