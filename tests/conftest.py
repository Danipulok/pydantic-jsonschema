"""Shared test fixtures and type aliases."""

from typing import Any

from pydantic import ValidationError
from pydantic_core import ErrorDetails

type SchemaRaw = dict[str, Any]


def dump_errors(exc: ValidationError) -> list[ErrorDetails]:
    """Return a snapshot-friendly view of a `ValidationError`'s errors.

    `include_url=False` drops the version-pinned URL; `include_context=False` drops `ctx`
    (e.g. the non-roundtrippable `ValueError` from our own validators), leaving
    `type` / `loc` / `msg` / `input` — stable across Pydantic versions and safe for `snapshot()`.

    :param exc: The raised `ValidationError`.
    :returns: The error list with only the snapshot-stable fields.
    """
    return exc.errors(
        include_url=False,  # We don't care about URLs
        include_context=False,  # We always know context
    )
