# Default recipe to display help information
default:
    @just --list

# Format code with ruff
format:
    uv run ruff format pydantic_jsonschema tests
    uv run ruff check pydantic_jsonschema tests --fix

# Run linting checks
lint:
    uv run ruff check pydantic_jsonschema tests
    uv run mypy pydantic_jsonschema

# Run tests
test:
    uv run pytest tests/

# Run tests with coverage
test-cov:
    uv run pytest tests/ --cov=pydantic_jsonschema --cov-report=term-missing

# Run all checks (lint + test)
check: lint test

# Install dependencies
install:
    uv sync --all-groups

# Install pre-commit hooks
install-hooks:
    uv run pre-commit install

# Run pre-commit on all files
pre-commit:
    uv run pre-commit run --all-files

# Clean up generated files
clean:
    rm -rf .pytest_cache
    rm -rf .ruff_cache
    rm -rf .mypy_cache
    rm -rf .coverage
    rm -rf htmlcov
    find . -type d -name __pycache__ -exec rm -rf {} +
    find . -type f -name "*.pyc" -delete
