# --- General ---

# Default recipe to display help information
default:
    @just --list

# Check that `uv` is installed
_check-uv:
    @uv --version > /dev/null || echo "Please install uv: https://docs.astral.sh/uv/getting-started/installation"

# --- Setup ---

# Install the package, dependencies, and pre-commit for local development
install: _check-uv
    uv sync --frozen --all-extras --all-packages
    uv run pre-commit install --install-hooks

# Install and synchronize an interpreter for every supported python version
install-all-python:
    UV_PROJECT_ENVIRONMENT=.venv312 uv sync --python 3.12 --frozen --no-default-groups --group test
    UV_PROJECT_ENVIRONMENT=.venv313 uv sync --python 3.13 --frozen --no-default-groups --group test
    UV_PROJECT_ENVIRONMENT=.venv314 uv sync --python 3.14 --frozen --no-default-groups --group test
    UV_PROJECT_ENVIRONMENT=.venv315 uv sync --python 3.15 --frozen --no-default-groups --group test

# Update local packages and `uv.lock`
sync: _check-uv
    uv sync --all-extras --all-packages

# --- Code quality ---

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

# Run pre-commit on all files
precommit:
    uv run pre-commit run --all-files

# Run all checks
all: format lint test docs-build

# --- Tests ---

# Run tests and show coverage report
test:
    uv run coverage run -m pytest
    uv run coverage combine
    uv run coverage report

# Run tests for every supported python version and show combined coverage report
test-all-python: install-all-python
    UV_PROJECT_ENVIRONMENT=.venv312 uv run --python 3.12 --no-default-groups --group test coverage run -p -m pytest
    UV_PROJECT_ENVIRONMENT=.venv313 uv run --python 3.13 --no-default-groups --group test coverage run -p -m pytest
    UV_PROJECT_ENVIRONMENT=.venv314 uv run --python 3.14 --no-default-groups --group test coverage run -p -m pytest
    UV_PROJECT_ENVIRONMENT=.venv315 uv run --python 3.15 --no-default-groups --group test coverage run -p -m pytest
    uv run coverage combine
    uv run coverage report

# Run tests and generate an HTML coverage report
testcov: test
    uv run coverage html

# Update `inline_snapshot` values in tests after behavior changes
test-fix-snapshots:
    uv run pytest --inline-snapshot=fix

# --- Documentation ---

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

# Add alias for a documentation version
docs-alias version alias:
    uv run mike alias --push --update-aliases {{version}} {{alias}}

# Set default version for documentation
docs-set-default version:
    uv run mike set-default --push {{version}}

# List all deployed documentation versions
docs-list:
    uv run mike list

# Delete a documentation version
docs-delete version:
    uv run mike delete --push {{version}}

# --- Release ---

# Generate `docs/changelog.md` from git history via `git-cliff`
changelog tag="":
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "{{tag}}" ]]; then
        uv run git-cliff --tag "{{tag}}" -o docs/changelog.md
    else
        uv run git-cliff -o docs/changelog.md
    fi
    printf '%s\n' "$(< docs/changelog.md)" > docs/changelog.md

# Tag a release and push (triggers `release.yml` workflow)
release version: (_check-release-version version)
    #!/usr/bin/env bash
    set -euo pipefail
    version="{{version}}"
    if ! grep -q "^## \[$version\]" docs/changelog.md; then
        printf 'docs/changelog.md must contain release section `## [%s]`.\n' "$version" >&2
        exit 2
    fi
    if [[ -n "$(git status --porcelain)" ]]; then
        printf 'Working tree must be clean before release.\n' >&2
        exit 2
    fi
    git tag "v$version"
    git push origin main "v$version"

# Generate changelog, commit it, and run `just release`
release-auto version: (_check-release-version version)
    #!/usr/bin/env bash
    set -euo pipefail
    version="{{version}}"
    if [[ -n "$(git status --porcelain)" ]]; then
        printf 'Working tree must be clean before release.\n' >&2
        exit 2
    fi
    just changelog "v$version"
    if [[ -n "$(git status --porcelain docs/changelog.md)" ]]; then
        git add docs/changelog.md
        git commit -m "docs(changelog): add \`$version\` release section"
    fi
    just release "$version"

# Validate release version format
_check-release-version version:
    #!/usr/bin/env bash
    set -euo pipefail
    version="{{version}}"
    if [[ "$version" == v* ]]; then
        printf 'Release version must not start with `v`: %s\n' "$version" >&2
        exit 2
    fi
    if [[ ! "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+((a|b|rc)[0-9]+)?$ ]]; then
        printf 'Release version must look like `0.0.1`, `1.0.0b1`, or `1.0.0rc1`: %s\n' "$version" >&2
        exit 2
    fi

# --- CI (no `pre-commit`, no interactive tools) ---

# Install dependencies for CI
ci-install: _check-uv
    uv sync --frozen --all-extras --all-packages

# Install test dependencies only for CI (skips the `docs` group: `Pillow` has no Python 3.15 wheel)
ci-install-test: _check-uv
    uv sync --frozen --no-default-groups --group test

# Install docs dependencies for CI
ci-install-docs: _check-uv
    uv sync --group docs

# Install release dependencies for CI
ci-install-release: _check-uv
    uv sync --group release

# Run linting in CI
ci-lint:
    uv run ruff format --check
    uv run ruff check
    uv run mypy .
    uv run codespell
    npx --yes markdownlint-cli2

# Run tests with coverage XML output for CI
ci-test:
    uv run coverage run -m pytest
    uv run coverage combine
    uv run coverage report
    uv run coverage xml

# Build package and check metadata in CI
ci-build:
    rm -rf dist/
    uv build
    uvx twine check dist/*

# Build documentation in CI
ci-docs-build: docs-build

# Deploy versioned documentation and update `latest` alias in CI
ci-docs-deploy version: _ci-configure-git (docs-deploy-version version) (docs-alias version "latest") (docs-set-default "latest")

# Generate release notes for CI
ci-release-notes output:
    uv run --no-sync git-cliff --latest --strip header -o {{output}}

# Configure git identity for CI commits
_ci-configure-git:
    git config user.name 'github-actions[bot]'
    git config user.email 'github-actions[bot]@users.noreply.github.com'

# --- Maintenance ---

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
