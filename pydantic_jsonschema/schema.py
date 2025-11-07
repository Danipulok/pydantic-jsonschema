"""
JSON Schema generation from Pydantic models with reference support.

Allows dumping Pydantic models back to JSON Schema format with:
- $refs for known models
- $defs for nested models
- Proper JSON Schema 2020-12 format
"""

from typing import Any, Literal

from pydantic import BaseModel

__all__ = [
    "model_dump_json_schema",
]


def model_dump_json_schema(
    model: type[BaseModel],
    /,
    *,
    refs: dict[str, type[BaseModel]] | None = None,
    mode: Literal["validation", "serialization"] = "validation",
    by_alias: bool = True,
) -> dict[str, Any]:
    """
    Dump Pydantic model to JSON Schema with reference support.

    :param model: Pydantic model to dump.
    :param refs: Optional mapping of reference URIs to models.
    :param mode: Schema generation mode ("validation" or "serialization").
    :param by_alias: Use field aliases in schema.
    :returns: JSON Schema dict.
    """
    # Use Pydantic's built-in JSON schema generation
    schema = model.model_json_schema(
        mode=mode,
        by_alias=by_alias,
        ref_template="#/$defs/{model}",
    )

    # If refs provided, replace model refs with custom URIs
    if refs:
        schema = _replace_refs(schema, refs)

    return schema


def _replace_refs(
    schema: dict[str, Any],
    refs: dict[str, type[BaseModel]],
    /,
) -> dict[str, Any]:
    """
    Replace model references with custom URIs.

    :param schema: JSON Schema dict.
    :param refs: Mapping of reference URIs to models.
    :returns: Updated schema with custom refs.
    """
    # Build reverse mapping: model name -> ref URI
    model_to_ref: dict[str, str] = {}
    for ref_uri, model in refs.items():
        model_to_ref[model.__name__] = ref_uri

    # Recursively replace refs
    def replace_in_dict(obj: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in obj.items():
            if key == "$ref" and isinstance(value, str):
                # Extract model name from ref
                # Format: #/$defs/ModelName
                if value.startswith("#/$defs/"):
                    model_name = value.split("/")[-1]
                    result[key] = model_to_ref.get(model_name, value)
                else:
                    result[key] = value
            elif isinstance(value, dict):
                result[key] = replace_in_dict(value)
            elif isinstance(value, list):
                result[key] = [
                    replace_in_dict(item) if isinstance(item, dict) else item for item in value
                ]
            else:
                result[key] = value
        return result

    return replace_in_dict(schema)
