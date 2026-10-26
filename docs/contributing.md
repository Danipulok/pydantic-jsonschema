# Contributing

Thank you for helping improve Pydantic JSON Schema.

## Prerequisites

| Tool            | Required | Purpose                                                 |
|-----------------|----------|---------------------------------------------------------|
| Python 3.12+    | yes      | Supported runtime for development and tests             |
| `uv`            | yes      | Dependency management and Python command runner         |
| `just`          | yes      | Project command runner used by local and CI workflows   |
| Node.js / `npx` | yes      | Runs `markdownlint-cli2` through the `just lint` recipe |

## Setup

1. Fork the repository on GitHub.

2. Clone your fork:

    ```bash
    git clone <your-fork-url>
    cd pydantic-jsonschema
    ```

3. Install dependencies and hooks:

    ```bash
    just install
    ```

The `just install` recipe runs `uv sync --frozen --all-extras --all-packages` and installs
pre-commit hooks.

## Development Workflow

Run `just` to list all available commands.

| Need                              | Command                | What it runs                                                    |
|-----------------------------------|------------------------|-----------------------------------------------------------------|
| Format code                       | `just format`          | `ruff format` and autofix-only `ruff check`                     |
| Lint everything                   | `just lint`            | `ruff`, `mypy`, `pyright`, `codespell`, and `markdownlint-cli2` |
| Run tests                         | `just test`            | `pytest` with coverage reporting                                |
| Run all supported Python versions | `just test-all-python` | Test suite on every supported Python version                    |
| Generate HTML coverage            | `just testcov`         | `just test` plus `coverage html`                                |
| Run pre-commit hooks              | `just precommit`       | `pre-commit run --all-files`                                    |
| Run the full local gate           | `just all`             | format, lint, tests, and docs build                             |

Before opening a PR, run:

```bash
just all
```

## Documentation Workflow

| Need                                      | Command            |
|-------------------------------------------|--------------------|
| Build the documentation                   | `just docs-build`  |
| Serve documentation locally               | `just docs-serve`  |
| Format and refresh documentation examples | `just docs-format` |

After `just docs-serve`, open <http://127.0.0.1:8000>.

Documentation examples are verified in two ways:

- Python code blocks in documentation files are linted and executed by `tests/test_docs.py`.
- Python files in `examples/` are linted and executed by `tests/test_docs.py`.

The `docs/examples.md` page uses `--8<--` includes, so the page itself is not used as the source
of those code examples. The included `examples/*.py` files are still tested directly.

## Code Style

`just lint` runs `ruff`, `mypy`, `pyright`, `codespell` and `markdownlint`, and it is the gate — if
it passes, the mechanical half of the style is satisfied and no reviewer will argue about it.

- Use `ruff` for formatting and linting.
- Add type hints to public APIs and internal code where type inference is not obvious.
- Use `Sphinx`-style docstrings for public APIs (`:param:`, `:returns:`, `:raises:`).
- Keep `mypy` strict mode passing.
- Keep tests explicit about generated model behavior, validation errors, references, and formats.
- Take at most one positional parameter; everything after it is keyword-only, behind `*`. `ruff`
  enforces it as `PLR0917` outside `tests/`, where `pytest` passes test and fixture arguments by
  name; a helper in `tests/` is called by us and keeps the rule. A signature Python or `pydantic`
  calls positionally (a dunder such as `__exit__`, a `pydantic` hook) takes `# noqa: PLR0917` with
  a comment saying so; `ruff` already skips `@override` methods and `@overload` stubs.
- Use a frozen `dataclass`, never a `NamedTuple`, and log a caught error instead of
  `contextlib.suppress`. `ruff` bans both as `TID251`, and its message says why.

### Conventions the linters cannot check

These are the ones review actually spends its time on, so they are worth knowing before you open a
pull request. The theme behind all of them: a reader who has never seen the code should predict
what it does from the signature.

- **Separate logical blocks with blank lines.** A wall of statements at one indent is the single
  most common thing sent back: eight or more sibling statements with no blank line between them
  is a wall, five to seven is worth a look. A run of plain declarations or a table of one-line
  `if` assignments writing into one container is a table, not a paragraph — leave those unbroken.
- **Guard clauses over nesting.** Each condition returns or raises early; `try` holds only what can
  actually raise, and the success path goes in `else`.
- **A comment on why a branch exists goes above its keyword** — above `except` / `else` / `elif` /
  `finally`, at the same indent, not inside the block.
- **Full names everywhere.** No abbreviations and no single letters, in any scope. The exceptions
  are `_`, `er` for exception variables, `i`/`j`/`k` for matrix indices, `x`/`y`/`z` for geometric
  coordinates, and `cls`/`self`.
- **Two or more keyword arguments in a call go one per line**, with a trailing comma.
- **Catch the narrowest exception that can occur**, and bind it as `er`. A broad catch carries a
  comment saying why the boundary is broad.
- **Constants carry `Final[type]`**, module level and class level alike, never a bare `Final`. A
  meaningful literal at a call site is a missing constant. `__all__` is not such a constant; its
  form is under the `__all__` rule below.
- **Annotate an assignment only when the right-hand side does not state its type.** Literals,
  `None`, empty containers, arithmetic and a declaration with no value need one; a typed call, a
  constructor or a comprehension already says it, and the second copy drifts. A constant keeps its
  `Final[type]` either way, and `__all__` follows its own rule below.
