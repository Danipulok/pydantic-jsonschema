# Version Management Guide

This document explains how versions are managed in this project.

## Version in Code

The version is defined in a single source of truth:

**`pydantic_jsonschema/_version.py`:**

```python
__version__ = "0.1.0"
```

This version is:

- Automatically read by `hatchling` when building the package
- Imported in `pydantic_jsonschema/__init__.py` and exported
- Used throughout the codebase

### Updating the Version

To update the version, modify only `pydantic_jsonschema/_version.py`:

```python
__version__ = "0.2.0"
```

The change will automatically propagate to:

- Package metadata (via `pyproject.toml` dynamic versioning)
- Python API (`from pydantic_jsonschema import __version__`)
- Built distributions (wheel and sdist)

## Documentation Versioning

Documentation uses [mike](https://github.com/jimporter/mike) for version management, following the same pattern as Pydantic.

### Available Commands

```bash
# Deploy latest development version
just docs-deploy

# Deploy a specific version (e.g., 0.1.0, 1.0.0)
just docs-deploy-version 0.1.0

# Set the default version shown to users
just docs-set-default 0.1.0

# List all deployed versions
just docs-list

# Delete a version
just docs-delete 0.1.0
```

### Version Selector

Users can select different documentation versions via a dropdown in the top navigation bar (like Pydantic docs).

### Release Process

When releasing a new version:

1. **Update version in code:**

   ```bash
   # Edit pydantic_jsonschema/_version.py
   __version__ = "0.2.0"
   ```

2. **Update CHANGELOG.md:**

   ```bash
   # Add release notes for 0.2.0
   ```

3. **Commit and tag:**

   ```bash
   git add pydantic_jsonschema/_version.py CHANGELOG.md
   git commit -m "chore: bump version to 0.2.0"
   git tag v0.2.0
   git push origin master --tags
   ```

4. **Deploy documentation:**

   ```bash
   just docs-deploy-version 0.2.0
   just docs-set-default 0.2.0
   ```

5. **Create GitHub Release:**
   - Go to GitHub Releases
   - Create release from tag `v0.2.0`
   - GitHub Actions will automatically publish to PyPI

## Version Scheme

This project follows [Semantic Versioning](https://semver.org/):

- **MAJOR** (1.0.0): Breaking changes
- **MINOR** (0.1.0): New features, backwards compatible
- **PATCH** (0.0.1): Bug fixes, backwards compatible

### Pre-release Versions

For development versions:

- Alpha: `0.1.0a1`, `0.1.0a2`
- Beta: `0.1.0b1`, `0.1.0b2`
- Release Candidate: `0.1.0rc1`, `0.1.0rc2`

## Documentation Aliases

Mike supports aliases for documentation versions:

- `latest`: Latest stable release (e.g., 0.2.0)
- `dev`: Development version from master branch

Example deployment:

```bash
# Deploy 0.2.0 as latest
just docs-deploy-version 0.2.0
just docs-set-default latest

# Deploy development docs
just docs-deploy  # deploys as 'dev' and 'latest'
```

## Troubleshooting

### Version not updating

If the version doesn't update after changing `_version.py`:

```bash
# Rebuild the package
uv build --clean

# Or reinstall in development mode
uv pip install -e .
```

### Documentation version conflicts

If you see version conflicts in deployed docs:

```bash
# List all versions
just docs-list

# Delete problematic version
just docs-delete <version>

# Redeploy
just docs-deploy-version <version>
```
