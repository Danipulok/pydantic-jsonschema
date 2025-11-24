"""Import CSV data with automatic type coercion."""

import csv
from io import StringIO
from typing import Any

from pydantic_jsonschema import Schema, to_lax_model


# Custom coerce function for CSV lists
def coerce_csv_to_list(value: Any) -> Any:  # noqa: ANN401
    """Convert comma-separated string to list."""
    if isinstance(value, str) and "," in value:
        return [item.strip() for item in value.split(",")]
    return value


# Define the schema for CSV rows
product_schema = Schema.model_validate(
    {
        "type": "object",
        "properties": {
            "id": {"type": "integer"},
            "name": {"type": "string"},
            "price": {"type": "number"},
            "quantity": {"type": "integer"},
            "in_stock": {"type": "boolean"},
            "tags": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["id", "name", "price"],
    },
)

# Use custom coerce function for list type to handle CSV format
Product = to_lax_model(
    product_schema,
    model_name="Product",
    coerce_functions={list: coerce_csv_to_list},
)

# Sample CSV data (everything is strings)
csv_data = """id,name,price,quantity,in_stock,tags
1,Widget,19.99,100,true,"electronics,gadgets"
2,Gadget,29.99,50,false,"electronics,tech"
3,Tool,9.99,200,true,"hardware,tools"
"""

# Parse and validate
reader = csv.DictReader(StringIO(csv_data))
products = []

for row in reader:
    product = Product.model_validate(row)
    products.append(product)

for p in products:
    print(f"{p.name}: ${p.price} (Stock: {p.quantity})")  # type: ignore[attr-defined]
    # > Widget: $19.99 (Stock: 100)
    # > Gadget: $29.99 (Stock: 50)
    # > Tool: $9.99 (Stock: 200)
    # > Widget: $19.99 (Stock: 100)
    # > Gadget: $29.99 (Stock: 50)
    # > Tool: $9.99 (Stock: 200)
