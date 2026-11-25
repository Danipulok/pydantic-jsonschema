"""Test that `cliff.toml` renders the changelog the release flow commits."""

import shutil
import subprocess
import sysconfig
from collections.abc import Sequence
from pathlib import Path
from typing import Final

import pytest
from inline_snapshot import snapshot

__all__: list[str] = []

_CLIFF_CONFIG: Final[Path] = Path(__file__).parent.parent / "cliff.toml"
_EM_DASH: Final[str] = "\u2014"
_EN_DASH: Final[str] = "\u2013"
_COMMIT_DATE: Final[str] = "2026-01-01T00:00:00+00:00"


def _executable(
    name: str,
    *,
    search_path: str | None = None,
) -> str:
    """Return the absolute path of `name`, failing the test when it is not installed.

    :param name: The executable to look up.
    :param search_path: The directories to search, `PATH` when `None`.
    :returns: The absolute path.
    """
    executable = shutil.which(name, path=search_path)

    if executable is None:
        pytest.fail(f"`{name}` is not installed")

    return executable


def _run(
    command: Sequence[str],
    *,
    repository: Path,
) -> str:
    """Run `command` inside `repository` and return its standard output.

    :param command: The executable and its arguments.
    :param repository: The working directory.
    :returns: The standard output.
    """
    # Every command is built in this module from `shutil.which` paths and literals.
    completed = subprocess.run(  # noqa: S603
        command,
        cwd=repository,
        capture_output=True,
        check=False,
        encoding="utf-8",
    )

    if completed.returncode != 0:
        pytest.fail(f"`{' '.join(command)}` exited {completed.returncode}: {completed.stderr}")

    return completed.stdout


@pytest.fixture
def repository(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    """Build a repository holding two tagged releases, two dash subjects and a merge commit.

    :param tmp_path: The directory the repository is created in.
    :param monkeypatch: Sets the `git` identity and dates for the subprocesses.
    :returns: The repository root.
    """
    empty_config: Path = tmp_path / "gitconfig"
    empty_config.write_text("", encoding="utf-8")

    # A global config may sign commits or set another default branch.
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(empty_config))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")

    # Under a pre-commit hook, `git commit` exports the outer index, its `-c` options and, in a
    #  worktree, `GIT_DIR`, so the inner `git commit` fails with `Error building trees`.
    #  https://github.com/git/git/blob/67ad42147a7acc2af6074753ebd03d904476118f/commit.c#L1968
    for variable in ("GIT_DIR", "GIT_INDEX_FILE", "GIT_CONFIG_PARAMETERS"):
        monkeypatch.delenv(variable, raising=False)

    for role in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{role}_NAME", "Test")
        monkeypatch.setenv(f"GIT_{role}_EMAIL", "test@example.com")
        monkeypatch.setenv(f"GIT_{role}_DATE", _COMMIT_DATE)

    root: Path = tmp_path / "repository"
    root.mkdir()

    git = _executable("git")
    commit: list[str] = [git, "commit", "--quiet", "--allow-empty", "--message"]

    _run([git, "init", "--quiet", "--initial-branch=main"], repository=root)

    _run([*commit, "feat(core): add the converter"], repository=root)
    _run([*commit, "feat(core): add the alias map"], repository=root)
    _run([git, "tag", "v0.1.0"], repository=root)

    _run([*commit, f"fix(core): keep the field order {_EM_DASH} aliases included"], repository=root)
    _run([git, "tag", "v0.2.0"], repository=root)

    _run([git, "switch", "--quiet", "--create", "topic"], repository=root)
    _run([*commit, f"docs(readme): name the supported range 3.12 {_EN_DASH} 3.15"], repository=root)
    _run([git, "switch", "--quiet", "main"], repository=root)
    _run(
        [
            git,
            "merge",
            "--quiet",
            "--no-ff",
            "topic",
            "--message",
            "docs(readme): name the supported range (#7)",
        ],
        repository=root,
    )

    return root


def test_changelog_render(repository: Path) -> None:
    git_cliff = _executable("git-cliff", search_path=sysconfig.get_path("scripts"))

    changelog = _run([git_cliff, "--config", str(_CLIFF_CONFIG)], repository=repository)

    assert changelog == snapshot("""\
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Documentation

- name the supported range 3.12: 3.15

## [0.2.0] - 2026-01-01

### Fixed

- keep the field order: aliases included

## [0.1.0] - 2026-01-01

### Added

- add the alias map
- add the converter

[Unreleased]: <https://github.com/Danipulok/pydantic-jsonschema/compare/v0.2.0...HEAD>
[0.2.0]: <https://github.com/Danipulok/pydantic-jsonschema/compare/v0.1.0...v0.2.0>
[0.1.0]: <https://github.com/Danipulok/pydantic-jsonschema/releases/tag/v0.1.0>

""")
