# Installation

Pydantic JSON Schema is available on PyPI as
[`pydantic-jsonschema`](https://pypi.org/project/pydantic-jsonschema/), so installation is as
simple as:

=== "uv"

    ```bash
    uv add pydantic-jsonschema
    ```

=== "pip"

    ```bash
    pip install pydantic-jsonschema
    ```

(Requires Python 3.12+)

This installs the `pydantic_jsonschema` package, plus the core dependencies required to create and
validate generated models:

- [`pydantic`](https://docs.pydantic.dev/) for model creation and validation.
- [`openapi-pydantic`](https://github.com/kuimono/openapi-pydantic) for JSON Schema types such as
  `Schema`, `Reference`, and `DataType`.

## Optional dependencies

Pydantic JSON Schema has optional dependencies for `format` validation.

Use `formats-base` for standard JSON Schema formats such as email, hostname, URI, and IRI:

=== "uv"

    ```bash
    uv add 'pydantic-jsonschema[formats-base]'
    ```

=== "pip"

    ```bash
    pip install 'pydantic-jsonschema[formats-base]'
    ```

Use `formats-extra` for domain-specific formats such as payment cards, phone numbers, colors,
country codes, and MAC addresses:

=== "uv"

    ```bash
    uv add 'pydantic-jsonschema[formats-extra]'
    ```

=== "pip"

    ```bash
    pip install 'pydantic-jsonschema[formats-extra]'
    ```

To install both groups:

=== "uv"

    ```bash
    uv add 'pydantic-jsonschema[formats-all]'
    ```

=== "pip"

    ```bash
    pip install 'pydantic-jsonschema[formats-all]'
    ```

See [Format Validators](formats.md) for supported formats and usage examples.

## Install from repository

If you prefer to install directly from a repository checkout:

=== "uv"

    ```bash
    uv add 'git+https://github.com/Danipulok/pydantic-jsonschema@main'
    ```

=== "pip"

    ```bash
    pip install 'git+https://github.com/Danipulok/pydantic-jsonschema@main'
    ```

For local development, use the [contributing guide](contributing.md) instead. It is the source of
truth for development dependencies, `just` recipes, documentation checks, and PR workflow.

## Next Steps

- [Converters](converters.md) - Create Pydantic models from JSON Schema
- [Format Validators](formats.md) - Add validation for JSON Schema `format` values
- [Examples](examples.md) - Run complete examples
