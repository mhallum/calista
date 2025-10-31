"""Pytest fixtures for SiteCatalog contract tests.

Provided fixtures
-----------------
- **catalog**: Parametrized factory that returns a **fresh**
  `SiteCatalog` per test. Currently supports `"memory"` (the in-memory
  implementation). To exercise additional implementations later, add
  their keys to the `params` list and branch in the fixture body.

"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

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


@pytest.fixture
def make_params(make_site_params) -> Callable[..., dict[str, Any]]:
    """Factory for site parameters with sensible defaults.

    Args (defaults):
        - source: str | None = "Some Test Source"
        - timezone: str | None = "America/New_York"
        - lat_deg: float | None = 90.0
        - lon_deg: float | None = 30.0
        - elevation_m: float | None = 100.0
        - mpc_code: str | None = "XXX"

    defaults can be overridden by keyword arguments.
    """

    return make_site_params
