"""Expected values that depend on the installed `pydantic`."""

import re
from typing import Final

from pydantic import VERSION

__all__ = [
    "NEXT_MODEL_REF",
    "TOO_LONG_DICT_MESSAGE",
]

_PYDANTIC_VERSION: Final[tuple[int, ...]] = tuple(map(int, re.findall(r"\d+", VERSION)[:3]))

# `pydantic 2.14.0` stopped emitting `title` beside the `$ref` of an `X | MISSING = MISSING`
#  field; `2.13` still emits `"title": "Next"`. Drop the branch once the floor passes `2.13`.
#  https://github.com/pydantic/pydantic/blob/fcdefa7198c4fc94a22eecf1a5b7926e20b9fc8a/pydantic/json_schema.py#L2396-L2397
NEXT_MODEL_REF: Final[dict[str, str]] = (
    {"$ref": "#/$defs/Model"}
    if _PYDANTIC_VERSION >= (2, 14)
    else {"$ref": "#/$defs/Model", "title": "Next"}
)

# `pydantic 2.14.2` checks `max_length` while building the dict and no longer reports the
#  length: `not more` instead of `not 3`. Drop the branch once the floor reaches `2.14.2`.
#  https://github.com/pydantic/pydantic/blob/aa540acc29960fb394312cf97d888c99f9686814/pydantic-core/src/validators/list.rs#L96-L109
TOO_LONG_DICT_MESSAGE: Final[str] = (
    "Dictionary should have at most 2 items after validation, not more"
    if _PYDANTIC_VERSION >= (2, 14, 2)
    else "Dictionary should have at most 2 items after validation, not 3"
)
