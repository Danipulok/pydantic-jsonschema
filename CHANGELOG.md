# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2024-11-19

### Added

- Initial release of pydantic-jsonschema
- Core JSON Schema to Pydantic model conversion via `to_model()`
- Lax mode conversion for LLM-friendly validation via `to_lax_model()`
- Support for JSON Schema Draft 2020-12
- Automatic handling of `$ref` and `$defs`
- Schema composition support (`allOf`, `anyOf`, `oneOf`)
- Custom format validators (email, UUID, etc.) via optional dependencies
- Type-safe `Schema`, `DataType`, and `JsonType` models
- `SchemaConverter` and `LaxSchemaConverter` classes for advanced usage
- Comprehensive test suite with 100% coverage
- Full documentation with examples
- Python 3.12+ support

[Unreleased]: https://github.com/Danipulok/pydantic-jsonschema/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Danipulok/pydantic-jsonschema/releases/tag/v0.1.0
