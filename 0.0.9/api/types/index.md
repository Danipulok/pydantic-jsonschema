Public type exports.

Classes:

| Name        | Description                  |
| ----------- | ---------------------------- |
| `DataType`  | JSON Schema primitive types. |
| `Reference` | JSON Schema $ref reference.  |
| `Schema`    | JSON Schema object.          |

## DataType

Bases: `StrEnum`

JSON Schema primitive types.

See: https://json-schema.org/draft/2020-12/json-schema-core#section-4.2.1

## Reference

Bases: `BaseModel`

JSON Schema `$ref` reference.

See: https://json-schema.org/draft/2020-12/json-schema-core#section-8.2.3.1

## Schema

Bases: `BaseModel`

JSON Schema object.

Only fields consumed by the converter are declared explicitly. Unknown keywords are preserved via `extra="allow"` per spec §4.3.1 / §6.5.

See: https://json-schema.org/draft/2020-12/json-schema-core#section-4.3.1 See: https://json-schema.org/draft/2020-12/json-schema-core#section-6.5 See: https://json-schema.org/draft/2020-12/json-schema-validation
