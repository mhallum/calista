"""Pytest fixtures for SiteCatalog contract tests.

Provided fixtures
-----------------
- **catalog**: Parametrized factory that returns a **fresh**
  `TelescopeCatalog` per test. Currently supports `"memory"` (the in-memory
  implementation). To exercise additional implementations later, add
  their keys to the `params` list and branch in the fixture body.
- **make_params**: Factory for telescope parameters with sensible defaults.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import pytest

from calista.adapters.catalog.memory_store import InMemoryCatalogData
from calista.adapters.catalog.telescope_catalog.memory import InMemoryTelescopeCatalog

if TYPE_CHECKING:
    from calista.interfaces.catalog.telescope_catalog import TelescopeCatalog


@pytest.fixture(params=["memory"])
def catalog(request: pytest.FixtureRequest) -> TelescopeCatalog:
    """Return a fresh telescope catalog instance for the requested backend.

    Current params:
      - `"memory"` → `InMemoryTelescopeCatalog` (non-durable, in-memory)

    Extend by adding new identifiers to `params` and branching below to
    construct the corresponding implementation. Each invocation yields a brand-new
    catalog instance for isolation.
    """

    match request.param:
        case "memory":
            return InMemoryTelescopeCatalog(data=InMemoryCatalogData())
        case _:
            raise ValueError(f"unknown catalog type: {request.param}")


@pytest.fixture
def make_params(make_telescope_params) -> Callable[..., dict[str, Any]]:
    """Factory for site parameters with sensible defaults.

    * See `make_telescope_params` fixture for details.

    defaults can be overridden by keyword arguments.
    """

    return make_telescope_params
