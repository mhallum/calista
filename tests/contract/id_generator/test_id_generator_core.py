"""Contract tests for IdGenerator implementations."""

from __future__ import annotations

import concurrent.futures as cf
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from calista.interfaces.id_generator import IdGenerator


def test_returns_str_and_not_empty(id_generator: IdGenerator) -> None:
    """new_id() returns a non-empty string."""
    new_id = id_generator.new_id()
    assert isinstance(new_id, str)
    assert new_id != ""


def test_returns_unique_ids(id_generator: IdGenerator) -> None:
    """new_id() returns unique IDs."""
    ids = {id_generator.new_id() for _ in range(5000)}
    assert len(ids) == len(set(ids))  # all IDs are unique


def test_threaded_uniqueness_single_instance(id_generator: IdGenerator) -> None:
    """new_id() returns unique IDs when called from multiple threads."""

    def _next(_: int) -> str:
        return id_generator.new_id()

    n = 8000
    with cf.ThreadPoolExecutor(max_workers=16) as ex:
        ids = list(ex.map(_next, range(n)))

    assert len(ids) == len(set(ids))
