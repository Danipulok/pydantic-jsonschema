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

This installs the `pydantic_jsonschema` package with [`pydantic`](https://docs.pydantic.dev/) as the only core dependency.

## Third-party validator libraries

All built-in format validators work with zero extra dependencies.
For domain-specific formats such as payment cards, phone numbers, colors, country codes, and MAC addresses, install
[`pydantic-extra-types`](https://github.com/pydantic/pydantic-extra-types) directly:

=== "uv"

    ```bash
    uv add 'pydantic-extra-types[all]'
    ```

=== "pip"

    ```bash
    pip install 'pydantic-extra-types[all]'
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

- [Schema](schema.md) - Schema models, fields, and serialization
- [Converters](converters.md) - Create Pydantic models from JSON Schema
- [Format Validators](formats.md) - Add validation for JSON Schema `format` values
- [Examples](examples.md) - Run complete examples
