from typing import Any

from pydantic import BaseModel

type JsonItem = str | int | float | bool | None | list[Any] | dict[str, Any]
type PythonItem = str | int | float | bool | None | list[Any] | BaseModel
