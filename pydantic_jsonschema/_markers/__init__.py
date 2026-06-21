"""Marker validators for JSON Schema applicator keywords.

Each marker holds one or more subschema annotations (possibly a `ForwardRef`), builds its
`TypeAdapter`(s) lazily, and binds a forward-ref namespace after the whole schema is converted.
The converter collects them and calls `bind_namespace` once conversion finishes.
"""

from ._contains import Contains
from ._dependent_schemas import DependentSchemas
from ._if_then_else import IfThenElse
from ._not import Not
from ._one_of import OneOf
from ._pattern_properties import PatternProperties
from ._prefix_items import PrefixItems
from ._property_names import PropertyNames

__all__ = [
    "Contains",
    "DependentSchemas",
    "IfThenElse",
    "Not",
    "OneOf",
    "PatternProperties",
    "PrefixItems",
    "PropertyNames",
]
