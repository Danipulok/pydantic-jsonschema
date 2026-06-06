# Releasing

## First-time setup

These steps are required once before the first release.

### 1. Create GitHub environments

Go to **Settings → Environments** in the GitHub repository and create two environments:

- `pypi`
- `testpypi`

### 2. Configure PyPI trusted publisher (OIDC)

On [pypi.org](https://pypi.org):

1. Go to **Your projects → Manage → Publishing**
2. Add a new **pending publisher** (if the project doesn't exist on PyPI yet):
   - PyPI project name: `pydantic-jsonschema`
   - Owner: `Danipulok`
   - Repository: `pydantic-jsonschema`
   - Workflow name: `release.yml`
   - Environment name: `pypi`

### 3. Configure TestPyPI trusted publisher (OIDC)

On [test.pypi.org](https://test.pypi.org):

1. Go to **Your projects → Manage → Publishing**
2. Add a new **pending publisher**:
   - PyPI project name: `pydantic-jsonschema`
   - Owner: `Danipulok`
   - Repository: `pydantic-jsonschema`
   - Workflow name: `release.yml`
   - Environment name: `testpypi`

## Pre-release checklist

Before the first public release:

1. Run `just all` — format, lint, tests, docs build must all pass.
2. Verify `docs/changelog.md` contains the target release section, for example `## [X.Y.Z]`.
3. Confirm PyPI and TestPyPI trusted publishers are configured (see above).
4. Confirm GitHub environments `pypi` and `testpypi` exist.

## Creating a release

1. Run the release recipe:

   ```bash
   just release X.Y.Z
   ```

   Pass the version without the leading `v`. This validates `docs/changelog.md`, creates tag `vX.Y.Z`, and pushes `main` plus the tag.

2. The `release.yml` workflow will automatically:
   - Build sdist and wheel (version derived from git tag via `hatch-vcs`).
   - Publish to PyPI.
   - Publish to TestPyPI (for `v0.*` tags).
   - Generate release notes via `git-cliff`.
   - Create a GitHub Release with the generated notes and distribution artifacts.

## Versioning

Version is determined automatically from git tags by `hatch-vcs`. There is no hardcoded version in
`pyproject.toml`.

- Tagged commit `v1.2.3` → version `1.2.3`.
- Untagged commit after `v1.2.3` → version `1.2.4.dev1+gabcdef`.
- No tags at all → version `0.0.0.dev1+gabcdef`.

This project follows [Semantic Versioning](https://semver.org/):

- **MAJOR** (1.0.0): Breaking changes.
- **MINOR** (0.1.0): New features, backwards compatible.
- **PATCH** (0.0.1): Bug fixes, backwards compatible.

## Documentation versioning

Documentation uses [mike](https://github.com/jimporter/mike) for version management.

After creating a release:

```bash
just docs-deploy-version X.Y.Z
just docs-set-default X.Y.Z
```
