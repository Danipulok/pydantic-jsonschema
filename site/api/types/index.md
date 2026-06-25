# Schema model

The JSON Schema document model — what you build, or validate raw input into, before conversion.

Public JSON Schema models: `Schema`, `Reference`, and the `DataType` enum.

## DataType

Bases: `StrEnum`

JSON Schema primitive types.

See [core §4.2.1](https://json-schema.org/draft/2020-12/json-schema-core#section-4.2.1).

### NULL

```python
NULL
```

The `null` type.

### STRING

```python
STRING
```

The `string` type.

### NUMBER

```python
NUMBER
```

The `number` type (any numeric value).

### INTEGER

```python
INTEGER
```

The `integer` type.

### BOOLEAN

```python
BOOLEAN
```

The `boolean` type.

### ARRAY

```python
ARRAY
```

The `array` type.

### OBJECT

```python
OBJECT
```

The `object` type.

## Reference

Bases: `BaseModel`

JSON Schema `$ref` reference.

See [core §8.2.3.1](https://json-schema.org/draft/2020-12/json-schema-core#section-8.2.3.1).

### ref

```python
ref: str
```

The `$ref` keyword: a URI reference to another schema.

## Schema

Bases: `BaseModel`

JSON Schema object.

Declares the JSON Schema 2020-12 validation and applicator keywords; any other or custom keyword is still preserved via `extra="allow"` per spec §4.3.1 / §6.5.

Not every declared keyword is consumed by the converter yet: unsupported ones round-trip through parsing and serialization but do not affect the generated model.

See:

- [core §4.3.1](https://json-schema.org/draft/2020-12/json-schema-core#section-4.3.1)
- [core §6.5](https://json-schema.org/draft/2020-12/json-schema-core#section-6.5)
- [validation](https://json-schema.org/draft/2020-12/json-schema-validation)

### type

```python
type: DataType | list[DataType] | MISSING
```

The `type` keyword: allowed JSON type(s). [Validation §6.1.1](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.1.1).

### enum

```python
enum: list[Any] | MISSING
```

The `enum` keyword: the set of allowed values. [Validation §6.1.2](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.1.2).

### const

```python
const: Any | MISSING
```

The `const` keyword: the single allowed value. [Validation §6.1.3](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.1.3).

### properties

```python
properties: dict[str, SchemaOrRefType] | MISSING
```

The `properties` keyword: schemas for object properties. [Core §10.3.2.1](https://json-schema.org/draft/2020-12/json-schema-core#section-10.3.2.1).

### items

```python
items: SchemaOrRefType | MISSING
```

The `items` keyword: the schema for array elements. [Core §10.3.1.2](https://json-schema.org/draft/2020-12/json-schema-core#section-10.3.1.2).

### prefix_items

```python
prefix_items: list[SchemaOrRefType] | MISSING
```

The `prefixItems` keyword: schemas for the leading array elements (tuple). [Core §10.3.1.1](https://json-schema.org/draft/2020-12/json-schema-core#section-10.3.1.1).

### contains

```python
contains: SchemaOrRefType | MISSING
```

The `contains` keyword: at least one array element must match this schema. [Core §10.3.1.3](https://json-schema.org/draft/2020-12/json-schema-core#section-10.3.1.3).

### additional_properties

```python
additional_properties: SchemaOrRefType | bool | MISSING
```

The `additionalProperties` keyword: schema/toggle for extra properties. [Core §10.3.2.3](https://json-schema.org/draft/2020-12/json-schema-core#section-10.3.2.3).

### pattern_properties

```python
pattern_properties: dict[str, SchemaOrRefType] | MISSING
```

The `patternProperties` keyword: schemas for properties matching a regex. [Core §10.3.2.2](https://json-schema.org/draft/2020-12/json-schema-core#section-10.3.2.2).

### property_names

```python
property_names: SchemaOrRefType | MISSING
```

The `propertyNames` keyword: schema every property name must match. [Core §10.3.2.4](https://json-schema.org/draft/2020-12/json-schema-core#section-10.3.2.4).

### required

```python
required: list[str] | MISSING
```

The `required` keyword: names of required properties. [Validation §6.5.3](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.5.3).

### min_properties

```python
min_properties: int | MISSING
```

The `minProperties` keyword: minimum number of properties. [Validation §6.5.2](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.5.2).

### max_properties

```python
max_properties: int | MISSING
```

The `maxProperties` keyword: maximum number of properties. [Validation §6.5.1](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.5.1).

### dependent_required

```python
dependent_required: dict[str, list[str]] | MISSING
```

The `dependentRequired` keyword: properties required when another is present. [Validation §6.5.4](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.5.4).

### dependent_schemas

```python
dependent_schemas: dict[str, SchemaOrRefType] | MISSING
```

The `dependentSchemas` keyword: subschemas applied when a property is present. [Core §10.2.2.4](https://json-schema.org/draft/2020-12/json-schema-core#section-10.2.2.4).

### all_of

```python
all_of: list[SchemaOrRefType] | MISSING
```

The `allOf` keyword: must match every subschema. [Core §10.2.1.1](https://json-schema.org/draft/2020-12/json-schema-core#section-10.2.1.1).

### any_of

```python
any_of: list[SchemaOrRefType] | MISSING
```

The `anyOf` keyword: must match at least one subschema. [Core §10.2.1.2](https://json-schema.org/draft/2020-12/json-schema-core#section-10.2.1.2).

### one_of

```python
one_of: list[SchemaOrRefType] | MISSING
```

The `oneOf` keyword: must match exactly one subschema. [Core §10.2.1.3](https://json-schema.org/draft/2020-12/json-schema-core#section-10.2.1.3).

### not\_

```python
not_: SchemaOrRefType | MISSING
```

The `not` keyword: must NOT match this subschema. [Core §10.2.1.4](https://json-schema.org/draft/2020-12/json-schema-core#section-10.2.1.4).

### if\_

```python
if_: SchemaOrRefType | MISSING
```

The `if` keyword: condition subschema gating `then` / `else`. [Core §10.2.2.1](https://json-schema.org/draft/2020-12/json-schema-core#section-10.2.2.1).

### then

```python
then: SchemaOrRefType | MISSING
```

The `then` keyword: applied when `if` validates. [Core §10.2.2.2](https://json-schema.org/draft/2020-12/json-schema-core#section-10.2.2.2).

### else\_

```python
else_: SchemaOrRefType | MISSING
```

The `else` keyword: applied when `if` fails. [Core §10.2.2.3](https://json-schema.org/draft/2020-12/json-schema-core#section-10.2.2.3).

### multiple_of

```python
multiple_of: float | MISSING
```

The `multipleOf` keyword: value must be a multiple of this. [Validation §6.2.1](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.2.1).

### maximum

```python
maximum: float | MISSING
```

The `maximum` keyword: inclusive upper bound. [Validation §6.2.2](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.2.2).

### exclusive_maximum

```python
exclusive_maximum: float | MISSING
```

The `exclusiveMaximum` keyword: exclusive upper bound. [Validation §6.2.3](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.2.3).

### minimum

```python
minimum: float | MISSING
```

The `minimum` keyword: inclusive lower bound. [Validation §6.2.4](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.2.4).

### exclusive_minimum

```python
exclusive_minimum: float | MISSING
```

The `exclusiveMinimum` keyword: exclusive lower bound. [Validation §6.2.5](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.2.5).

### min_length

```python
min_length: int | MISSING
```

The `minLength` keyword: minimum string length. [Validation §6.3.2](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.3.2).

### max_length

```python
max_length: int | MISSING
```

The `maxLength` keyword: maximum string length. [Validation §6.3.1](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.3.1).

### pattern

```python
pattern: str | MISSING
```

The `pattern` keyword: regex the string must match. [Validation §6.3.3](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.3.3).

### min_items

```python
min_items: int | MISSING
```

The `minItems` keyword: minimum array length. [Validation §6.4.2](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.4.2).

### max_items

```python
max_items: int | MISSING
```

The `maxItems` keyword: maximum array length. [Validation §6.4.1](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.4.1).

### unique_items

```python
unique_items: bool | MISSING
```

The `uniqueItems` keyword: array elements must be unique. [Validation §6.4.3](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.4.3).

### max_contains

```python
max_contains: int | MISSING
```

The `maxContains` keyword: max elements matching `contains`. [Validation §6.4.4](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.4.4).

### min_contains

```python
min_contains: int | MISSING
```

The `minContains` keyword: min elements matching `contains`. [Validation §6.4.5](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.4.5).

### format

```python
format: str | MISSING
```

The `format` keyword: a semantic format (e.g. `date-time`). [Validation §7](https://json-schema.org/draft/2020-12/json-schema-validation#section-7).

### title

```python
title: str | MISSING
```

The `title` keyword: a human-readable name. [Validation §9.1](https://json-schema.org/draft/2020-12/json-schema-validation#section-9.1).

### description

```python
description: str | MISSING
```

The `description` keyword: a human-readable explanation. [Validation §9.1](https://json-schema.org/draft/2020-12/json-schema-validation#section-9.1).

### default

```python
default: Any | MISSING
```

The `default` keyword: a default value for the instance. [Validation §9.2](https://json-schema.org/draft/2020-12/json-schema-validation#section-9.2).

### examples

```python
examples: list[Any] | MISSING
```

The `examples` keyword: example values. [Validation §9.5](https://json-schema.org/draft/2020-12/json-schema-validation#section-9.5).

### defs

```python
defs: dict[str, SchemaOrRefType] | MISSING
```

The `$defs` keyword: reusable subschema definitions. [Core §8.2.4](https://json-schema.org/draft/2020-12/json-schema-core#section-8.2.4).
