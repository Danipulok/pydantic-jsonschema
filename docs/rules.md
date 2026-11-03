# Rules

Rules attach custom loading and dumping behavior to the model `to_model` generates — matched **by
type, by path, or by an arbitrary predicate** — without hand-writing the model. Each rule has three
parts, one object each:

1. **when**: a matcher (`ByType`, `ByPath`, `ByFunc`);
2. **what**: a callable, held by the action;
3. **how**: the action kind.

Actions come in two families. *Annotation actions* (`Before`, `After`, `Override`, `Dump`) wrap the
matched field's annotation. *Model actions* (`ModelBefore`, `ModelAfter`, `ModelWrap`) attach a
whole-object `model_validator` to the model built for the matched object node, the root included.

One rule performs exactly one action. A load-and-dump round-trip is two rules sharing a matcher.

Pass rules to `to_model(schema, rules=[...])`, or to `SchemaConverter(rules=[...])` when you drive
conversion yourself — the two take the same list.

## Basic Usage

A field declared as array-of-string can accept a comma-separated string by coercing the raw input
with a `Before` action, matched on the field's Python type with `ByType`.

```python title="rules_basic.py"
from pydantic_jsonschema import Schema, to_model
from pydantic_jsonschema.rules import Before, ByType, Rule


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
    ],
)

print(User(tags="a,b,c").tags)
#> ['a', 'b', 'c']
print(User(tags=["x", "y"]).tags)
#> ['x', 'y']
```

## Actions

Each action maps to exactly one Pydantic wrapper, so a rule holding one action does exactly one
thing.

### Annotation Actions

Annotation actions wrap the matched field's annotation.

| Action           | Pydantic wrapper  | When it runs                          |
|------------------|-------------------|---------------------------------------|
| `Before(func)`   | `BeforeValidator` | before core parsing, on the raw input |
| `After(func)`    | `AfterValidator`  | after core parsing, on the value      |
| `Override(func)` | `PlainValidator`  | replaces core parsing entirely        |
| `Dump(func)`     | `PlainSerializer` | on serialization (model → output)     |

### Model Actions

Model actions attach a whole-object `model_validator` to the model built for the matched object
node, the root one or a nested one, whichever model it becomes (a model class, a map `RootModel`,
an `allOf` combination). This is how an **object root** with properties is reached: it becomes
the model class itself, and a class carries no annotation for an annotation action to wrap.

Model actions pair with `ByPath` / `ByFunc`. `ByType` never matches a model node: the model class
does not exist yet when the matcher runs, so the node has no resolved annotation, and
`MatchContext.is_model` is `True` there. A `$ref`'d definition is matched where it is declared
(`/$defs/User`), never at a property that refers to it. A nested object with no `properties` (a
bare `{"type": "object"}` or a map of `additionalProperties`) becomes a `dict` field, not a
model, so it takes annotation actions and no model action.

| Action              | Pydantic wrapper                 | What `func` receives                    |
|---------------------|----------------------------------|-----------------------------------------|
| `ModelBefore(func)` | `model_validator(mode="before")` | the raw input, before field parsing     |
| `ModelAfter(func)`  | `model_validator(mode="after")`  | the built model (cross-field slot)      |
| `ModelWrap(func)`   | `model_validator(mode="wrap")`   | the raw input and a `handler` to build  |

```python title="rules_model_after.py"
from pydantic import BaseModel

from pydantic_jsonschema import Schema, to_model
from pydantic_jsonschema.rules import ByPath, ModelAfter, Rule


def require_end_after_start(model: BaseModel) -> BaseModel:
    values = model.model_dump()
    if values["end"] < values["start"]:
        msg = "end must not precede start"
        raise ValueError(msg)
    return model


schema = Schema.model_validate(
    {
        "type": "object",
        "properties": {"start": {"type": "integer"}, "end": {"type": "integer"}},
        "required": ["start", "end"],
    }
)

Span = to_model(schema, rules=[Rule(ByPath("/"), ModelAfter(require_end_after_start))])

print(Span(start=1, end=5).model_dump())
#> {'start': 1, 'end': 5}

# `pydantic.ValidationError` subclasses `ValueError`, so it is caught here.
try:
    Span(start=5, end=1)
except ValueError as er:
    print(type(er).__name__)
    #> ValidationError
```

## Matchers

### `ByType`

Matches on the resolved annotation. A parameterized generic matches exactly — `list[str]` does not
match `list[int]`.

An **unparameterized** generic matches every parameterization of itself, because the converter never
produces a bare one: an array becomes `list[str]` (or `list[Any]` without `items`), a typed map
becomes `dict[str, T]`. Comparing a bare `list` by equality would therefore match nothing at all.

| Target      | Matches                                  |
|-------------|------------------------------------------|
| `list`      | `list[str]`, `list[int]`, `list[Any]`, … |
| `list[str]` | `list[str]`                              |
| `list[Any]` | `list[Any]` — an array without `items`   |
| `dict`      | `dict[str, str]`, `dict[str, Any]`, …    |

A PEP 695 alias resolves to whatever it names, so `type Tags = list[str]` and `ByType(Tags)` are
interchangeable with `ByType(list[str])`.

