"""Tests for converter `Annotated` metadata helpers."""

from typing import Annotated, get_args, get_origin

import annotated_types
import pytest
from pydantic import AfterValidator

from pydantic_jsonschema.converters._metadata import (
    _ensure_unique_items,
    annotate,
    array_metadata,
    object_dict_metadata,
)
from pydantic_jsonschema.schema import Schema

__all__: list[str] = []


class TestAnnotate:
    """Tests for `annotate`: wrap an annotation with `Annotated` metadata."""

    def test_no_metadata_returns_annotation_unchanged(self) -> None:
        """With no metadata the base annotation is returned as-is."""
        base = list[int]
        assert annotate(base, metadata=[]) is base

    def test_metadata_wraps_in_annotated(self) -> None:
        """With metadata the base becomes `Annotated[base, *metadata]`."""
        marker = annotated_types.MinLen(1)
        result = annotate(list[int], metadata=[marker])

        assert get_origin(result) is Annotated
        assert get_args(result) == (list[int], marker)


class TestArrayMetadata:
    """Tests for `array_metadata`: `Annotated` metadata for array constraint keywords."""

    def test_unique_items_true_adds_validator(self) -> None:
        """`uniqueItems: true` contributes an `AfterValidator`."""
        metadata = array_metadata(Schema.model_validate({"type": "array", "uniqueItems": True}))

        assert len(metadata) == 1
        assert isinstance(metadata[0], AfterValidator)

    @pytest.mark.parametrize(
        "schema_raw",
        [
            pytest.param({"type": "array"}, id="absent"),
            pytest.param({"type": "array", "uniqueItems": False}, id="false"),
        ],
    )
    def test_no_unique_items_no_metadata(self, schema_raw: dict[str, object]) -> None:
        """Absent or `false` `uniqueItems` imposes no constraint."""
        assert array_metadata(Schema.model_validate(schema_raw)) == []


class TestObjectDictMetadata:
    """Tests for `object_dict_metadata`: length metadata for `min` / `maxProperties`."""

    def test_bounds_produce_len_metadata(self) -> None:
        """`minProperties` / `maxProperties` map to `MinLen` / `MaxLen`."""
        metadata = object_dict_metadata(
            Schema.model_validate({"type": "object", "minProperties": 1, "maxProperties": 3})
        )

        assert metadata == [annotated_types.MinLen(1), annotated_types.MaxLen(3)]

    def test_no_bounds_no_metadata(self) -> None:
        """Without property bounds there is no metadata."""
        assert object_dict_metadata(Schema.model_validate({"type": "object"})) == []


class TestEnsureUniqueItems:
    """Tests for `_ensure_unique_items`: O(n^2) `uniqueItems` enforcement."""

    def test_unique_returned_unchanged(self) -> None:
        """A list with distinct items (including unhashable ones) is returned unchanged."""
        items = [1, 2, {"a": 1}, [3]]
        assert _ensure_unique_items(items) is items

    @pytest.mark.parametrize(
        "items",
        [
            pytest.param([1, 1], id="scalars"),
            pytest.param([{"a": 1}, {"a": 1}], id="unhashable-dicts"),
            # NOTE: Python equates `True == 1`, so this is treated as a duplicate.
            pytest.param([True, 1], id="bool-int-edge"),
        ],
    )
    def test_duplicates_rejected(self, items: list[object]) -> None:
        """Equal items (including the `True == 1` edge) raise `ValueError`."""
        with pytest.raises(ValueError, match="Array items must be unique"):
            _ensure_unique_items(items)
