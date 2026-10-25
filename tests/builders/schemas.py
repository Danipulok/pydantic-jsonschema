"""Expected `model_json_schema()` fragments that depend on the installed `pydantic`."""

from typing import Final

from pydantic import VERSION

__all__ = [
    "NEXT_MODEL_REF",
]

# `pydantic 2.14.0` stopped emitting `title` beside the `$ref` of an `X | MISSING = MISSING`
#  field; `2.13` still emits `"title": "Next"`. Drop the branch once the floor passes `2.13`.
#  https://github.com/pydantic/pydantic/blob/fcdefa7198c4fc94a22eecf1a5b7926e20b9fc8a/pydantic/json_schema.py#L2396-L2397
NEXT_MODEL_REF: Final[dict[str, str]] = (
    {"$ref": "#/$defs/Model"}
    if tuple(map(int, VERSION.split(".")[:2])) >= (2, 14)
    else {"$ref": "#/$defs/Model", "title": "Next"}
)
