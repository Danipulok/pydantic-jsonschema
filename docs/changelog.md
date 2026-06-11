# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.0.2] — 2026-06-11

### Added

- replace `openapi-pydantic` with our own `Schema`, `Reference` and `DataType`

### Build

- add `docs-alias` recipe and deploy `latest` alias on release
- route all CI commands through `justfile` recipes
- add `test` hook to enforce 100% coverage on commit

### Documentation

- add `0.0.2` release section
- add `inline_snapshot` item to roadmap
- add `Ruff`, `uv`, `mypy`, and `pre-commit` badges
- add acknowledgments section
- add roadmap section

### Fixed

- add `ignore_missing_imports` override for `fqdn`/`rfc3986`
- add `latest` prefix to installation guide link
- allow missing AWS credentials config
- validate URI/IRI component validity, rename `exc` to `er`
- update copyright year to `2026`
- deploy `docs` and route `v0.*` to `TestPyPI`

### Other

- remove `TestPyPI` publishing

### Testing

- add tests for invalid URI/IRI reference validation

## [0.0.1] — 2026-06-11

### Added

- export `Reference` in public API
- add custom `Schema`/`Reference` with `None`-stripping serialization
- add model validators support in lax mode
- implement user-provided coerce functions in lax mode
- implement centralized version management and docs versioning
- add `__version__` and allow direct references
- add PyPI metadata to `pyproject.toml`
- add IRI validators
- add format validators, public API, lax mode, and schema dumping
- initial library with converter, formats, and types

### Build

- add PR title validation for Conventional Commits format
- switch from exclude to include whitelist
- add tag-based release workflow, `git-cliff` changelog, `just release`
- switch to `hatch-vcs` for version from git tags
- configure `hatchling` build targets and exclusions
- add GitHub Actions workflows for CI and PyPI publishing

### Changed

- simplify `sanitize_identifier` with `re.sub`
- remove `SchemaFormat` class and `_base.py` module
- remove all lax model functionality
- add `TYPE_CHECKING` guard for `JsonType` import
- add `__all__` to `_version.py`
- convert builtin formats to Pydantic types
- remove `extra.py` and related tests
- move `markdownlint-cli2` to `justfile` lint
- integrate `codespell` and `markdownlint` into `just lint`
- remove dead `lax.py` per-file ignores
- remove `UP007` ignore from `converters.py`
- remove `FURB162` ignore (timezone)
- remove complexity ignores (`C901`, `PLR0911`, `PLR0912`)
- remove `PLR2004` ignore (magic values)
- remove `A001`/`A004` ignores (shadowing builtins)
- remove `TRY` ignores (`TRY003`/`004`/`300`/`301`)
- remove `EM102` ignore (f-string in exceptions)
- remove `FBT001` ignore (boolean positional args)
- remove `PLW2901` ignore (loop variable overwrite)
- remove `RET504` ignore (unnecessary assignment)
- remove `RUF022` ignore and sort `__all__`
- remove `ERA001` ignore (commented code)
- restructure into package, improve tests
- remove `schema.py` module
- restructure modules, merge lax into `SchemaConverter`
- remove `before_validators` support
- clean up converter logic
- simplify README and `__init__.py`

### Documentation

- set initial release to `0.0.1`
- replace placeholder URLs with actual repository URL
- fix data in license
- simplify `README.md`, add docs and license badges
- clarify `format_validators` behavior
- refresh documentation homepage
- use tabbed installation guide
- align workflow and examples docs
- clarify `object` schema conversion
- explain `model_name` resolution
- improve contribution guidelines
- fix command to use `uv`
- improve contribution workflow documentation
- add `CONTRIBUTING.md` symlink to repo root
- fix `types.md` to reference own module instead of `openapi_pydantic`
- remove stale lax mode references, fix version path and twine command
- simplify PR template, fix docstring style to Sphinx
- apply review feedback across all documentation pages
- fix install command in `README.md` and update `install.md`
- add module docstrings
- fix remaining CSV format examples
- update examples to use JSON format instead of CSV
- enhance theme with auto-switch and darker colors
- resolve TODO items and improve documentation
- add publishing guide for PyPI releases
- add `CHANGELOG.md` for version tracking
- improve documentation and fix examples
- add complete README documentation

### Fixed

- validate `release` version argument
- generate changelog for target tag
- restore fork placeholder in `contributing.md`
- set `ruff` `target-version` to `py312` to match `requires-python`
- rename `SchemaConvertionError` to `SchemaConversionError`
- fix broken optional dependency check in `_validators.py`
- enforce `additionalProperties` for `object` fields
- use correct `#>` print output format
- resolve lint errors and update `uv.lock`
- move `fqdn`/`rfc3986` back to `formats-base` optional extra
- add `fqdn` and `rfc3986` to core dependencies
- configure `codespell` and adjust `markdownlint` integration
- add necessary ignores for existing lint issues

### Other

- run `lint` hook for non-python changes
- run `pre-commit` through `uv` in `install`
- ignore `coverage.xml` artifact
- add `exclude-newer` supply-chain guard, upgrade all dependencies
- add `.python-version` with `3.12`
- ignore `COM812` to fix `ruff format` conflict warning
- wrap `$defs` and `$ref` in backticks in comments and docstrings
- merge `.markdownlint.yaml` into `.markdownlint-cli2.yaml`
- use `# fmt: off` for `#>` markers, remove `ruff.format.exclude`
- add docstrings to package `__init__.py`, remove `D104` ignore
- add missing docstrings, remove `D100`/`D104`/`D105`/`D107` ignores
- reorder `pyproject.toml` sections, `[project]` first
- replace `pytest-examples` git dep with PyPI release
- add `just` CI recipes, use `just ci-*` in all workflow jobs
- pin all actions by SHA, update to latest versions, clean up params
- improve workflow description
- fix errors, restore 100% coverage, exclude scratch files
- update author email, switch `pydantic-extra-types` to PyPI
- add build artifacts to `.gitignore`
- remove override for `tests.*`
- remove override for `pydantic_jsonschema.formats.extra`
- remove override for `fqdn` and `rfc3986`
- remove override for `examples.*`
- add infrastructure (docs site, examples, templates, license)
- resolve remaining `ruff` lint issues
- update `.gitignore`
- enable strict typing for tests
- add `ruff` linting, `justfile`, and `pre-commit`
- add `.gitignore`

### Testing

- remove duplicate tests and WHAT-comments
- add tests for `Schema` `None`-stripping and `Reference` `$ref` key serialization
- add coverage tests for `LaxSchemaConverter` edge cases
- add coverage tests and set `cov-fail-under`
- add comprehensive test suite

[0.0.2]: <https://github.com/Danipulok/pydantic-jsonschema/compare/v0.0.1...v0.0.2>
[0.0.1]: <https://github.com/Danipulok/pydantic-jsonschema/releases/tag/v0.0.1>
