# Block installing known-malware dependencies (OSV MAL records) before any package code runs.
# Exported here so every `uv sync` / `uv add` run through `just` is checked — CI and local alike.
# `malware-check` is a `uv` preview feature; naming it also silences its experimental warning.
export UV_MALWARE_CHECK := "1"
export UV_PREVIEW_FEATURES := "malware-check"

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
    uv run mypy
    uv run pyright
    uv run codespell
    npx --yes markdownlint-cli2

# Audit dependencies for known vulnerabilities and abandoned packages (OSV-backed `uv audit`)
audit:
    uv audit --preview-features audit-command

# Audit GitHub Actions workflows for security issues (`zizmor`)
audit-workflows:
    uvx zizmor --offline .github/workflows/

# Run pre-commit on all files
precommit:
    uv run pre-commit run --all-files

# Run all checks
all: format lint audit audit-workflows test docs-build

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
    just ci-test-floor
    just ci-test-ceil

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
        git commit -m "chore(version): update to \`$version\`"
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
    uv run --no-sync ruff format --check
    uv run --no-sync ruff check
    uv run --no-sync mypy
    uv run --no-sync pyright
    uv run --no-sync codespell
    npx --yes markdownlint-cli2

# Run tests with coverage XML output for CI
ci-test:
    uv run --no-sync coverage run -m pytest
    uv run --no-sync coverage combine
    uv run --no-sync coverage report
    uv run --no-sync coverage xml

# Test the dependency FLOOR: lowest Python + lowest direct deps our bounds allow.
# `--resolution lowest-direct` re-resolves direct deps to their declared minimums (e.g.
# `pydantic>=2.13.0` -> `2.13.0`), proving the floor actually resolves and passes. Isolated env
# (never touches `.venv`); no coverage gate.
ci-test-floor:
    UV_PROJECT_ENVIRONMENT=.venv-floor uv run --python 3.12 --resolution lowest-direct --no-default-groups --group test pytest

# Test the dependency CEILING: latest stable Python + highest resolvable deps.
# `--upgrade` ignores the lockfile pins and re-resolves to the latest allowed versions (within
# `exclude-newer`), catching breakage from a new dependency release before it reaches the lockfile.
# Isolated env; no coverage gate.
ci-test-ceil:
    UV_PROJECT_ENVIRONMENT=.venv-ceil uv run --python 3.14 --upgrade --no-default-groups --group test pytest

# Build package and check metadata in CI
ci-build:
    rm -rf dist/
    uv build
    uvx twine check dist/*

# Smoke-test a just-published release: install it FROM PyPI into a throwaway env and verify it
# imports and converts a real schema. `--isolated --no-project` builds the env from the index only
# (ignores the local source), so this exercises the actual published wheel.
#
# NOTE: `--exclude-newer-package "pydantic-jsonschema=2999-12-31"` is required. Our `[tool.uv]
# exclude-newer = "7 days"` cooldown is read because `just` runs inside the repo, and it rejects the
# just-released version as "too new" (it is 0 days old). The override lifts the cutoff for OUR
# package only (a far-future date = no limit); dependencies keep the cooldown. Without it:
#   uv run --with 'pydantic-jsonschema==<fresh version>' ...
#   # -> error: ... filtered by `exclude-newer` ... requirements are unsatisfiable
ci-smoke-test version:
    uv run --isolated --no-project --exclude-newer-package "pydantic-jsonschema=2999-12-31" --with "pydantic-jsonschema=={{ version }}" python -c "from pydantic_jsonschema import Schema, to_model; print(to_model(Schema.model_validate({'type': 'object', 'properties': {'x': {'type': 'integer'}}, 'required': ['x']}))(x=1).model_dump())"

# Build documentation in CI
ci-docs-build:
    uv run --no-sync mkdocs build

# Deploy versioned docs to a single-commit `gh-pages` in CI (history never grows).
#
# `mike` keeps every version in the `gh-pages` *tree*, but each `mike deploy --push` adds a
# commit carrying a full site snapshot, so the branch history balloons over time. Instead we
# deploy locally (no `--push`), then collapse the whole branch into one orphan commit and
# force-push it — each release replaces `gh-pages` rather than appending to it.
# See: https://github.com/ag2ai/ag2/pull/2989
ci-docs-deploy version: _ci-configure-git
    #!/usr/bin/env bash
    set -euo pipefail
    # Bring the existing versions local so `mike` preserves them in the new tree.
    git fetch origin gh-pages:gh-pages 2>/dev/null || true
    uv run --no-sync mike deploy --update-aliases "{{version}}" latest
    uv run --no-sync mike set-default latest
    # Squash the entire branch to one orphan commit, then replace the remote branch.
    git checkout gh-pages
    git checkout --orphan _gh_pages_squashed
    git add --all
    git commit --quiet --message "docs: deploy {{version}}"
    git push --force origin _gh_pages_squashed:gh-pages

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
    # Remove throwaway envs (`.venv312`-`.venv315`, `.venv-floor`, `.venv-ceil`) but keep the
    # main `.venv` so a clean doesn't force a full re-sync of the working environment.
    find . -maxdepth 1 -type d -name ".venv*" ! -name ".venv" -exec rm -rf {} +
    find . -type d -name __pycache__ -exec rm -rf {} +
    find . -type f -name "*.pyc" -delete
