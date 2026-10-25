"""Names whose import path differs across the supported `pydantic` releases."""

# `pydantic.MISSING` exists only from `2.14.0`, which deprecates the `2.13` path
#  `pydantic.experimental.missing_sentinel` (`PydanticDeprecatedSince214` on import).
#  Both return this same `pydantic_core` object, so importing it here works on either.
#  https://github.com/pydantic/pydantic/blob/fcdefa7198c4fc94a22eecf1a5b7926e20b9fc8a/pydantic/__init__.py#L406
#  https://github.com/pydantic/pydantic/blob/fcdefa7198c4fc94a22eecf1a5b7926e20b9fc8a/pydantic/experimental/missing_sentinel.py#L18-L25
from pydantic_core import MISSING

__all__ = [
    "MISSING",
]
