"""Tests for converter utility functions."""

from typing import get_args

import pytest
from pydantic.experimental.missing_sentinel import MISSING

from pydantic_jsonschema.converters._utils import make_union, unwrap

__all__: list[str] = []


class TestUnwrap:
    """Tests for `unwrap`: a `Schema` field value, or a default when it is `MISSING`."""

    @pytest.mark.parametrize(
        ("value", "default", "expected"),
        [
            pytest.param(5, 0, 5, id="present-int"),
            pytest.param("x", "fallback", "x", id="present-str"),
            pytest.param(None, 1, None, id="present-none-is-not-missing"),
            pytest.param(MISSING, 42, 42, id="missing-falls-back"),
        ],
    )
    def test_unwrap(self, value: object, default: object, expected: object) -> None:
        """A present value is returned; the `MISSING` sentinel falls back to the default."""
        assert unwrap(value, default=default) == expected


class TestMakeUnion:
    """Tests for `make_union`: build a `Union` annotation from a dynamic list of members."""

    def test_multiple_members(self) -> None:
        """Multiple members build a union over exactly those members."""
        assert set(get_args(make_union([int, str, float]))) == {int, str, float}

    def test_single_member_collapses(self) -> None:
        """A union of one member collapses to that member."""
        assert make_union([int]) is int
