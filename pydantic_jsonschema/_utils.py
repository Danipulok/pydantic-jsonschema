"""Internal utilities shared across the package."""

import re
from typing import Any, TypeAliasType

__all__ = [
    "sanitize_identifier",
    "unwrap_type_alias",
]

# Any annotation Pydantic supports (`type`, `Annotated`, `Union`, `Literal`, ...).
type AnnotationType = Any

_LEADING_NON_ALPHA: re.Pattern[str] = re.compile(r"^[^a-zA-Z_]+")
_INVALID_CHARS: re.Pattern[str] = re.compile(r"[^a-zA-Z0-9_]")


def sanitize_identifier(name: str) -> str:
    """Sanitize string to be a valid Python identifier.

    :param name: String to sanitize.
    :returns: Valid Python identifier.
    """
    name = _LEADING_NON_ALPHA.sub("", name)
    return _INVALID_CHARS.sub("", name)


def unwrap_type_alias(annotation: AnnotationType, /) -> AnnotationType:
    """Resolve a PEP 695 `type` alias down to the annotation it names.

    A `TypeAliasType` compares by identity, never by what it aliases, so it is unusable in any
    equality check against a real annotation:

        type DateTime = datetime.datetime
        DateTime == datetime.datetime
        #> False

    The loop covers an alias of an alias (`type Timestamp = DateTime`), which one unwrap step
    would leave as another `TypeAliasType`.

    :param annotation: Annotation that may be a PEP 695 alias.
    :returns: The aliased annotation, or `annotation` unchanged when it is not an alias.
    """
    while isinstance(annotation, TypeAliasType):
        annotation = annotation.__value__

    return annotation