- **`object` is never a type, and `Any` is a last resort** behind a concrete type, a `Protocol` and
  a union — with a comment saying why. Callbacks use a `Protocol` with `__call__`, not `Callable`,
  which loses the parameter names.
- **Structures have field names.** No anonymous tuples in signatures, and a `dict` in a signature
  is a missing `dataclass`, model or `TypedDict`. Raw dicts belong at the boundary.
- **Type aliases use the `type` statement and carry a `Type` suffix** — `type IdType = UUID`.
- **`import datetime as dt`**, never `from datetime import datetime` — the module and the class
  share a name, and the alias keeps every reference unambiguous.
- **Every module defines `__all__`**, and imports live at the top of it. Entry points,
  `conftest.py` and test modules are exempt from `__all__`. An import inside a function carries a
  comment naming the import cycle or the optional dependency that forces it.
- **Only an empty `__all__` is annotated**, as `__all__: list[str] = []`, since an empty list
  states no element type. A non-empty one stays bare, `__all__ = ["Name"]`, and never takes
  `Final`: type checkers read `__all__` by its form
  ([typing spec](https://github.com/python/typing/blob/aa8dab0b63a538330362b9fbaf7ab89ec34e9549/docs/spec/distributing.rst?plain=1#L389-L400)),
  and `Final` turns the `__all__ += [...]` form into an error.
- **Comments say why, in one plain line, ending with a period.** Code a comment would restate
  needs no comment. A continuation line starts at `#` followed by two spaces, one more than the
  first line takes. `# TODO:` is the only tag we use: no `NOTE:`, `FIXME:`, `HACK:` or `XXX:`. A
  non-obvious workaround or guard says why it exists, names what failed without it and links a
  permalink pinned to a commit SHA.
- **Backtick every code entity in prose** — identifiers, paths, commands, flags, env var names,
  versions, config keys — in comments, docstrings, documentation, commit messages and pull
  request descriptions alike.

Tests are held to all of the above, except where a rule exempts them by name; see
[Testing Requirements](#testing-requirements) for what they add on top.

## Testing Requirements

- Add tests for every new feature or behavior change.
- Maintain 100% coverage.
- Prefer direct behavior assertions over implementation-detail assertions.
- Prefer one parametrized test with explicit `pytest.param` ids over near-duplicate tests — the id
  is what a failing CI log names.
- Include validation failure cases when schema constraints should reject input.
- Add documentation examples when a behavior needs user-facing explanation.
- Annotate every test `-> None`, and every fixture, factory and helper in full, parameters
  included. A fixture returning a callable is typed with a `Protocol` in `conftest.py`.
- Mirror the source tree: one source module, one test module, same path under `tests/`.
- Keep the environment out of tests — no `os.environ`, no `os.getenv`, no `dotenv`. A fixture
  builds the prepared object once and each test takes it as a parameter.
- Keep `tests/` to tests, fixtures, `conftest.py` and the shared values in `tests/builders/`. A
  one-off utility belongs in `scripts/`, exposing a function the test imports.

## Pull Request Process

1. Create a new branch:

    ```bash
    git switch -c feat/your-feature-name
    ```

2. Make your changes.

3. Run the full local gate:

    ```bash
    just all
    ```

4. Commit your changes:

    ```bash
    git commit -m "feat(scope): brief description"
    ```

5. Push your branch:

    ```bash
    git push origin feat/your-feature-name
    ```

6. Open a pull request.

In the PR description, include what changed, why it changed, how it was tested, and any breaking
behavior changes.

## Commit Messages

Use one-line [Conventional Commits](https://www.conventionalcommits.org/) messages:

```text
<type>(<scope>): <description>
```

Common types:

| Type       | Use for                                     |
|------------|---------------------------------------------|
| `feat`     | New features                                |
| `fix`      | Bug fixes                                   |
| `docs`     | Documentation changes                       |
| `chore`    | Maintenance tasks                           |
| `refactor` | Code restructuring without behavior changes |
| `test`     | Test additions or updates                   |
| `perf`     | Performance improvements                    |
| `build`    | Build system or packaging changes           |
| `ci`       | CI workflow changes                         |

Examples:

- `feat(converters): add custom format validators`
- `fix(converters): resolve nested schema references`
- `docs(examples): add nested schema conversion example`
- `chore(deps): update pydantic dependency`

## Documentation Guidelines

Documentation should show how to use a feature and why it matters.

When adding or changing behavior:

- Add examples showing realistic input and output.
- Keep examples concise and self-contained.
- Prefer code-first explanations.
- Start with common use cases before edge cases.
- Update API documentation when public functions, classes, or parameters change.
- Update user guides when observable behavior changes.
- Add or update `examples/*.py` when a complete runnable scenario is useful.
- State every fact in one place; elsewhere, link to it instead of repeating it.
- Write plain, short sentences; technical precision over academic prose.
- Use obvious placeholders in examples (`your-api-key-here`, `https://example.com`), never a real
  path, hostname or credential.

## Where to Add Documentation

| Change                      | Where to document it                   |
|-----------------------------|----------------------------------------|
| Converter behavior          | `docs/converters.md`                   |
| Formats                     | `docs/formats.md`                      |
| Complete runnable scenarios | `examples/*.py` and `docs/examples.md` |
| Public API changes          | API docs and public docstrings         |
| Breaking changes            | Relevant guide and migration notes     |

## Questions

If you need help, review the documentation and existing issues before opening a new issue.
