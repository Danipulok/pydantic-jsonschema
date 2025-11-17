"""Test that code examples in documentation work correctly."""

from collections.abc import Iterable
from pathlib import Path
from typing import Final, Literal

import pytest
from pytest_examples import CodeExample, EvalExample, find_examples

__all__ = []

QUOTES: Final[Literal["single", "double", "either"]] = "double"
LINE_LENGTH: Final[int] = 88


def get_example_files() -> list[Path]:
    """Find all Python example files.

    :returns: A list of Python example files.
    """
    examples_dir = Path(__file__).parent.parent.joinpath("examples")
    return sorted(path for path in examples_dir.glob("*.py") if path.name != "__init__.py")


def get_examples() -> Iterable[CodeExample]:
    """Find all Python code examples in documentation files.

    :returns: A list of Python code examples.
    """
    # Find examples in docs directory and README
    docs_dir = Path(__file__).parent.parent.joinpath("docs")
    readme = Path(__file__).parent.parent.joinpath("README.md")

    # Collect all markdown files, excluding `examples.md`
    # (uses --8<-- syntax for file inclusion)
    paths = [readme, *(path for path in docs_dir.glob("*.md") if path.name != "examples.md")]

    # Find examples in all paths
    return find_examples(*paths)


@pytest.mark.parametrize("example", get_examples(), ids=str)
def test_docs_examples(example: CodeExample, eval_example: EvalExample) -> None:
    """Test that all Python code examples in documentation are valid and run correctly.

    :param example: An example object.
    :param eval_example: Fixture for evaluating examples.
    """
    eval_example.set_config(
        line_length=LINE_LENGTH,
        ruff_ignore=[
            "T201",  # Allow print()
            "D",  # Skip all docstring checks
            "PLR2004",  # Allow magic values in comparisons
            "COM812",  # Allow missing trailing commas
        ],
        quotes=QUOTES,
    )

    # Check if we should update examples
    if eval_example.update_examples:
        # Format and update the example with print output
        eval_example.format_ruff(example)
        eval_example.run_print_update(example)
    else:
        # Lint the example with ruff
        eval_example.lint_ruff(example)
        # Run and check print output matches expected
        eval_example.run_print_check(example)


@pytest.mark.parametrize("example_file", get_example_files(), ids=lambda p: p.name)
def test_example_files(example_file: Path, eval_example: EvalExample) -> None:
    """Test that Python example files run correctly.

    :param example_file: Path to the example file.
    :param eval_example: Fixture for evaluating examples.
    """
    eval_example.set_config(
        line_length=LINE_LENGTH,
        ruff_ignore=[
            "T201",  # Allow print()
            "D",  # Skip all docstring checks
            "PLR2004",  # Allow magic values in comparisons
        ],
        quotes=QUOTES,
    )

    # Read the file content
    code = example_file.read_text(encoding="utf-8")

    # Create a CodeExample from the file
    example = CodeExample.create(
        source=code,
        path=example_file,
        start_line=1,
    )

    # Check if we should update examples
    if eval_example.update_examples:
        # Format and update the example with print output
        eval_example.format_ruff(example)
        eval_example.run_print_update(example)
    else:
        # Lint the example with ruff
        eval_example.lint_ruff(example)
        # Run and check print output matches expected
        eval_example.run_print_check(example)
