# Pydantic JSON Schema

[![CI](https://github.com/danipulok/pydantic-jsonschema/workflows/CI/badge.svg)](https://github.com/danipulok/pydantic-jsonschema/actions)
[![Coverage](https://img.shields.io/codecov/c/github/danipulok/pydantic-jsonschema)](https://codecov.io/gh/danipulok/pydantic-jsonschema)
[![PyPI](https://img.shields.io/pypi/v/pydantic-jsonschema.svg)](https://pypi.org/project/pydantic-jsonschema/)
[![Python Versions](https://img.shields.io/pypi/pyversions/pydantic-jsonschema.svg)](https://pypi.org/project/pydantic-jsonschema/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/danipulok/pydantic-jsonschema/blob/main/LICENSE)
[![Docs](https://img.shields.io/badge/docs-latest-blue.svg)](https://danipulok.github.io/pydantic-jsonschema/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![mypy](https://img.shields.io/badge/types-mypy-blue.svg)](https://github.com/python/mypy)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)

**Pydantic turns models into JSON Schema. This library does the reverse** — it turns a
JSON Schema into a Pydantic model, so you can validate data against a schema you already
have, with all of Pydantic's runtime checks and editor support.

Reach for it when the schema comes first: API contracts, config files, tool definitions,
or validating LLM output against a fixed shape.

## Installation

```bash
uv add pydantic-jsonschema
```

Requires Python 3.12+. See the
[installation guide](https://danipulok.github.io/pydantic-jsonschema/latest/install/)
for optional validator libraries.

## Quick start

```python
from pydantic_jsonschema import Schema, to_model

schema = Schema.model_validate({
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "age": {"type": "integer", "minimum": 0},
    },
    "required": ["name"],
})

User = to_model(schema, model_name="User")

user = User(name="Alice", age=30)
print(user.model_dump())
#> {'name': 'Alice', 'age': 30}
```

## What's inside

Four building blocks.

### 1. The schema model — `Schema` & `Reference`

A Pydantic model for JSON Schema itself: parse, inspect, and serialize schemas with full
type safety. `$ref`s are parsed as `Reference` objects and resolved during conversion.

```python
from pydantic_jsonschema import DataType, Schema

schema = Schema(
    type=DataType.OBJECT,
    properties={"name": Schema(type=DataType.STRING)},
    required=["name"],
)

print(schema.model_dump_json())
#> {"type":"object","properties":{"name":{"type":"string"}},"required":["name"]}
```

### 2. The converter — `to_model` / `SchemaConverter`

Turns a `Schema` into a Pydantic model (see [Quick start](#quick-start)). It resolves
`$ref` / `$defs`, maps `anyOf` / `oneOf` (including discriminated unions) / `allOf` to
Python types, and applies string, number, array, and object constraints as Pydantic
validation.

### 3. Formats

Built-in types for every `format` in the JSON Schema spec (`email`, `uri`, `uuid`,
`date-time`, `hostname`, `json-pointer`, `regex`, and more) — with zero extra
dependencies. Map your own Pydantic type for custom formats.

```python
from pydantic_jsonschema import Schema, to_model
from pydantic_jsonschema.formats import Email

schema = Schema.model_validate({
    "type": "object",
    "properties": {"email": {"type": "string", "format": "email"}},
    "required": ["email"],
})

User = to_model(schema, formats={"email": Email})

print(User(email="alice@example.com").email)
#> alice@example.com
```

### 4. Rules

Per-node input coercion and output serialization, matched by type, by JSON Pointer path, or by an
arbitrary predicate — inspired by [adaptix](https://github.com/reagento/adaptix). A `Rule` pairs a
matcher (`ByType`, `ByPath`, `ByFunc`) with one action (`Before`, `After`, `Override`, `Dump`), so
a field declared as array-of-string can accept a comma-separated string, and dump back as one.

```python
from pydantic_jsonschema import Schema, to_model
from pydantic_jsonschema.rules import Before, ByType, Rule


def csv_to_list(value: str | list[str]) -> list[str]:
    return value.split(",") if isinstance(value, str) else value


schema = Schema.model_validate({
    "type": "object",
    "properties": {"tags": {"type": "array", "items": {"type": "string"}}},
    "required": ["tags"],
})

User = to_model(schema, rules=[Rule(ByType(list[str]), Before(csv_to_list))])

print(User(tags="a,b,c").tags)
#> ['a', 'b', 'c']
```

## Documentation

[https://danipulok.github.io/pydantic-jsonschema/](https://danipulok.github.io/pydantic-jsonschema/)

## Acknowledgments

- [vgavro](https://github.com/vgavro) — initial library idea and early guidance
- [bodlan](https://github.com/bodlan) — early documentation review and feedback

## License

MIT License - see [LICENSE](LICENSE) for details.
