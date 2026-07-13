# Rules

Rules attach custom loading behavior to the model `to_model` generates, matched **by type or by
path** — without hand-writing the model. Each rule has three parts, one object each:

1. **when** — a matcher (`ByType`, `ByPath`, `ByFunc`);
2. **what** — a callable, held by the action;
3. **how** — the action kind (`Before`, `After`, `Override`, `Dump`).

One rule performs exactly one action. A load-and-dump round-trip is two rules sharing a matcher.

## Basic Usage

A field declared as array-of-string can accept a comma-separated string by coercing the raw input
with a `Before` action, matched on the field's Python type with `ByType`.

```python title="rules_basic.py"
from pydantic_jsonschema import Before, ByType, Rule, Schema, to_model


def csv_to_list(value: str | list[str]) -> list[str]:
    return value.split(",") if isinstance(value, str) else value


schema = Schema.model_validate(
    {
        "type": "object",
        "properties": {"tags": {"type": "array", "items": {"type": "string"}}},
        "required": ["tags"],
    }
)

User = to_model(schema, rules=[Rule(ByType(list[str]), Before(csv_to_list))])

print(User(tags="a,b,c").tags)
#> ['a', 'b', 'c']
print(User(tags=["x", "y"]).tags)
#> ['x', 'y']
```

## Actions

Each action maps to exactly one Pydantic wrapper, so a rule holding one action does exactly one
thing.

| Action           | Pydantic wrapper  | When it runs                          |
|------------------|-------------------|---------------------------------------|
| `Before(func)`   | `BeforeValidator` | before core parsing, on the raw input |
| `After(func)`    | `AfterValidator`  | after core parsing, on the value      |
| `Override(func)` | `PlainValidator`  | replaces core parsing entirely        |
| `Dump(func)`     | `PlainSerializer` | on serialization (model → output)     |

## Matchers

### `ByType`

Matches when the resolved annotation equals the given type. Parameterized generics match exactly
(`list[str]`, not `list[int]`).

### `ByPath`

Matches a single node by its JSON Pointer. Accepts `#/properties/code`, `/properties/code`, or
`properties/code` — all normalize identically.

```python title="rules_by_path.py"
from pydantic_jsonschema import After, ByPath, Rule, Schema, to_model


def strip_upper(value: str) -> str:
    return value.strip().upper()


schema = Schema.model_validate(
    {
        "type": "object",
        "properties": {"code": {"type": "string"}},
        "required": ["code"],
    }
)

Product = to_model(schema, rules=[Rule(ByPath("#/properties/code"), After(strip_upper))])

print(Product(code="  ab-1  ").code)
#> AB-1
```

### `ByFunc`

An escape hatch: match on any predicate over the node's `MatchContext` (its `schema`,
`annotation`, and `path`).

```python title="rules_by_func.py"
from pydantic_jsonschema import After, ByFunc, MatchContext, Rule, Schema, to_model


def is_string(context: MatchContext) -> bool:
    return context.annotation is str


def strip_upper(value: str) -> str:
    return value.strip().upper()


schema = Schema.model_validate(
    {
        "type": "object",
        "properties": {"code": {"type": "string"}},
        "required": ["code"],
    }
)

Product = to_model(schema, rules=[Rule(ByFunc(is_string), After(strip_upper))])

print(Product(code=" ab ").code)
#> AB
```

## Load and Dump Round-Trip

`Before` and `Dump` are separate actions, so a round-trip is two rules that share a matcher —
matcher duplication is intentional.

```python title="rules_round_trip.py"
from pydantic_jsonschema import Before, ByType, Dump, Rule, Schema, to_model


def csv_to_list(value: str | list[str]) -> list[str]:
    return value.split(",") if isinstance(value, str) else value


schema = Schema.model_validate(
    {
        "type": "object",
        "properties": {"tags": {"type": "array", "items": {"type": "string"}}},
        "required": ["tags"],
    }
)

User = to_model(
    schema,
    rules=[
        Rule(ByType(list[str]), Before(csv_to_list)),
        Rule(ByType(list[str]), Dump(",".join)),
    ],
)

user = User(tags="a,b,c")
print(user.tags)
#> ['a', 'b', 'c']
print(user.model_dump())
#> {'tags': 'a,b,c'}
```

## Rules Are Data

Matchers, actions, and `Rule` are frozen dataclasses, so they compare, hash, and `repr` as plain
data — convenient for building rule sets programmatically and asserting on them in tests. The only
non-data field is the held callable (and `ByFunc`'s predicate).

## Rules vs. Formats

Use [`formats`](formats.md) when a schema declares a `format` keyword and you want a type to
enforce it. Use `rules` when you want to match by Python type or path and control loading with a
chosen Pydantic slot. The two compose: format substitution runs first, then rules wrap the result.

## Next Steps

- [Formats](formats.md) - Enforce JSON Schema `format` keywords
- [Converters](converters.md) - Learn how schema conversion works
- [Examples](examples.md) - Run complete examples
