"""Re-exports of core openapi_pydantic types and project-level JSON type alias."""

import types
import typing
from typing import Any, get_type_hints

from openapi_pydantic import DataType
from openapi_pydantic import Reference as _OpenAPIReference
from openapi_pydantic import Schema as _OpenAPISchema
from pydantic import ConfigDict, SerializerFunctionWrapHandler, model_serializer

__all__ = [
    "DataType",
    "JsonType",
    "Reference",
    "Schema",
]


type JsonType = str | int | float | bool | None | list["JsonType"] | dict[str, "JsonType"]


class Schema(_OpenAPISchema):
    """`openapi_pydantic.Schema` with `None` fields dropped on serialization.

    `openapi_pydantic.Schema` has 50+ optional fields all defaulting to `None`.
    Serializing it naively bloats API responses and JSONB storage with `null`
    leaves. The wrap serializer below strips them recursively at dump time.

    `openapi_pydantic.Schema`'s recursive fields (`properties`, `items`, `allOf`,
    ...) are declared against itself and `openapi_pydantic.Reference`.
    `_rebind_nested_schema` below rewrites those annotations to point at our
    subclasses, so nested values deserialize as `Schema` / `Reference` (not
    parents) and `None`-strip / equality behavior works everywhere.
    """

    model_config = _OpenAPISchema.model_config | ConfigDict(
        serialize_by_alias=True,
    )

    @model_serializer(mode="wrap")
    def __model_serializer_wrap(
        self,
        handler: SerializerFunctionWrapHandler,
    ) -> dict[str, Any]:
        """Drop `None` leaves (recursively) inherited from parent fields."""
        return _strip_none(handler(self))


class Reference(_OpenAPIReference):
    """`openapi_pydantic.Reference` with `None` fields dropped on serialization."""

    model_config = _OpenAPIReference.model_config | ConfigDict(
        serialize_by_alias=True,
    )

    @model_serializer(mode="wrap")
    def __model_serializer_wrap(
        self,
        handler: SerializerFunctionWrapHandler,
    ) -> dict[str, Any]:
        """Drop `None` leaves (recursively) inherited from parent fields."""
        return _strip_none(handler(self))


def _strip_none(value: Any) -> Any:  # noqa: ANN401
    if isinstance(value, dict):
        return {k: _strip_none(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [_strip_none(v) for v in value]
    return value


def _swap_type(annotation: Any, from_type: type, to_type: type) -> Any:  # noqa: ANN401
    if annotation is from_type:
        return to_type

    args = typing.get_args(annotation)
    if not args:
        return annotation

    new_args = tuple(_swap_type(arg, from_type, to_type) for arg in args)
    if new_args == args:
        return annotation

    origin = typing.get_origin(annotation)
    if origin is typing.Union or origin is types.UnionType:
        result = new_args[0]
        for arg in new_args[1:]:
            result = result | arg
        return result

    return origin[new_args]


def _rebind_nested_schema() -> None:
    """Rebind `Schema`'s recursive annotations from parent classes to subclasses."""
    swaps = (
        (_OpenAPISchema, Schema),
        (_OpenAPIReference, Reference),
    )

    for name, annotation in get_type_hints(Schema).items():
        new_annotation = annotation
        for from_type, to_type in swaps:
            new_annotation = _swap_type(new_annotation, from_type, to_type)

        Schema.__annotations__[name] = new_annotation
        if name in Schema.model_fields:
            Schema.model_fields[name].annotation = new_annotation

    Schema.model_rebuild(force=True)


_rebind_nested_schema()
