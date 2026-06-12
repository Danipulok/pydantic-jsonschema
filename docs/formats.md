# Format Validators

JSON Schema `format` values describe semantic constraints such as email addresses, UUIDs, URIs, or
domain-specific identifiers. Pydantic JSON Schema only enforces those constraints when you pass a
matching entry in `format_validators`.

Without a matching validator, `format` is treated as metadata and the normal JSON Schema type still
applies.

## Third-Party Validator Libraries

All built-in format validators work with zero extra dependencies.
For domain-specific types, install [`pydantic-extra-types`](https://github.com/pydantic/pydantic-extra-types) or other packages directly.

See [Installation](install.md#third-party-validator-libraries) for the install commands.

## Basic Usage

The key in `format_validators` must match the schema's `format` value.

```python title="format_validators.py"
from pydantic import ValidationError

from pydantic_jsonschema import Schema, to_model
from pydantic_jsonschema.formats import UUID, Email

schema = Schema.model_validate(
    {
        "type": "object",
        "properties": {
            "email": {"type": "string", "format": "email"},
            "id": {"type": "string", "format": "uuid"},
        },
    }
)

LooseUser = to_model(schema)
loose_user = LooseUser(email="not-an-email", id="not-a-uuid")
print(loose_user.email)
#> not-an-email

StrictUser = to_model(
    schema,
    format_validators={
        "email": Email,
        "uuid": UUID,
    },
)

strict_user = StrictUser(
    email="alice@example.com",
    id="550e8400-e29b-41d4-a716-446655440000",
)
print(type(strict_user.id).__name__)
#> UUID

try:
    StrictUser(email="invalid", id="550e8400-e29b-41d4-a716-446655440000")
except ValidationError as er:
    print(type(er).__name__)
    #> ValidationError
```

## Provided Format Aliases

The `pydantic_jsonschema.formats` module exports aliases that can be passed to
`format_validators`.

| JSON Schema `format` | Alias          | Validates                                                    |
|----------------------|----------------|--------------------------------------------------------------|
| `email`              | `Email`        | Email addresses                                              |
| `hostname`           | `Hostname`     | RFC 1123 hostnames, including single labels like `localhost` |
| `uri`                | `Uri`          | Absolute URIs with a scheme                                  |
| `uri-reference`      | `UriReference` | Absolute or relative URI references                          |
| `iri`                | `Iri`          | Absolute internationalized URIs                              |
| `iri-reference`      | `IriReference` | Absolute or relative internationalized URI references        |
| `date`               | `Date`         | Dates                                                        |
| `time`               | `Time`         | Times                                                        |
| `date-time`          | `DateTime`     | Date-time values                                             |
| `duration`           | `Duration`     | Durations                                                    |
| `uuid`               | `UUID`         | UUID values                                                  |
| `ipv4`               | `IPv4`         | IPv4 addresses                                               |
| `ipv6`               | `IPv6`         | IPv6 addresses                                               |

```python title="provided_formats.py"
from pydantic_jsonschema import Schema, to_model
from pydantic_jsonschema.formats import DateTime, Email, IPv4, Uri

schema = Schema.model_validate(
    {
        "type": "object",
        "properties": {
            "email": {"type": "string", "format": "email"},
            "website": {"type": "string", "format": "uri"},
            "created_at": {"type": "string", "format": "date-time"},
            "ip": {"type": "string", "format": "ipv4"},
        },
    }
)

User = to_model(
    schema,
    format_validators={
        "email": Email,
        "uri": Uri,
        "date-time": DateTime,
        "ipv4": IPv4,
    },
)

user = User(
    email="alice@example.com",
    website="https://example.com/profile",
    created_at="2024-01-15T10:30:00Z",
    ip="192.168.1.1",
)

print(type(user.created_at).__name__)
#> datetime
```

## Third-Party Pydantic Types

If you want to use third-party or custom format validators, you can pass them via `format_validators`.
Here's an example involving `pydantic-extra-types` package.

```python title="extra_types.py"
from pydantic_extra_types.color import Color
from pydantic_extra_types.payment import PaymentCardNumber

from pydantic_jsonschema import Schema, to_model

schema = Schema.model_validate(
    {
        "type": "object",
        "properties": {
            "card": {"type": "string", "format": "payment-card"},
            "color": {"type": "string", "format": "color"},
        },
    }
)

Checkout = to_model(
    schema,
    format_validators={
        "payment-card": PaymentCardNumber,
        "color": Color,
    },
)

checkout = Checkout(card="4111111111111111", color="#ff5733")
print(type(checkout.color).__name__)
#> Color
```

Common `pydantic-extra-types` validators include payment cards, colors, countries, coordinates,
MAC addresses, and phone numbers. See the
[pydantic-extra-types documentation](https://github.com/pydantic/pydantic-extra-types) for the full
list.

## Custom Validators

Use a callable when you want to validate or normalize a project-specific format.

Callable validators receive the raw input before Pydantic type coercion. They should return the
validated value and raise `ValueError` when validation fails.

```python title="custom_sku_validator.py"
from pydantic import ValidationError

from pydantic_jsonschema import Schema, to_model


def validate_sku(value: str) -> str:
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

    return value.upper()


schema = Schema.model_validate(
    {
        "type": "object",
        "properties": {
            "sku": {"type": "string", "format": "sku"},
        },
    }
)

Product = to_model(schema, format_validators={"sku": validate_sku})

product = Product(sku="abc-1234-xyz")
print(product.sku)
#> ABC-1234-XYZ

try:
    Product(sku="abc-12")
except ValidationError as er:
    print(type(er).__name__)
    #> ValidationError
```

## Validator Types

`format_validators` accepts these validator forms:

| Validator form   | Example                    | Behavior                                                       |
|------------------|----------------------------|----------------------------------------------------------------|
| Callable         | `{"sku": validate_sku}`    | Called before Pydantic type validation                         |
| Pydantic type    | `{"url": HttpUrl}`         | Replaces the generated annotation                              |
| `Annotated` type | `{"price": PositivePrice}` | Replaces the generated annotation and preserves its validators |

### Callable Validators

```python title="callable_validator.py"
from pydantic_jsonschema import JsonType


def normalize_phone(value: JsonType) -> str:
    digits = "".join(character for character in str(value) if character.isdigit())

    if len(digits) != 10:
        msg = "Phone number must contain 10 digits"
        raise ValueError(msg)

    return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"


format_validators = {"phone": normalize_phone}
```

### Pydantic Types

```python title="pydantic_type_validator.py"
from pydantic import HttpUrl
from pydantic_extra_types.color import Color

format_validators = {
    "color": Color,
    "url": HttpUrl,
}
```

### Annotated Types

```python title="annotated_validator.py"
from typing import Annotated

from pydantic import AfterValidator, Field


def round_price(value: float) -> float:
    return round(value, 2)


PositivePrice = Annotated[
    float,
    Field(gt=0),
    AfterValidator(round_price),
]

format_validators = {"price": PositivePrice}
```

## Execution Order

Execution order depends on the validator form:

| Validator form   | Order                                           |
|------------------|-------------------------------------------------|
| Callable         | format callable, then generated type validation |
| Pydantic type    | Pydantic type validation                        |
| `Annotated` type | validators defined inside the `Annotated` type  |

For callable validators, the value passed to the function is the raw input value. For Pydantic
types and `Annotated` types, the validator replaces the generated annotation, so Pydantic runs that
type's own validation pipeline.

## Error Handling

Raise `ValueError` with a clear message when a value is invalid:

```python title="error_handling.py"
def validate_age(value: int) -> int:
    if value < 0:
        msg = "Age cannot be negative"
        raise ValueError(msg)

    if value > 150:
        msg = "Age seems unrealistic"
        raise ValueError(msg)

    return value
```

Pydantic converts the error into a `ValidationError` with field location information.

## Best Practices

- Keep validators focused on one format.
- Return the original or normalized value.
- Raise `ValueError` for invalid values.
- Include valid and invalid cases in tests.
- Document the expected input format in examples and error messages.

## Next Steps

- [Installation](install.md) - Install optional format validator dependencies
- [Converters](converters.md) - Learn how schema conversion works
- [Examples](examples.md) - Run complete examples
