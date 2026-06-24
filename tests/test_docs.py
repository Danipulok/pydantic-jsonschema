"""Test that code examples in documentation work correctly."""

import tomllib
from pathlib import Path
from typing import Any, Final

import pytest
from pytest_examples import CodeExample, EvalExample, find_examples

__all__ = []

# `pytest-examples` has no native `pyproject.toml` support, so source its settings here instead of
# hardcoding them: `line-length` / `target-version` / `quote-style` track `[tool.ruff]`, and the
# doc/example-only `ruff` ignores live in `[tool.pytest-examples]`. A `None` (key absent) means
# "leave the `pytest-examples` default" — the value is simply not forwarded to `set_config`.
_PYPROJECT_TOML_DATA: Final[dict[str, Any]] = tomllib.loads(
    (Path(__file__).parent.parent / "pyproject.toml").read_text(encoding="utf-8"),
)
_TOOL_DATA: Final[dict[str, Any]] = _PYPROJECT_TOML_DATA["tool"]
_RUFF_DATA: Final[dict[str, Any]] = _TOOL_DATA["ruff"]

LINE_LENGTH: Final[int | None] = _RUFF_DATA.get("line-length")
TARGET_VERSION: Final[str | None] = _RUFF_DATA.get("target-version")
QUOTES: Final[str | None] = _RUFF_DATA.get("format", {}).get("quote-style")
RUFF_IGNORE: Final[list[str]] = _TOOL_DATA.get("pytest-examples", {}).get("ruff-ignore", [])


def _configure(eval_example: EvalExample, /) -> None:
    """Apply the example-linting config sourced from `pyproject.toml`.

    :param eval_example: Fixture for evaluating examples.
    """
    config: dict[str, Any] = {"ruff_ignore": RUFF_IGNORE}
    if LINE_LENGTH is not None:
        config["line_length"] = LINE_LENGTH
    if TARGET_VERSION is not None:
        config["target_version"] = TARGET_VERSION
    if QUOTES is not None:
        config["quotes"] = QUOTES
    eval_example.set_config(**config)


def get_example_files() -> list[Path]:
    """Find all Python example files.

    :returns: A list of Python example files.
    """
    examples_dir = Path(__file__).parent.parent.joinpath("examples")
    return sorted(path for path in examples_dir.glob("*.py") if path.name != "__init__.py")


def get_examples() -> list[CodeExample]:
    """Find all Python code examples in documentation files.

    :returns: A list of Python code examples.
    """
    docs_dir = Path(__file__).parent.parent.joinpath("docs")
    readme = Path(__file__).parent.parent.joinpath("README.md")

    # NOTE: `examples.md` uses `--8<--` file inclusion, so its code blocks are not standalone.
    paths = [readme, *(path for path in docs_dir.glob("*.md") if path.name != "examples.md")]

    # NOTE: `list(...)` is required — `find_examples` returns a generator, and `parametrize`
    # deprecated non-`Collection` iterables (`PytestRemovedIn10Warning`, surfaced by the ceiling
    # test on a newer pytest). Reproduce:
    #   uv run --upgrade pytest -W error -q   # -> error during collection of `tests/test_docs.py`
    return list(find_examples(*paths))


@pytest.mark.parametrize("example", get_examples(), ids=str)
def test_docs_examples(example: CodeExample, eval_example: EvalExample) -> None:
    """Test that all Python code examples in documentation are valid and run correctly.

    :param example: An example object.
    :param eval_example: Fixture for evaluating examples.
    """
    _configure(eval_example)

    if eval_example.update_examples:
        eval_example.format_ruff(example)
        eval_example.run_print_update(example)
    else:
        eval_example.lint_ruff(example)
        eval_example.run_print_check(example)


@pytest.mark.parametrize("example_file", get_example_files(), ids=lambda p: p.name)
def test_example_files(example_file: Path, eval_example: EvalExample) -> None:
    """Test that Python example files run correctly.

    :param example_file: Path to the example file.
    :param eval_example: Fixture for evaluating examples.
    """
    _configure(eval_example)

    code = example_file.read_text(encoding="utf-8")
    example = CodeExample.create(
        source=code,
        path=example_file,
        start_line=1,
    )

    if eval_example.update_examples:
        eval_example.format_ruff(example)
        eval_example.run_print_update(example)
    else:
        eval_example.lint_ruff(example)
        eval_example.run_print_check(example)
