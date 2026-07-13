"""Loading rules: per-node input coercion and output serialization, matched by type or path.

A `Rule` attaches custom loading behavior to the model `to_model` generates, without hand-writing
the model. Each rule has three parts, one object each:

1. **when** — a matcher (`ByType`, `ByPath`, `ByFunc`);
2. **what** — a callable, held by the action;
3. **how** — the action kind (`Before`, `After`, `Override`, `Dump`).

One rule performs exactly one action. A load-and-dump round-trip is two rules sharing a matcher.

```python
to_model(schema, rules=[Rule(ByType(list[str]), Before(csv_to_list))])
```

See `.ai/configurable-loading.md` for the design and the action -> Pydantic slot mapping.
"""

from pydantic_jsonschema.rules._actions import (
    Action,
    After,
    Before,
    Dump,
    Loader,
    Override,
    Serializer,
)
from pydantic_jsonschema.rules._matchers import (
    ByFunc,
    ByPath,
    ByType,
    MatchContext,
    Matcher,
    SchemaPredicate,
)
from pydantic_jsonschema.rules._rule import Rule

__all__ = [
    "Action",
    "After",
    "Before",
    "ByFunc",
    "ByPath",
    "ByType",
    "Dump",
    "Loader",
    "MatchContext",
    "Matcher",
    "Override",
    "Rule",
    "SchemaPredicate",
    "Serializer",
]
