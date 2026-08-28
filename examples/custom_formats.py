"""Map a JSON Schema `format` to a custom Pydantic type."""

import re
from typing import Annotated

from pydantic import AfterValidator

from pydantic_jsonschema import Schema, to_model


def validate_sku(value: str) -> str:
    """Validate product SKU format: ABC-1234-XYZ."""
    value = value.upper()
    pattern = r"^[A-Z]{3}-\d{4}-[A-Z]{3}$"

    if not re.match(pattern, value):
        msg = "SKU must be in format ABC-1234-XYZ"
        raise ValueError(msg)

    return value


def validate_price(value: float) -> float:
    """Validate price is positive with max 2 decimals."""
    if value <= 0:
        msg = "Price must be positive"
        raise ValueError(msg)

    if round(value, 2) != value:
        msg = "Price can have at most 2 decimal places"
        raise ValueError(msg)

    return value


# A custom format is a Pydantic type, the same shape as the built-in formats
#  (e.g. `type Email = Annotated[str, AfterValidator(...)]`). The wrapper you pick
#  (`AfterValidator`, `BeforeValidator`, ...) controls when validation runs.
type Sku = Annotated[str, AfterValidator(validate_sku)]
type Price = Annotated[float, AfterValidator(validate_price)]


product_schema = Schema.model_validate(
    {
        "type": "object",
        "properties": {
            "sku": {"type": "string", "format": "sku"},
            "name": {"type": "string"},
            "price": {"type": "number", "format": "price"},
        },
        "required": ["sku", "name", "price"],
    },
)

Product = to_model(
    product_schema,
    formats={
        "sku": Sku,
        "price": Price,
    },
)

product = Product(
    sku="wdg-1234-pro",  # Normalized to uppercase
    name="Widget Pro",
    price=19.99,
)

# NOTE: `ruff format` rewrites `#>` to `# >`, breaking `pytest-examples` output markers.
# fmt: off
print(product.sku)  # type: ignore[attr-defined]
#> WDG-1234-PRO
print(product.price)  # type: ignore[attr-defined]
#> 19.99
# fmt: on
