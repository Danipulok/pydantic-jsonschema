# Contributing to Pydantic JSON Schema

Thank you for your interest in contributing to Pydantic JSON Schema!

## Installation and Setup

### Prerequisites

You'll need:

- **Python 3.12+**
- **[uv](https://docs.astral.sh/uv/)** - Fast Python package installer
- **[just](https://github.com/casey/just)** - Command runner (optional, but recommended)

### Setup Steps

1. **[Fork the repository](https://github.com/Danipulok/pydantic-jsonschema/fork)** on GitHub

1. **Clone your fork:**

    ```bash
    git clone <https://github.com/YOUR-USERNAME/pydantic-jsonschema.git>
    cd pydantic-jsonschema
    ```

1. **Install dependencies:**

    ```bash
    just install
    ```

This will:

- Install all dependencies (`uv sync --frozen --all-extras --all-packages`)
- Install pre-commit hooks (`pre-commit install`)

## Development Workflow

We use [just](https://github.com/casey/just) for development tasks.
Run `just` to see all available commands.

### Running Tests

Run the test suite with coverage:

```bash
just test
```

Generate HTML coverage report:

```bash
just testcov
```

Test across all supported Python versions (3.12, 3.13, 3.14):

```bash
just test-all-python
```

### Code Formatting and Linting

Auto-format code with Ruff:

```bash
just format
```

Run all linting checks (Ruff + mypy):

```bash
just lint
```

Run pre-commit hooks on all files:

```bash
just precommit
```

Run all checks (format + lint + test + build docs):

```bash
just all
```

### Working with Documentation

Build the documentation:

```bash
just docs-build
```

Serve documentation locally with live reload:

```bash
just docs-serve
```

Then visit <http://127.0.0.1:8000>

## Code Style

- We use **Ruff** for linting and formatting
- Type hints are required for all public APIs
- Docstrings are required for all public APIs
- All code must pass `mypy` strict mode

## Testing Requirements

- All new features must include tests
- Maintain 100% test coverage
- Tests should be clear and well-documented
- Use descriptive test names

## Pull Request Process

1. Create a new branch for your changes:

    ```bash
    git checkout -b feature/your-feature-name
    ```

1. Make your changes and ensure all checks pass:

    ```bash
    just all
    ```

1. Commit your changes with a clear message:

    ```bash
    git commit -m "feat(scope): brief description of changes"
    ```

1. Push to your fork and create a pull request:

    ```bash
    git push origin feature/your-feature-name
    ```

1. In your PR description:
   - Describe what your changes do
   - Link to any related issues
   - Include examples if adding new features
   - Note any breaking changes

## Commit Message Guidelines

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification.

**Format:**

```text
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:**

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `chore`: Maintenance tasks
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `perf`: Performance improvements

**Examples:**

- `feat(converters): add support for custom format validators`
- `fix(schema): resolve nested schema references correctly`
- `docs(examples): update LLM validation examples`
- `chore(deps): update pydantic to 2.10.0`

## Documentation Guidelines

Documentation is crucial! When adding features or making changes:

### Update Documentation Files

- Add examples showing **how** to use the feature, not just what it is
- Focus on use cases and practical applications
- Keep examples concise and self-contained
- Use real-world scenarios when possible

### Documentation Style

We follow a style similar to [Pydantic AI](https://ai.pydantic.dev/):

- **Code-first**: Show examples before explanations
- **Use-case driven**: Demonstrate WHY someone would use a feature
- **Progressive complexity**: Start simple, then show advanced usage
- **Practical examples**: Real-world scenarios, not contrived examples

### Where to Add Documentation

- **New features**: Add to relevant section in `docs/`
- **Examples**: Add complete examples to `examples/` and link it in docs
- **Breaking changes**: Note in relevant docs + update migration guide
- **API changes**: Update inline docstrings

## Questions?

If you have questions or need help:

- [Open a discussion](https://github.com/Danipulok/pydantic-jsonschema/discussions) on GitHub
- Check [existing issues](https://github.com/Danipulok/pydantic-jsonschema/issues) and PRs
- Review the [documentation](https://danipulok.github.io/pydantic-jsonschema/)

Thank you for contributing!
