# Formats

JSON Schema `format` values describe semantic constraints such as email addresses, UUIDs, URIs, or domain-specific identifiers. Pydantic JSON Schema only enforces those constraints when you pass a matching entry in `formats`.

Without a matching validator, `format` is treated as metadata and the normal JSON Schema type still applies.

## Third-Party Validator Libraries

All built-in formats work with zero extra dependencies. For domain-specific types, install [`pydantic-extra-types`](https://github.com/pydantic/pydantic-extra-types) or other packages directly.

See [Installation](https://danipulok.github.io/pydantic-jsonschema/0.0.13/install/#third-party-validator-libraries) for the install commands.

## Basic Usage

The key in `formats` must match the schema's `format` value.

formats.py

```python
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
    formats={
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

The `pydantic_jsonschema.formats` module exports aliases that can be passed to `formats`.

| JSON Schema `format`    | Alias                 | Validates                                                    |
| ----------------------- | --------------------- | ------------------------------------------------------------ |
| `email`                 | `Email`               | Email addresses                                              |
| `idn-email`             | `IdnEmail`            | Internationalized email addresses (RFC 6531)                 |
| `hostname`              | `Hostname`            | RFC 1123 hostnames, including single labels like `localhost` |
| `idn-hostname`          | `IdnHostname`         | Internationalized hostnames (RFC 5890)                       |
| `uri`                   | `Uri`                 | Absolute URIs with a scheme                                  |
| `uri-reference`         | `UriReference`        | Absolute or relative URI references                          |
| `iri`                   | `Iri`                 | Absolute internationalized URIs                              |
| `iri-reference`         | `IriReference`        | Absolute or relative internationalized URI references        |
| `uri-template`          | `UriTemplate`         | URI Templates (RFC 6570)                                     |
| `date`                  | `Date`                | Dates                                                        |
| `time`                  | `Time`                | Times                                                        |
| `date-time`             | `DateTime`            | Date-time values                                             |
| `duration`              | `Duration`            | Durations                                                    |
| `uuid`                  | `UUID`                | UUID values                                                  |
| `ipv4`                  | `IPv4`                | IPv4 addresses                                               |
| `ipv6`                  | `IPv6`                | IPv6 addresses                                               |
| `json-pointer`          | `JsonPointer`         | JSON Pointers (RFC 6901)                                     |
| `relative-json-pointer` | `RelativeJsonPointer` | Relative JSON Pointers                                       |
| `regex`                 | `Regex`               | Regular expressions                                          |

Differences from the specification

`idn-hostname` / `idn-email` convert domains via the stdlib IDNA 2003 codec, which is slightly more permissive than the IDNA 2008 tables referenced by the spec. `regex` compiles with Python `re`, a close superset of the ECMA-262 dialect the spec requires.

provided_formats.py

```python
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
    formats={
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

If you want to use third-party or custom format types, you can pass them via `formats`. Here's an example involving `pydantic-extra-types` package.

extra_types.py

```python
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
    formats={
        "payment-card": PaymentCardNumber,
        "color": Color,
    },
)

checkout = Checkout(card="4111111111111111", color="#ff5733")
print(type(checkout.color).__name__)
#> Color
```

Common `pydantic-extra-types` validators include payment cards, colors, countries, coordinates, MAC addresses, and phone numbers. See the [pydantic-extra-types documentation](https://github.com/pydantic/pydantic-extra-types) for the full list.

## Custom Formats

A custom format is a Pydantic type you map to a `format` value — exactly how the built-in aliases are defined (`Email = Annotated[str, AfterValidator(...)]`). Wrap your own validation or normalization in an `Annotated` type; the wrapper you choose (`AfterValidator`, `BeforeValidator`, `Field(...)`) controls how and when it runs, so you keep full control.

custom_sku_format.py

```python
from typing import Annotated

from pydantic import AfterValidator, ValidationError

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


Sku = Annotated[str, AfterValidator(validate_sku)]

schema = Schema.model_validate(
    {
        "type": "object",
        "properties": {
            "sku": {"type": "string", "format": "sku"},
        },
    }
)

Product = to_model(schema, formats={"sku": Sku})

product = Product(sku="abc-1234-xyz")
print(product.sku)
#> ABC-1234-XYZ

try:
    Product(sku="abc-12")
except ValidationError as er:
    print(type(er).__name__)
    #> ValidationError
```

## Accepted Forms

`formats` maps each format name to a Pydantic type. Two forms are accepted:

| Form             | Example                    | Behavior                                           |
| ---------------- | -------------------------- | -------------------------------------------------- |
| Type class       | `{"url": HttpUrl}`         | Replaces the generated annotation                  |
| `Annotated` type | `{"price": PositivePrice}` | Replaces the annotation, preserving its validators |

A bare callable is **not** accepted — wrap it in `Annotated[...]` so the timing is explicit (`Annotated[str, BeforeValidator(fn)]` for raw input, `Annotated[str, AfterValidator(fn)]` for the coerced value).

### Type classes

type_class_format.py

```python
from pydantic import HttpUrl
from pydantic_extra_types.color import Color

formats = {
    "color": Color,
    "url": HttpUrl,
}
```

### Annotated types

annotated_format.py

```python
from typing import Annotated

from pydantic import AfterValidator, BeforeValidator, Field


def round_price(value: float) -> float:
    return round(value, 2)


def normalize_phone(value: str) -> str:
    digits = "".join(character for character in value if character.isdigit())

    if len(digits) != 10:
        msg = "Phone number must contain 10 digits"
        raise ValueError(msg)

    return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"


# `AfterValidator` runs on the coerced value; `BeforeValidator` runs on the raw input.
PositivePrice = Annotated[float, Field(gt=0), AfterValidator(round_price)]
Phone = Annotated[str, BeforeValidator(normalize_phone)]

formats = {"price": PositivePrice, "phone": Phone}
```

## Execution Order

Each format type replaces the generated annotation and runs its own validation pipeline. With an `Annotated` type you set the order explicitly through the wrappers you include: `BeforeValidator` runs on the raw input, then Pydantic coerces to the base type, then `AfterValidator` and `Field(...)` constraints run on the coerced value.

## Error Handling

Raise `ValueError` with a clear message when a value is invalid:

error_handling.py

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

Pydantic converts the error into a `ValidationError` with field location information.

## Best Practices

- Keep validators focused on one format.
- Return the original or normalized value.
- Raise `ValueError` for invalid values.
- Include valid and invalid cases in tests.
- Document the expected input format in examples and error messages.

## Next Steps

- [Installation](https://danipulok.github.io/pydantic-jsonschema/0.0.13/install/index.md) - Install optional format validator dependencies
- [Converters](https://danipulok.github.io/pydantic-jsonschema/0.0.13/converters/index.md) - Learn how schema conversion works
- [Examples](https://danipulok.github.io/pydantic-jsonschema/0.0.13/examples/index.md) - Run complete examples
