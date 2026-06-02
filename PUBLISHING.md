# Publishing Guide

This guide explains how to publish `pydantic-jsonschema` to PyPI.

## Prerequisites

Before publishing, ensure you have:

1. Completed and tested all changes
2. Updated version in `pyproject.toml` and `pydantic_jsonschema/__init__.py`
3. Updated `CHANGELOG.md` with the new version
4. All tests pass locally: `just test`
5. All linting checks pass: `just lint`

## Publishing to PyPI

### Option 1: Automatic Publishing (Recommended)

The package is configured to automatically publish to PyPI when you create a GitHub Release:

1. **Push all commits to GitHub:**

   ```bash
   git push origin main
   ```

2. **Create a new release on GitHub:**
   - Go to <https://github.com/Danipulok/pydantic-jsonschema/releases/new>
   - Create a new tag (e.g., `v0.1.0`)
   - Set the release title (e.g., `Release 0.1.0`)
   - Add release notes from `CHANGELOG.md`
   - Click "Publish release"

3. **GitHub Actions will automatically:**
   - Build the package
   - Publish to PyPI using trusted publishing (OIDC)

### Option 2: Manual Publishing

If you prefer to publish manually:

1. **Build the package:**

   ```bash
   uv build
   ```

2. **Check the build:**

   ```bash
   uv pip install --system twine
   twine check dist/*
   ```

3. **Upload to Test PyPI (optional):**

   ```bash
   twine upload --repository testpypi dist/*
   ```

4. **Upload to PyPI:**

   ```bash
   twine upload dist/*
   ```

   You'll need PyPI credentials for manual upload.

## Testing on TestPyPI

To test the package on TestPyPI before publishing to PyPI:

1. **Trigger the TestPyPI workflow:**
   - Go to <https://github.com/Danipulok/pydantic-jsonschema/actions>
   - Select "Publish to PyPI" workflow
   - Click "Run workflow"
   - This will publish to TestPyPI

2. **Install from TestPyPI:**

   ```bash
   uv pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ pydantic-jsonschema
   ```

## Pre-Release Checklist

- [ ] Version bumped in `pyproject.toml`
- [ ] Version bumped in `pydantic_jsonschema/__init__.py`
- [ ] `CHANGELOG.md` updated with new version
- [ ] All tests passing (`just test`)
- [ ] All linting passing (`just lint`)
- [ ] Documentation updated if needed
- [ ] Built package locally (`uv build`)
- [ ] Verified package contents
- [ ] All changes committed and pushed

## Post-Release Tasks

After publishing a new version:

1. Update the "Unreleased" section in `CHANGELOG.md`
2. Consider updating documentation
3. Announce the release (if applicable)

## Important Notes

### Git Dependencies

**Important:** The current `pyproject.toml` includes git dependencies in the `formats-extra` optional dependency group:

```toml
formats-extra = [
    "pydantic-extra-types[all] @ git+https://github.com/Danipulok/pydantic-extra-types.git@refactor/s3",
]
```

**Before publishing to PyPI**, you have two options:

1. **Wait for upstream packages to be published** to PyPI and update dependencies
2. **Remove the `formats-extra` group** temporarily if those features aren't ready

PyPI does not accept packages with direct git dependencies, even though we have `allow-direct-references = true` set for local development.

### Trusted Publishing Setup

The GitHub Actions workflow uses OpenID Connect (OIDC) for trusted publishing. To set this up:

1. Go to <https://pypi.org/manage/account/publishing/>
2. Add a new publisher:
   - PyPI Project Name: `pydantic-jsonschema`
   - Owner: `Danipulok`
   - Repository name: `pydantic-jsonschema`
   - Workflow name: `publish.yml`
   - Environment name: `pypi`

Do the same for TestPyPI at <https://test.pypi.org/manage/account/publishing/>

## Version Number Guidelines

This project follows [Semantic Versioning](https://semver.org/):

- **MAJOR** version for incompatible API changes
- **MINOR** version for backwards-compatible functionality additions
- **PATCH** version for backwards-compatible bug fixes

Example: `1.2.3` = MAJOR.MINOR.PATCH
