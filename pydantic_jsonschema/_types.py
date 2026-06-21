"""Shared type aliases used across the converter and the marker validators."""

from typing import Any

__all__ = [
    "AnnotationType",
    "PythonType",
]

# Any annotation Pydantic supports (`type`, `Annotated`, `Union`, `Literal`, `ForwardRef`, ...).
type AnnotationType = Any
# Any value or type Pydantic can validate or produce.
type PythonType = Any
