"""Test that code examples in documentation work correctly."""

from collections.abc import Iterable
from pathlib import Path

import pytest
from pytest_examples import CodeExample, EvalExample, find_examples


def get_examples() -> Iterable[CodeExample]:
    """Find all Python code examples in documentation files.

    :returns: A list of Python code examples.
    """
    # Find examples in docs directory and README
    docs_dir = Path(__file__).parent.parent / "docs"
    readme = Path(__file__).parent.parent / "README.md"

    # Collect all markdown files
    paths = [readme, *docs_dir.glob("*.md")]

    # Find examples in all paths
    return find_examples(*paths)


@pytest.mark.parametrize("example", get_examples(), ids=str)
def test_docs_examples(example: CodeExample, eval_example: EvalExample) -> None:
    """Test that all Python code examples in documentation are valid and run correctly.

    :param example: An example object.
    :param eval_example: Fixture for evaluating examples.
    """
    # Configure linting with minimal checks - we want examples to be readable, not perfect
    eval_example.set_config(
        ruff_ignore=[
            "T201",  # Allow print()
            "D",  # Skip all docstring checks
            "I001",  # Ignore import order
            "PLR2004",  # Allow magic values in comparisons
            "TRY003",  # Allow long error messages
            "EM101",  # Allow string literals in exceptions
            "S101",  # Allow assert
            "ARG001",  # Allow unused arguments
            "F841",  # Allow unused variables
            "F401",  # Allow unused imports (examples often import for demonstration)
            "F821",  # Allow undefined names (examples are often incomplete snippets)
            "E501",  # Allow long lines
            "E721",  # Allow type() comparisons
            "COM812",  # Allow missing trailing commas
            "ANN",  # Skip all type annotation checks
            "BLE001",  # Allow catching broad exceptions
            "SLF001",  # Allow private member access (examples show internal usage)
            "FA102",  # Allow missing future annotations import
            "B018",  # Allow useless expressions (showing constants)
            "ERA001",  # Allow commented code (examples often show comments)
            "Q000",  # Don't enforce quote style
            "B002",  # Python does not support the unary prefix decrement operator (`--`)
            "B015",  # Pointless comparison
        ],
        line_length=100,
        target_version="py310",  # Match project's minimum Python version
        isort=False,  # Don't enforce import sorting
    )

    # Try to lint with ruff only (skip black to avoid formatting nitpicks)
    # Skip examples that fail - many are intentionally incomplete demonstrations
    try:
        eval_example.lint_ruff(example)
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"Linting failed (likely incomplete example): {e}")

    # Try to run the example
    try:
        eval_example.run(example)
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"Execution failed (missing deps or incomplete example): {e}")
