"""Pytest fixtures for SiteCatalog contract tests.

Provided fixtures
-----------------
- **catalog**: Parametrized factory that returns a **fresh**
  `SiteCatalog` per test. Currently supports `"memory"` (the in-memory
  implementation). To exercise additional implementations later, add
  their keys to the `params` list and branch in the fixture body.

"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from calista.adapters.catalog.memory_store import InMemoryCatalogData
from calista.adapters.catalog.site_catalog.memory import InMemorySiteCatalog

if TYPE_CHECKING:
    from calista.interfaces.catalog.site_catalog import SiteCatalog


@pytest.fixture(params=["memory"])
def catalog(request: pytest.FixtureRequest) -> SiteCatalog:
    """Return a fresh site catalog instance for the requested backend.

    Current params:
      - `"memory"` → `InMemorySiteCatalog` (non-durable, in-memory)

    Extend by adding new identifiers to `params` and branching below to
    construct the corresponding implementation. Each invocation yields a brand-new
    catalog instance for isolation.
    """

    match request.param:
        case "memory":
            return InMemorySiteCatalog(data=InMemoryCatalogData())
        case _:
            raise ValueError(f"unknown catalog type: {request.param}")