A node whose annotation a [`formats`](formats.md) entry replaced carries the format type, so target
it with that same type. `ByType(Email)` reaches the email fields; a bare `ByType(str)` reaches only
the strings no format touched, because `Annotated[str, ...]` is neither equal to `str` nor a
parameterization of it.

The format's own validation runs first, so the rule sees a value the format already accepted.

```python title="rules_by_type_format.py"
from pydantic_jsonschema import Schema, to_model
from pydantic_jsonschema.formats import Email
from pydantic_jsonschema.rules import After, ByType, Rule


def to_lower(value: str) -> str:
    return value.lower()


schema = Schema.model_validate(
    {
        "type": "object",
        "properties": {
            "contact": {"type": "string", "format": "email"},
            "note": {"type": "string"},
        },
        "required": ["contact", "note"],
    }
)

User = to_model(
    schema,
    formats={"email": Email},
    rules=[
        Rule(ByType(Email), After(to_lower)),
    ],
)

user = User(contact="User@Example.COM", note="Kept")
print(user.contact)
#> user@example.com
print(user.note)
#> Kept
```

### `ByPath`

Matches a single node by its [JSON Pointer](https://www.rfc-editor.org/rfc/rfc6901). The pointer
starts with `/` and carries no `#` prefix, which is exactly how `MatchContext.path` reports it — so
a `ByPath` rule and a `ByFunc` predicate comparing `context.path` always agree on the same string.

There is only this one accepted spelling. A `$ref` in the schema looks like `#/$defs/User`, and
pasting that fragment form into `ByPath` raises `ValueError` naming the pointer to use instead,
rather than silently producing a rule that matches nothing.

Every node the converter walks has a pointer, not just top-level properties:

| Node                            | Pointer                                 |
|---------------------------------|-----------------------------------------|
| root                            | `/`                                     |
| property `code`                 | `/properties/code`                      |
| element of an array property    | `/properties/tags/items`                |
| value of a typed map            | `/properties/meta/additionalProperties` |
| second `anyOf` branch           | `/properties/value/anyOf/1`             |
| property inside a `$defs` entry | `/$defs/User/properties/name`           |

`/` addresses the root whatever the root is; which action family fits depends on what it becomes.
A non-object root, and an object root with only a schema-valued `additionalProperties`, become a
`RootModel` whose value has an annotation, so annotation actions apply. Any other object root
becomes the model class itself, which carries no annotation: an annotation action has nothing to
wrap there and never fires, so reach it with a model action instead. A model action reaches
every object root, whichever model it becomes.

```python title="rules_root_pointer.py"
from pydantic_jsonschema import Schema, to_model
from pydantic_jsonschema.rules import After, ByPath, Rule


def strip_upper(value: str) -> str:
    return value.strip().upper()


root_rule = Rule(ByPath("/"), After(strip_upper))

Code = to_model(
    Schema.model_validate({"type": "string"}),
    rules=[root_rule],
)

print(Code("  ab-1  ").root)
#> AB-1

Product = to_model(
    Schema.model_validate(
        {
            "type": "object",
            "properties": {"code": {"type": "string"}},
            "required": ["code"],
        }
    ),
    rules=[root_rule],
)

# An annotation action has nothing to wrap on an object root, so it never fires: a model
# action such as `ModelAfter` is what reaches this root.
print(repr(Product(code="  ab-1  ").code))
#> '  ab-1  '
```

A definition is addressed where it is *declared* (`/$defs/User/...`), not through the `$ref`s that
point at it, so one rule covers every use of that definition. Property names keep their literal
characters and are escaped per RFC 6901 — `~` becomes `~0` and `/` becomes `~1`, so a property
named `a/b` is `/properties/a~1b`.

```python title="rules_by_path.py"
from pydantic_jsonschema import Schema, to_model
from pydantic_jsonschema.rules import After, ByPath, Rule


def strip_upper(value: str) -> str:
    return value.strip().upper()


schema = Schema.model_validate(
    {
        "type": "object",
        "properties": {"code": {"type": "string"}},
        "required": ["code"],
    }
)

Product = to_model(
    schema,
    rules=[
        Rule(ByPath("/properties/code"), After(strip_upper)),
    ],
)

print(Product(code="  ab-1  ").code)
#> AB-1
```

### `ByFunc`

An escape hatch: match on any predicate over the node's `MatchContext` (its `schema`,
`annotation`, `path`, and `is_model`, which is `True` on an object model node whose `annotation`
is a `None` placeholder).

```python title="rules_by_func.py"
from pydantic_jsonschema import Schema, to_model
from pydantic_jsonschema.rules import After, ByFunc, MatchContext, Rule


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

Product = to_model(
    schema,
    rules=[
        Rule(ByFunc(is_string), After(strip_upper)),
    ],
)

print(Product(code=" ab ").code)
#> AB
```

## Load and Dump Round-Trip

`Before` and `Dump` are separate actions, so a round-trip is two rules that share a matcher —
matcher duplication is intentional.

```python title="rules_round_trip.py"
from pydantic_jsonschema import Schema, to_model
from pydantic_jsonschema.rules import Before, ByType, Dump, Rule


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
