# Applicators

In JSON Schema, a keyword whose value is *itself a schema* (or schemas) is called an
**applicator**: it applies those subschemas to the instance — or to its array items, object
property values, or property names — and the instance is valid only if those subschemas are
satisfied. The term and the grouping are the spec's own, from
[core §10, "A Vocabulary for Applying Subschemas"][applicator-vocab].

`pydantic-jsonschema` represents the applicators that have **no native Pydantic equivalent** as a
small set of validator classes in `pydantic_jsonschema.applicators`. The
[converter](converters.md) builds them while turning a `Schema` into a model, and you can also use
them directly on your own Pydantic models.

## Why "applicators", not "validators" or "markers"

- **`validators`** is too broad. The package already has *format validators* and *field
  constraints*; "validator" says nothing about the trait that sets these apart — *applying a
  subschema*.
- **`markers`** described only the implementation: an `Annotated[T, ...]` metadata object. But
  several of these run as `before` model validators rather than `Annotated` markers — so the name
  was both narrower and less accurate than the behaviour.
- **`applicators`** is the exact word the JSON Schema spec uses for this category. The library
  speaks JSON Schema everywhere else, so it speaks it here too.

## Supported applicators

| Keyword | Class | Applies a subschema to… |
| --- | --- | --- |
| `not` | `Not` | the whole instance (it must *not* match) |
| `oneOf` | `OneOf` | the whole instance (exactly one branch matches) |
| `if` / `then` / `else` | `IfThenElse` | the whole instance, conditionally |
| `dependentSchemas` | `DependentSchemas` | the whole instance, when a property is present |
| `contains` | `Contains` | array items (at least / at most N match) |
| `prefixItems` | `PrefixItems` | array items by position |
| `patternProperties` | `PatternProperties` | property values whose name matches a regex |
| `propertyNames` | `PropertyNames` | every property name |

The first four are *in-place* applicators (they apply to the whole instance); the last four are
*child* applicators (they apply to items, property values, or names).

## What is not here

`allOf`, `anyOf`, `properties`, `items`, and `additionalProperties` are applicators too, but each
has a native Pydantic equivalent — inheritance, `Union`, and model fields — so the converter
expresses them directly instead of through a class here. See the
[conversion map](converters.md#conversion-map).

## How they work

Each applicator holds one or more subschema annotations and validates a value against them with a
Pydantic `TypeAdapter`. A subschema may be a `ForwardRef` pointing at a `$ref` that only becomes
resolvable once the whole schema — including `$defs` — is converted, so applicators build their
adapters lazily and receive a forward-reference namespace via `bind_namespace` after conversion
finishes.

Depending on the keyword, the converter attaches an applicator either as `Annotated` metadata on
the field type or as a `before` model validator on the model.

## Using an applicator directly

The applicator classes are not converter-internal — you can build a validated annotation from one
directly. `OneOf`, for example, enforces JSON Schema `oneOf` semantics (*exactly one* branch must
match), unlike a plain `Union`:

```python title="applicator_one_of.py"
from pydantic import TypeAdapter, ValidationError

from pydantic_jsonschema.applicators import OneOf

one_of = OneOf(branches=[int, float])
adapter = TypeAdapter(one_of.as_annotation())

print(adapter.validate_python(1.5))
#> 1.5

try:
    # `1` validates as both `int` and `float` -> two branches, not exactly one
    adapter.validate_python(1)
except ValidationError as er:
    print(er.errors()[0]["msg"])
    #> Value error, Input matches 2 `oneOf` branches, expected exactly 1
```

## Reference

See the [Applicators API](api/applicators.md) for every class, and
[core §10, "A Vocabulary for Applying Subschemas"][applicator-vocab] for the spec.

[applicator-vocab]: https://json-schema.org/draft/2020-12/json-schema-core#section-10
