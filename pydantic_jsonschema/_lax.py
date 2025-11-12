import json
from collections.abc import Callable
from typing import Any, cast

__all__ = [
    "COERCE_FUNCTIONS",
    "coerce_to_float",
    "coerce_to_int",
    "coerce_to_list",
    "coerce_to_str",
    "load_json_simple",
]


def load_json_simple(data: str, /) -> list[Any] | dict[str, Any] | None:
    """Load complex JSON (dict, list) from the given string.

    Return `None` if the string is not a valid complex JSON.
    Do not attempt to fix malformed JSON.
    """
    data = data.strip()

    try:
        return cast("list[Any] | dict[str, Any]", json.loads(data, strict=True))
    except (json.JSONDecodeError, TypeError):
        pass

    try:
        return cast("list[Any] | dict[str, Any]", json.loads(data, strict=False))
    except (json.JSONDecodeError, TypeError):
        pass

    return None


def coerce_to_str(value: Any) -> Any:  # noqa: ANN401
    # None -> str
    if value is None:
        return ""

    return str(value)


def coerce_to_int(value: Any) -> Any:  # noqa: ANN401
    # str -> int
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return value

    # float -> int
    if isinstance(value, float):
        return int(value)

    return value


def coerce_to_float(value: Any) -> Any:  # noqa: ANN401
    # str -> float
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return value

    # int -> float
    if isinstance(value, int):
        return float(value)

    return value


def coerce_to_list(value: Any) -> Any:  # noqa: ANN401
    # None -> list
    if value is None:
        return []

    # str -> list
    # "a, b, c" -> ["a", "b", "c"]
    if isinstance(value, str) and "," in value:
        return [item.strip() for item in value.split(",")]

    # JSON -> list
    # '["a", "b", "c"]' -> ["a", "b", "c"]
    if isinstance(value, str) and value.startswith("[") and value.endswith("]"):
        loaded_json = load_json_simple(value)
        return loaded_json if isinstance(loaded_json, list) else value

    return value


COERCE_FUNCTIONS: dict[type, Callable[[Any], Any]] = {
    str: coerce_to_str,
    int: coerce_to_int,
    float: coerce_to_float,
    list: coerce_to_list,
}
