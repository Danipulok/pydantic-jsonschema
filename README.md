### What this library does

- Convertion of OpenAPI schema to Pydantic model (for validation).
- Lax convertion of pydantic models (be less restrictive for llms / accept more formats).
- Partial validation of pydantic models (all fields are optional with default null). (check how pydantic handles it)

- Custom schema formats
- Dump model json schema with knows models (ref URI) (convert_schema, model_dump_json_schema with refs (where is it needed?), not for converter)

## Converters
### 1. - Сейчас надо на каждую конвертацию создавать инстанс. Это ок.

### 2. - lax, опции:
1. дефолты для полей которые required но list with no minItems + dict with no minProperties
2. делать все | None + default None
3. валидаторы (coerce "123" -> 123)
Надо решить как это сохранять
"""