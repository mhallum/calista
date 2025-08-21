"""Pytest fixtures for CAS filestore contract tests.

Provided fixtures
-----------------
- **store**: Parametrized backend factory that returns a **fresh**
  `AbstractFileStore` per test. Currently supports `"memory"` (the in-memory
  implementation). To exercise additional backends later, add their keys to
  the `params` list and branch in the fixture body.

- **arbitrary_bytes**: Small, deterministic byte sample useful for smoke tests
  and quick round-trips. Tests that need larger payloads (or random data)
  should define their own fixture locally.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from calista.adapters.filestore.memory import MemoryFileStore

if TYPE_CHECKING:
    from calista.adapters.filestore.api import AbstractFileStore


@pytest.fixture(params=["memory"])
def store(request: pytest.FixtureRequest) -> AbstractFileStore:
    """Return a fresh filestore instance for the requested backend.

    Current params:
      - `"memory"` → `MemoryFileStore` (non-durable, in-memory CAS)

    Extend by adding new identifiers to `params` and branching below to
    construct the corresponding backend. Each invocation yields a brand-new
    store instance for isolation.
    """

    match request.param:
        case "memory":
            return MemoryFileStore()
        case _:
            raise ValueError(f"unknown store type: {request.param}")


@pytest.fixture
def arbitrary_bytes() -> bytes:
    """Deterministic sample payload for quick round-trip tests."""
    return b"The quick brown fox jumps over the lazy dog"
