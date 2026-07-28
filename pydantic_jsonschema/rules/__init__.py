"""Loading rules: per-node input coercion and output serialization, matched by type or path.

A `Rule` attaches custom loading behavior to the model `to_model` generates, without hand-writing
the model. Each rule has three parts, one object each:

1. **when** — a matcher (`ByType`, `ByPath`, `ByFunc`);
2. **what** — a callable, held by the action;
3. **how** — the action kind.

Actions come in two families. *Annotation actions* (`Before`, `After`, `Override`, `Dump`) wrap
the matched field's annotation. *Model actions* (`ModelBefore`, `ModelAfter`, `ModelWrap`) attach a
whole-object `model_validator` to the matched object model — the only way to reach the root model.

One rule performs exactly one action. A load-and-dump round-trip is two rules sharing a matcher.

```python
to_model(schema, rules=[Rule(ByType(list[str]), Before(csv_to_list))])
```

See `.ai/configurable-loading.md` for the design and the action -> Pydantic slot mapping.
"""

from pydantic_jsonschema.rules._actions import (
    Action,
    After,
    AnnotationAction,
    Before,
    Dump,
    Loader,
    ModelAction,
    ModelAfter,
    ModelBefore,
    ModelWrap,
    ModelWrapper,
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
    "AnnotationAction",
    "Before",
    "ByFunc",
    "ByPath",
    "ByType",
    "Dump",
    "Loader",
    "MatchContext",
    "Matcher",
    "ModelAction",
    "ModelAfter",
    "ModelBefore",
    "ModelWrap",
    "ModelWrapper",
    "Override",
    "Rule",
    "SchemaPredicate",
    "Serializer",
]
