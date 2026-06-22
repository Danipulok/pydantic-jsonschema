"""Applicators: JSON Schema keywords that apply subschemas to an instance.

JSON Schema calls a keyword whose value is itself a schema (or schemas) an *applicator*: it
applies those subschemas to the instance, or to its array items / object property values, and
the instance is valid only if the subschemas are satisfied. The term and the grouping come
straight from the spec — [core §10, "A Vocabulary for Applying Subschemas"][spec].

The classes here cover the applicators that have no native Pydantic equivalent and must be
validated by hand, each against a `TypeAdapter`-wrapped subschema:

- in-place applicators (apply to the whole instance): `Not` (`not`), `OneOf` (`oneOf`),
  `IfThenElse` (`if`/`then`/`else`), `DependentSchemas` (`dependentSchemas`);
- child applicators (apply to items / property values / names): `Contains` (`contains`),
  `PrefixItems` (`prefixItems`), `PatternProperties` (`patternProperties`),
  `PropertyNames` (`propertyNames`).

The remaining applicators — `allOf` / `anyOf` / `properties` / `items` / `additionalProperties` —
are *not* here: the converter expresses them natively as Pydantic unions, inheritance, and fields.

Why not "validators" or "markers": "validator" is too broad (it collides with the package's
format validators and field constraints) and says nothing about *applying a subschema*;
"marker" only described the implementation (an `Annotated` metadata object), and several of these
run as `before` model validators rather than `Annotated` markers. "Applicator" is the spec's own
word for exactly this category.

Each applicator holds one or more subschema annotations (possibly a `ForwardRef`), builds its
`TypeAdapter`(s) lazily, and binds a forward-ref namespace after the whole schema is converted.
The converter collects them and calls `bind_namespace` once conversion finishes.

[spec]: https://json-schema.org/draft/2020-12/json-schema-core#section-10
"""

from ._base import Applicator
from ._contains import Contains
from ._dependent_schemas import DependentSchemas
from ._if_then_else import IfThenElse
from ._not import Not
from ._one_of import OneOf
from ._pattern_properties import PatternProperties
from ._prefix_items import PrefixItems
from ._property_names import PropertyNames

__all__ = [
    "Applicator",
    "Contains",
    "DependentSchemas",
    "IfThenElse",
    "Not",
    "OneOf",
    "PatternProperties",
    "PrefixItems",
    "PropertyNames",
]
