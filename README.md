### What this library does

- Convertion of OpenAPI schema to Pydantic model (for validation).
- Lax convertion of pydantic models (be less restrictive for llms / accept more formats).
- Partial validation of pydantic models (all fields are optional with default null). (check how pydantic handles it)

- Custom schema formats
- Dump model json schema with knows models (ref URI) (to_model, model_dump_json_schema with refs (where is it needed?), not for converter)
