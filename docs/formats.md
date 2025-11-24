# Format Validators

Add validation for schema formats like email, UUID, dates, and custom domain-specific formats.

## What are Formats?

JSON Schema's `format` keyword lets you specify semantic validation beyond basic types:

```python
from uuid import UUID

from pydantic import EmailStr, ValidationError

from pydantic_jsonschema import Schema, to_model

schema = Schema.model_validate(
    {
        "type": "object",
        "properties": {
            "email": {"type": "string", "format": "email"},
            "id": {"type": "string", "format": "uuid"},
        },
    }
)

# Without format validators, these are just strings
User = to_model(schema)
user = User(email="not-an-email", id="not-a-uuid")  # ✓ No validation

User = to_model(
    schema,
    format_validators={
        "email": EmailStr,
        "uuid": UUID
    }
)

try:
    User(email="invalid")
except ValidationError as e:
    print(e)
    """
    1 validation error for Model
    email
      value is not a valid email address: An email address must have an @-sign. [type=value_error, input_value='invalid', input_type=str]
    """
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
from pydantic_jsonschema import Schema, to_model
from pydantic_jsonschema.formats import DateTime, Email, IPv4, Uri, UUID

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

User = to_model(
    schema,
    format_validators={
        "email": Email,
        "uri": Uri,
        "date-time": DateTime,
        "uuid": UUID,
        "ipv4": IPv4,
    },
)

user = User(
    email="alice@example.com",
    website="https://example.com/profile",
    created_at="2024-01-15T10:30:00Z",
    id="550e8400-e29b-41d4-a716-446655440000",
    ip="192.168.1.1",
)
```

### Extended Format Validators

Install domain-specific validators:

```bash
uv add pydantic-jsonschema[formats-extra]
```

