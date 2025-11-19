# Default recipe to display help information
default:
    @just --list

# Check that `uv` is installed
_check-uv:
    @uv --version > /dev/null || echo "Please install uv: https://docs.astral.sh/uv/getting-started/installation"

# Install the package, dependencies, and pre-commit for local development
install: _check-uv
    uv sync --frozen --all-extras --all-packages
    pre-commit install --install-hooks

# Install and synchronize an interpreter for every supported python version
install-all-python:
    UV_PROJECT_ENVIRONMENT=.venv312 uv sync --python 3.12 --frozen --all-extras --all-packages
    UV_PROJECT_ENVIRONMENT=.venv313 uv sync --python 3.13 --frozen --all-extras --all-packages
    UV_PROJECT_ENVIRONMENT=.venv314 uv sync --python 3.14 --frozen --all-extras --all-packages

# Update local packages and `uv.lock`
sync: _check-uv
    uv sync --all-extras --all-packages

# Format code
format:
    uv run ruff format
    uv run ruff check --fix --fix-only

# Run linting
lint:
    uv run ruff format --check
    uv run ruff check
    uv run mypy .
    uv run codespell
    npx --yes markdownlint-cli2

# Run tests and show coverage report
test:
    uv run coverage run -m pytest
    uv run coverage combine
    uv run coverage report

# Run tests for every supported python version and show combined coverage report
test-all-python: install-all-python
    UV_PROJECT_ENVIRONMENT=.venv312 uv run --python 3.12 --all-extras --all-packages coverage run -p -m pytest
    UV_PROJECT_ENVIRONMENT=.venv313 uv run --python 3.13 --all-extras --all-packages coverage run -p -m pytest
    UV_PROJECT_ENVIRONMENT=.venv314 uv run --python 3.14 --all-extras --all-packages coverage run -p -m pytest
    uv run coverage combine
    uv run coverage report

# Run tests and generate an HTML coverage report
testcov: test
    uv run coverage html

# Run pre-commit on all files
precommit:
    uv run pre-commit run --all-files

# Run all checks
all: format lint test docs-build

# Format documentation examples
docs-format:
    uv run pytest tests/test_docs.py --update-examples -v --tb=long

# Build documentation
docs-build:
    uv run mkdocs build

# Serve documentation locally with live reload
docs-serve:
    uv run mkdocs serve

# Deploy documentation to GitHub Pages (latest version)
docs-deploy:
    uv run mike deploy --push --update-aliases latest dev

# Deploy documentation for a specific version
docs-deploy-version version:
    uv run mike deploy --push --update-aliases {{version}}

# Set default version for documentation
docs-set-default version:
    uv run mike set-default --push {{version}}

# List all deployed documentation versions
docs-list:
    uv run mike list

# Delete a documentation version
docs-delete version:
    uv run mike delete --push {{version}}

# Clean up generated files
clean:
    rm -rf .pytest_cache
    rm -rf .ruff_cache
    rm -rf .mypy_cache
    rm -rf .coverage
    rm -rf htmlcov
    rm -rf site
    find . -type d -name __pycache__ -exec rm -rf {} +
    find . -type f -name "*.pyc" -delete
