"""Convert a JSON Schema `Schema` into a Pydantic model (`to_model` / `SchemaConverter`)."""

from ._converter import SchemaConverter, to_model

__all__ = [
    "SchemaConverter",
    "to_model",
]
