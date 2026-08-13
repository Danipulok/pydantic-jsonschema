"""Attach per-node loading and dumping behavior with `rules`."""

from pydantic_jsonschema import Schema, to_model
from pydantic_jsonschema.rules import After, Before, ByPath, ByType, Dump, Rule


def csv_to_list(value: str | list[str]) -> list[str]:
    """Accept a comma-separated string wherever a list of strings is expected."""
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]

    return value


def normalize_sku(value: str) -> str:
    """Normalize a product code to its canonical upper-case form."""
    return value.strip().upper()


# A feed exported from a spreadsheet: every column arrives as a string, and `tags`
# packs several values into one cell.
order_schema = Schema.model_validate(
    {
        "type": "object",
        "properties": {
            "sku": {"type": "string"},
            "tags": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["sku", "tags"],
    },
)

# A rule is a matcher plus one action. `ByType` covers every node of that Python type,
# `ByPath` targets a single node by its JSON Pointer, and a load-and-dump round-trip is
# two rules sharing a matcher.
Order = to_model(
    order_schema,
    rules=[
        Rule(ByType(list[str]), Before(csv_to_list)),
        Rule(ByPath("#/properties/sku"), After(normalize_sku)),
        Rule(ByType(list[str]), Dump(",".join)),
    ],
)

order = Order(
    sku="  wdg-1234-pro  ",  # Trimmed and upper-cased by the `ByPath` rule.
    tags="sale, clearance",  # Split into a list by the `ByType` rule.
)

# NOTE: `ruff format` rewrites `#>` to `# >`, breaking `pytest-examples` output markers.
# fmt: off
print(order.sku)  # type: ignore[attr-defined]
#> WDG-1234-PRO
print(order.tags)  # type: ignore[attr-defined]
#> ['sale', 'clearance']

# The `Dump` rule packs the list back into the shape the feed uses.
print(order.model_dump())
#> {'sku': 'WDG-1234-PRO', 'tags': 'sale,clearance'}
# fmt: on