This adds validators from [`pydantic-extra-types`](https://github.com/pydantic/pydantic-extra-types):

```python
from pydantic_extra_types.payment import PaymentCardNumber
from pydantic_extra_types.phone_numbers import PhoneNumber

from pydantic_jsonschema import Schema, to_model

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
from pydantic_jsonschema import Schema, to_model


def validate_sku(value: str) -> str:
    """Validate SKU format: ABC-1234-XYZ"""
    parts = value.split("-")

    if len(parts) != 3:
        msg = "SKU must have 3 parts"
        raise ValueError(msg)

    if not parts[0].isalpha() or len(parts[0]) != 3:
        msg = "First part must be 3 letters"
        raise ValueError(msg)

    if not parts[1].isdigit() or len(parts[1]) != 4:
        msg = "Second part must be 4 digits"
        raise ValueError(msg)

    if not parts[2].isalpha() or len(parts[2]) != 3:
        msg = "Third part must be 3 letters"
        raise ValueError(msg)

    return value.upper()  # Normalize to uppercase


schema = Schema.model_validate({
    "type": "object",
    "properties": {
        "sku": {"type": "string", "format": "sku"}
    }
})

Product = to_model(schema, format_validators={"sku": validate_sku})

product = Product(sku="abc-1234-xyz")
print(product.sku)
#> ABC-1234-XYZ
```

*This example is complete and can be run as-is.*

### Using Annotated Types

For more complex validation, use Pydantic's `Annotated` types:

```python
from typing import Annotated

from pydantic import AfterValidator, Field

from pydantic_jsonschema import Schema, to_model


def validate_positive(value: float) -> float:
    if value <= 0:
        msg = "Must be positive"
        raise ValueError(msg)
    return value


# Create a custom type
PositivePrice = Annotated[
    float,
    Field(gt=0, description="Product price"),
    AfterValidator(lambda v: round(v, 2)),  # Round to 2 decimals
]

schema = Schema.model_validate({
    "type": "object",
    "properties": {
        "price": {"type": "number", "format": "price"}
    }
})

Product = to_model(schema, format_validators={"price": PositivePrice})

product = Product(price=19.999)
print(product.price)
#> 20.0
```

*This example is complete and can be run as-is.*

## Real-World Example: Semantic Version

Validate semantic versioning format:

```python
import re

from pydantic import ValidationError

from pydantic_jsonschema import Schema, to_model


def validate_semver(value: str) -> str:
    """Validate semantic version (e.g., 1.2.3)"""
    pattern = r"^\d+\.\d+\.\d+(-[a-zA-Z0-9]+)?$"

    if not re.match(pattern, value):
        msg = "Must be semantic version format (e.g., 1.2.3 or 1.2.3-beta)"
        raise ValueError(msg)
    return value


schema = Schema.model_validate({
    "type": "object",
    "properties": {
        "version": {"type": "string", "format": "semver"}
    }
})

Package = to_model(schema, format_validators={"semver": validate_semver})

Package(version="1.2.3")  # ✓
Package(version="2.0.0-beta")  # ✓

try:
    Package(version="1.2")
except ValidationError as e:
    print(e)
    """
    1 validation error for Model
    version
      Value error, Must be semantic version format (e.g., 1.2.3 or 1.2.3-beta) [type=value_error, input_value='1.2', input_type=str]
        For further information visit https://errors.pydantic.dev/2.12/v/value_error
    """
```

*This example is complete and can be run as-is.*

## Real-World Example: Hex Color

Validate and normalize hex color codes:

```python
from pydantic_jsonschema import Schema, to_model


def validate_hex_color(value: str) -> str:
    """Validate and normalize hex color (#RRGGBB)"""
    value = value.strip()

    # Add # if missing
    if not value.startswith("#"):
        value = f"#{value}"

    # Check format
    if len(value) != 7:
        msg = "Must be 6 hex digits"
        raise ValueError(msg)

    # Validate hex digits
    try:
        int(value[1:], 16)
    except ValueError:
        msg = "Invalid hex digits"
        raise ValueError(msg) from None

    return value.upper()


schema = Schema.model_validate({
    "type": "object",
    "properties": {
        "color": {"type": "string", "format": "hex-color"}
    }
})


Theme = to_model(schema, format_validators={"hex-color": validate_hex_color})

theme = Theme(color="ff5733")
print(theme.color)
#> #FF5733

theme = Theme(color="#1a2b3c")
print(theme.color)
#> #1A2B3C
```

*This example is complete and can be run as-is.*

## Validator Types

Format validators can be:

### 1. Functions

Simple callables that validate and return the value:

```python
from pydantic_jsonschema import JsonType


def is_valid(_value: JsonType) -> bool:
    # Your validation logic here
    return True


def transform(value: JsonType) -> JsonType:
    # Your transformation logic here
    return value


def my_validator(value: JsonType) -> JsonType:
    if not is_valid(value):
        msg = "Invalid"
        raise ValueError(msg)
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

from pydantic import AfterValidator


def uppercase(v: str) -> str:
    return v.upper()


UpperStr = Annotated[str, AfterValidator(uppercase)]

format_validators = {"upper": UpperStr}
```

## Validator Execution Order

Validators run at different stages:

```python
from typing import Annotated

from pydantic import AfterValidator, BeforeValidator

from pydantic_jsonschema import JsonType


def before_validation(v: JsonType) -> str:
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
from pydantic import EmailStr

from pydantic_jsonschema import Schema, to_lax_model

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
        msg = "Port must be 1-65535"
        raise ValueError(msg)
    return value


Port = Annotated[int, Field(ge=1, le=65535)]

format_validators = {"port": Port}
```

### Multiple Constraints

```python
from typing import Annotated

from pydantic import AfterValidator, Field


def validate_username(value: str) -> str:
    if not value.isalnum():
        msg = "Must be alphanumeric"
        raise ValueError(msg)
    return value.lower()


Username = Annotated[
    str,
    Field(min_length=3, max_length=20),
    AfterValidator(validate_username)
]

format_validators = {"username": Username}
```

### Normalization

```python
def normalize_phone(value: str) -> str:
    """Remove all non-digits"""
    digits = "".join(c for c in value if c.isdigit())

    if len(digits) != 10:
        msg = "Must be 10 digits"
        raise ValueError(msg)

    # Format as (XXX) XXX-XXXX
    return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"


format_validators = {"phone": normalize_phone}
```

## Error Handling

Validators should raise `ValueError` with a clear message:

```python
def validate_age(value: int) -> int:
    if value < 0:
        msg = "Age cannot be negative"
        raise ValueError(msg)

    if value > 150:
        msg = "Age seems unrealistic"
        raise ValueError(msg)

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
