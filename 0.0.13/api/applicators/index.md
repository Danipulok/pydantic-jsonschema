# Applicators

For the concepts behind these classes — what an applicator is and why it is named that — see the [Applicators guide](https://danipulok.github.io/pydantic-jsonschema/0.0.13/applicators/index.md).

Applicators: JSON Schema keywords that apply subschemas to an instance.

JSON Schema calls a keyword whose value is itself a schema (or schemas) an *applicator*: it applies those subschemas to the instance, or to its array items / object property values, and the instance is valid only if the subschemas are satisfied. The term and the grouping come straight from the spec — [core §10, "A Vocabulary for Applying Subschemas"](https://json-schema.org/draft/2020-12/json-schema-core#section-10).

The classes here cover the applicators that have no native Pydantic equivalent and must be validated by hand, each against a `TypeAdapter`-wrapped subschema:

- in-place applicators (apply to the whole instance): `Not` (`not`), `OneOf` (`oneOf`), `IfThenElse` (`if`/`then`/`else`), `DependentSchemas` (`dependentSchemas`);
- child applicators (apply to items / property values / names): `Contains` (`contains`), `PrefixItems` (`prefixItems`), `PatternProperties` (`patternProperties`), `PropertyNames` (`propertyNames`).

The remaining applicators — `allOf` / `anyOf` / `properties` / `items` / `additionalProperties` — are *not* here: the converter expresses them natively as Pydantic unions, inheritance, and fields.

Why not "validators" or "markers": "validator" is too broad (it collides with the package's format validators and field constraints) and says nothing about *applying a subschema*; "marker" only described the implementation (an `Annotated` metadata object), and several of these run as `before` model validators rather than `Annotated` markers. "Applicator" is the spec's own word for exactly this category.

Each applicator holds one or more subschema annotations (possibly a `ForwardRef`), builds its `TypeAdapter`(s) lazily, and binds a forward-ref namespace after the whole schema is converted. The converter collects them and calls `bind_namespace` once conversion finishes.

## AnnotationApplicator

```python
AnnotationApplicator()
```

Bases: `Applicator`, `ABC`

An applicator applied as `Annotated[type, self]` metadata on a value annotation.

It overrides Pydantic's schema hooks: `__get_pydantic_core_schema__` enforces the keyword during validation, and `__get_pydantic_json_schema__` re-emits it on `model_json_schema()`.

## Applicator

```python
Applicator()
```

Plumbing base for validators that check values against `TypeAdapter`-wrapped subschemas.

Holds the forward-ref namespace and provides the shared plumbing: resolving a `ForwardRef` subschema and building its adapter, and testing whether a value validates against an adapter. Subclasses own their adapter caching (single / list / mapping), since the shape differs per keyword. Concrete applicators extend the abstract roles `AnnotationApplicator` and/or `ObjectApplicator` (which carry the required hooks), never this class directly.

Initialize with an empty forward-ref namespace (bound later via `bind_namespace`).

### bind_namespace

```python
bind_namespace(namespace: dict[str, type[BaseModel]]) -> None
```

Provide the namespace used to resolve `ForwardRef` subschemas.

Parameters:

| Name        | Type                         | Description                                     | Default    |
| ----------- | ---------------------------- | ----------------------------------------------- | ---------- |
| `namespace` | `dict[str, type[BaseModel]]` | Mapping of sanitized reference names to models. | *required* |

## ObjectApplicator

```python
ObjectApplicator()
```

Bases: `Applicator`, `ABC`

An applicator applied to an object model via the converter's model-wrapper.

The wrapper delegates `validate` (raw-mapping check, run as a `before` validator) and `json_schema_keyword` (keyword fragment) from the model subclass's Pydantic hooks, so object keywords round-trip without riding on an `Annotated` annotation.

### validate

```python
validate(data: AnnotationType) -> AnnotationType
```

Validate the raw mapping, returning it unchanged or raising `ValueError`.

### json_schema_keyword

```python
json_schema_keyword() -> JsonSchemaValue
```

Return this applicator's keyword fragment for the dumped JSON Schema.

## Contains

```python
Contains(
    *, branch: AnnotationType, min_contains: int, max_contains: int | None
)
```

Bases: `AnnotationApplicator`

Enforce JSON Schema `contains` / `minContains` / `maxContains` on an array.

Counts how many array elements validate against the `contains` subschema and requires that count to stay within `[min_contains, max_contains]`. Attached as `Annotated` metadata on the array's `list[...]` annotation; the subschema may be a `ForwardRef` resolved lazily via `bind_namespace` (a `contains` that points at a `$ref`).

Initialize with the `contains` subschema annotation and the match-count bounds.

Parameters:

| Name           | Type             | Description                                                   | Default                                                     |
| -------------- | ---------------- | ------------------------------------------------------------- | ----------------------------------------------------------- |
| `branch`       | `AnnotationType` | The contains subschema annotation (may be a ForwardRef).      | *required*                                                  |
| `min_contains` | `int`            | Minimum number of matching elements (minContains, default 1). | *required*                                                  |
| `max_contains` | \`int            | None\`                                                        | Maximum number of matching elements (maxContains), or None. |

## DependentSchemas

```python
DependentSchemas(*, branches: dict[str, AnnotationType])
```

Bases: `ObjectApplicator`

Enforce JSON Schema `dependentSchemas`: a present property triggers a whole-object schema.

For each `{property: subschema}` pair, when the property is present in the object the entire instance must also validate against the subschema. Used from a `before` model validator on object models; subschemas may be `ForwardRef` (pointing at a `$ref`), resolved lazily via `bind_namespace`.

Initialize with the property-to-subschema mapping.

Parameters:

| Name       | Type                        | Description                                                                              | Default    |
| ---------- | --------------------------- | ---------------------------------------------------------------------------------------- | ---------- |
| `branches` | `dict[str, AnnotationType]` | Mapping of trigger property name to its subschema annotation (each may be a ForwardRef). | *required* |

### json_schema_keyword

```python
json_schema_keyword() -> JsonSchemaValue
```

Return the `dependentSchemas` keyword fragment for the dumped JSON Schema.

### validate

```python
validate(data: AnnotationType) -> AnnotationType
```

Apply each triggered subschema to the whole instance.

Parameters:

| Name   | Type             | Description                                                                | Default    |
| ------ | ---------------- | -------------------------------------------------------------------------- | ---------- |
| `data` | `AnnotationType` | The raw input mapping (other input is left for type validation to reject). | *required* |

Returns:

| Type             | Description                                                   |
| ---------------- | ------------------------------------------------------------- |
| `AnnotationType` | The input unchanged when every triggered subschema validates. |

Raises:

| Type         | Description                                                         |
| ------------ | ------------------------------------------------------------------- |
| `ValueError` | When a present property's subschema does not validate the instance. |

## IfThenElse

```python
IfThenElse(
    *,
    if_branch: AnnotationType,
    then_branch: AnnotationType | None,
    else_branch: AnnotationType | None
)
```

Bases: `AnnotationApplicator`, `ObjectApplicator`

Enforce JSON Schema `if` / `then` / `else` conditional application.

If the instance validates against `if`, it must also validate against `then`; otherwise it must validate against `else`. `then` / `else` are optional (a missing branch imposes no constraint). All checks run on the *raw* input. Used both as `Annotated` metadata (a wrap-validator) on value annotations and via `check` from a `before` model validator on a root object model. Subschemas may be `ForwardRef` (pointing at a `$ref`), resolved lazily via `bind_namespace`.

Initialize with the `if` / `then` / `else` subschema annotations.

Parameters:

| Name          | Type             | Description                                       | Default                                          |
| ------------- | ---------------- | ------------------------------------------------- | ------------------------------------------------ |
| `if_branch`   | `AnnotationType` | The if condition subschema (may be a ForwardRef). | *required*                                       |
| `then_branch` | \`AnnotationType | None\`                                            | The then subschema applied on a match, or None.  |
| `else_branch` | \`AnnotationType | None\`                                            | The else subschema applied on no match, or None. |

### json_schema_keyword

```python
json_schema_keyword() -> JsonSchemaValue
```

Return the `if` / `then` / `else` keyword fragment for the dumped JSON Schema.

### validate

```python
validate(value: AnnotationType) -> AnnotationType
```

Apply the `then` / `else` branch selected by the `if` condition.

Parameters:

| Name    | Type             | Description          | Default    |
| ------- | ---------------- | -------------------- | ---------- |
| `value` | `AnnotationType` | The raw input value. | *required* |

Returns:

| Type             | Description                                             |
| ---------------- | ------------------------------------------------------- |
| `AnnotationType` | The value unchanged when the selected branch validates. |

Raises:

| Type         | Description                                           |
| ------------ | ----------------------------------------------------- |
| `ValueError` | When the selected branch does not validate the value. |

## Not

```python
Not(*, branch: AnnotationType)
```

Bases: `AnnotationApplicator`, `ObjectApplicator`

Enforce JSON Schema `not`: the instance must NOT validate against the subschema.

Used two ways, both checking the *raw* input (before the host type coerces it):

- as `Annotated` metadata on a value annotation (a wrap-validator), for non-object values and nested objects/dicts;
- via `matches`, from a `before` model validator on a root object model (which bypasses the annotation path).

The subschema may be a `ForwardRef` (a `not` pointing at a `$ref`), resolved lazily through `bind_namespace`.

Initialize with the `not` subschema annotation.

Parameters:

| Name     | Type             | Description                                         | Default    |
| -------- | ---------------- | --------------------------------------------------- | ---------- |
| `branch` | `AnnotationType` | The not subschema annotation (may be a ForwardRef). | *required* |

### json_schema_keyword

```python
json_schema_keyword() -> JsonSchemaValue
```

Return the `not` keyword fragment for the dumped JSON Schema.

### matches

```python
matches(value: AnnotationType) -> bool
```

Return whether a value validates against the `not` subschema.

Parameters:

| Name    | Type             | Description          | Default    |
| ------- | ---------------- | -------------------- | ---------- |
| `value` | `AnnotationType` | The raw input value. | *required* |

Returns:

| Type   | Description                                                          |
| ------ | -------------------------------------------------------------------- |
| `bool` | True when the value validates against not (and so must be rejected). |

### validate

```python
validate(value: AnnotationType) -> AnnotationType
```

Reject inputs matching the `not` subschema (whole-value assertion on the raw input).

Parameters:

| Name    | Type             | Description          | Default    |
| ------- | ---------------- | -------------------- | ---------- |
| `value` | `AnnotationType` | The raw input value. | *required* |

Returns:

| Type             | Description                                                   |
| ---------------- | ------------------------------------------------------------- |
| `AnnotationType` | The value unchanged when it does not match the not subschema. |

Raises:

| Type         | Description                               |
| ------------ | ----------------------------------------- |
| `ValueError` | When the value matches the not subschema. |

## OneOf

```python
OneOf(*, branches: Iterable[AnnotationType])
```

Bases: `AnnotationApplicator`

Enforce JSON Schema `oneOf` semantics: exactly one branch must match.

Python `Union` accepts a value when *any* branch matches (`anyOf` semantics), so this wrap-validator additionally counts matching branches and rejects inputs that match zero or more than one branch.

Initialize with union branch annotations.

Parameters:

| Name       | Type                       | Description                                        | Default    |
| ---------- | -------------------------- | -------------------------------------------------- | ---------- |
| `branches` | `Iterable[AnnotationType]` | Union branch annotations (may contain ForwardRef). | *required* |

### as_annotation

```python
as_annotation() -> AnnotationType
```

Build the field annotation: union of branches with this validator attached.

The plain `Union` is required: it drives Pydantic coercion and serialization, keeps the field type honest for static checkers, and lets `model_rebuild` resolve `ForwardRef` branches (which only works for refs in annotations).

Returns:

| Type             | Description                    |
| ---------------- | ------------------------------ |
| `AnnotationType` | Annotated\[Union[...], self\]. |

## PatternProperties

```python
PatternProperties(*, branches: dict[str, AnnotationType])
```

Bases: `ObjectApplicator`

Enforce JSON Schema `patternProperties`: regex-keyed property-value subschemas.

Every property whose name matches a regex must have a value validating against that regex's subschema (a name may match several patterns, and must then satisfy all of them). Used from a `before` model validator on object models; subschemas may be `ForwardRef` (pointing at a `$ref`), resolved lazily via `bind_namespace`.

Initialize with the pattern-to-subschema mapping.

Parameters:

| Name       | Type                        | Description                                                                                            | Default    |
| ---------- | --------------------------- | ------------------------------------------------------------------------------------------------------ | ---------- |
| `branches` | `dict[str, AnnotationType]` | Mapping of regex (patternProperties key) to its value subschema annotation (each may be a ForwardRef). | *required* |

### json_schema_keyword

```python
json_schema_keyword() -> JsonSchemaValue
```

Return the `patternProperties` keyword fragment for the dumped JSON Schema.

### validate

```python
validate(data: AnnotationType) -> AnnotationType
```

Validate every matching property's value against its pattern's subschema.

Parameters:

| Name   | Type             | Description                                                                | Default    |
| ------ | ---------------- | -------------------------------------------------------------------------- | ---------- |
| `data` | `AnnotationType` | The raw input mapping (other input is left for type validation to reject). | *required* |

Returns:

| Type             | Description                                             |
| ---------------- | ------------------------------------------------------- |
| `AnnotationType` | The input unchanged when every matched value validates. |

Raises:

| Type         | Description                                         |
| ------------ | --------------------------------------------------- |
| `ValueError` | When a matching property's value does not validate. |

## PrefixItems

```python
PrefixItems(*, prefixes: Iterable[AnnotationType], tail: AnnotationType | None)
```

Bases: `AnnotationApplicator`

Enforce JSON Schema `prefixItems`: positional (tuple-style) array validation.

Element `i` is validated against `prefixItems[i]`; elements past the prefix are validated against the array's `items` schema (the 2020-12 tail), or left unconstrained when `items` is absent. Attached as `Annotated` metadata on a `list[Any]` base; prefix / tail subschemas may be `ForwardRef` (pointing at a `$ref`), resolved lazily via `bind_namespace`.

Initialize with the positional subschema annotations and the tail schema.

Parameters:

| Name       | Type                       | Description                                                      | Default                                                                                                                  |
| ---------- | -------------------------- | ---------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `prefixes` | `Iterable[AnnotationType]` | One annotation per prefixItems entry (each may be a ForwardRef). | *required*                                                                                                               |
| `tail`     | \`AnnotationType           | None\`                                                           | The items annotation for elements past the prefix, or None when items is absent (extra elements are then unconstrained). |

## PropertyNames

```python
PropertyNames(*, branch: AnnotationType)
```

Bases: `ObjectApplicator`

Enforce JSON Schema `propertyNames`: every property name must match the subschema.

Property names are always strings, so the subschema typically constrains the string (a `pattern`, `maxLength`, `enum`, ...). Used from a `before` model validator on object models; the subschema may be a `ForwardRef` (pointing at a `$ref`), resolved lazily via `bind_namespace`.

Initialize with the `propertyNames` subschema annotation.

Parameters:

| Name     | Type             | Description                                                                    | Default    |
| -------- | ---------------- | ------------------------------------------------------------------------------ | ---------- |
| `branch` | `AnnotationType` | The subschema every property name must validate against (may be a ForwardRef). | *required* |

### json_schema_keyword

```python
json_schema_keyword() -> JsonSchemaValue
```

Return the `propertyNames` keyword fragment for the dumped JSON Schema.

### validate

```python
validate(data: AnnotationType) -> AnnotationType
```

Validate every property name against the subschema.

Parameters:

| Name   | Type             | Description                                                                | Default    |
| ------ | ---------------- | -------------------------------------------------------------------------- | ---------- |
| `data` | `AnnotationType` | The raw input mapping (other input is left for type validation to reject). | *required* |

Returns:

| Type             | Description                                    |
| ---------------- | ---------------------------------------------- |
| `AnnotationType` | The input unchanged when every name validates. |

Raises:

| Type         | Description                                                   |
| ------------ | ------------------------------------------------------------- |
| `ValueError` | When a property name does not validate against the subschema. |
