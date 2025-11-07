from typing import Any

from pydantic import BaseModel

__all__ = [
    "JsonItem",
    "PythonItem",
]

type JsonItem = str | int | float | bool | None | list[Any] | dict[str, Any]
type PythonItem = str | int | float | bool | None | list[Any] | BaseModel
