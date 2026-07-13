"""`Rule`: one matcher paired with one action.

A rule is the whole unit the converter consumes: *when* (a `Matcher`) and *what/how* (an
`Action`). The one-action-per-rule constraint is enforced structurally — a `Rule` holds a single
`action`, and there is no multi-action form. A load-and-dump round-trip is expressed as two rules
sharing a matcher.
"""

from dataclasses import dataclass

from pydantic_jsonschema.rules._actions import Action
from pydantic_jsonschema.rules._matchers import Matcher

__all__ = [
    "Rule",
]


# NOTE: `Rule(matcher, action)` intentionally takes two positional arguments, against the
# project's "keyword-only after the first parameter" convention. `(matcher, action)` reads as one
# natural pair, exactly like `Annotated[T, meta]`; every other public rule type takes a single
# argument. Kept positional by design — see `.ai/configurable-loading.md`.
@dataclass(frozen=True, slots=True)
class Rule:
    """A single loading rule: apply `action` wherever `matcher` matches."""

    matcher: Matcher
    action: Action
