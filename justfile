# Directories to check
SRC_DIR := "pydantic_jsonschema"
TEST_DIR := "tests"
CODE_DIRS := SRC_DIR + " " + TEST_DIR

# Default recipe to display help information
default:
    @just --list

# Format code with ruff
format:
    uv run ruff format {{CODE_DIRS}}
    uv run ruff check {{CODE_DIRS}} --fix

# Run linting checks
lint:
    uv run ruff check {{CODE_DIRS}}
    uv run mypy {{CODE_DIRS}}

# Run tests
test:
    uv run pytest {{TEST_DIR}}

# Run tests with coverage (require 88% minimum)
test-cov:
    uv run pytest {{TEST_DIR}} --cov={{SRC_DIR}} --cov-report=term-missing --cov-fail-under=88

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
