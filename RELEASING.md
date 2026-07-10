# Releasing

## First-time setup

These steps are required once before the first release.

### 1. Create GitHub environments

Go to **Settings → Environments** in the GitHub repository and create the environment:

- `pypi`

### 2. Configure PyPI trusted publisher (OIDC)

On [pypi.org](https://pypi.org):

1. Go to **Your projects → Manage → Publishing**
2. Add a new **pending publisher** (if the project doesn't exist on PyPI yet):
   - PyPI project name: `pydantic-jsonschema`
   - Owner: `Danipulok`
   - Repository: `pydantic-jsonschema`
   - Workflow name: `release.yml`
   - Environment name: `pypi`

## Pre-release checklist

Before the first public release:

1. Run `just all` — format, lint, tests, docs build must all pass.
2. Verify `docs/changelog.md` contains the target release section, for example `## [X.Y.Z]`.
3. Confirm PyPI trusted publisher is configured (see above).
4. Confirm GitHub environment `pypi` exists.

## Creating a release

The changelog lands on `main` through a regular PR; the tag is pushed as a separate ref, so
`main` is never pushed directly. Pass the version without the leading `v` in all commands.

1. Open the release PR:

   ```bash
   just release-pr X.Y.Z
   ```

   This creates branch `release/X.Y.Z` from up-to-date `main`, generates `docs/changelog.md`,
   commits it as `chore(version): update to X.Y.Z`, and opens the PR via `gh`.

2. Review and squash-merge the release PR (keep the PR title as the commit message).

3. Tag the merged commit:

   ```bash
   git switch main && git pull
   just release X.Y.Z
   ```

   This verifies you are on `main` matching `origin/main`, validates `docs/changelog.md`,
   creates tag `vX.Y.Z`, and pushes only the tag.

4. The `release.yml` workflow will automatically:
    - Build sdist and wheel (version derived from git tag via `hatch-vcs`).
    - Publish to PyPI.
    - Generate release notes via `git-cliff`.
    - Create a GitHub Release with the generated notes and distribution artifacts.
    - Deploy versioned documentation to GitHub Pages.

## Manual GitHub Release and docs deploy

The `release.yml` workflow creates the GitHub Release and deploys docs automatically.
If the workflow fails after PyPI publish (e.g. a broken action SHA), do it manually:

1. Generate release notes:

   ```bash
   uv run git-cliff vPREVIOUS..vX.Y.Z --strip all -o /tmp/release-notes.md
   ```

2. Create the GitHub Release:

   ```bash
   gh release create vX.Y.Z --title "vX.Y.Z" --notes-file /tmp/release-notes.md dist/*
   ```

3. Deploy documentation:

   ```bash
   just docs-deploy-version X.Y.Z
   just docs-alias X.Y.Z latest
   just docs-set-default latest
   ```

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

To redeploy documentation manually:

```bash
just docs-deploy-version X.Y.Z
just docs-set-default X.Y.Z
```
