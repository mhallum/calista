"""Pytest fixtures for InstrumentCatalog contract tests.

Provided fixtures
-----------------
- **catalog**: Parametrized factory that returns a **fresh**
  `InstrumentCatalog` per test. Currently supports `"memory"` (the in-memory
  implementation). To exercise additional implementations later, add
  their keys to the `params` list and branch in the fixture body.
- **make_params**: Factory for instrument parameters with sensible defaults.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import pytest

from calista.adapters.catalog.instrument_catalog.memory import InMemoryInstrumentCatalog
from calista.adapters.catalog.memory_store import InMemoryCatalogData

if TYPE_CHECKING:
    from calista.interfaces.catalog.instrument_catalog import InstrumentCatalog


@pytest.fixture(params=["memory"])
def catalog(request: pytest.FixtureRequest) -> InstrumentCatalog:
    """Return a fresh instrument catalog instance for the requested backend.

    Current params:
      - `"memory"` → `InMemoryInstrumentCatalog` (non-durable, in-memory)

    Extend by adding new identifiers to `params` and branching below to
    construct the corresponding implementation. Each invocation yields a brand-new
    catalog instance for isolation.
    """

    match request.param:
        case "memory":
            return InMemoryInstrumentCatalog(data=InMemoryCatalogData())
        case _:
            raise ValueError(f"unknown catalog type: {request.param}")


@pytest.fixture
def make_params(make_instrument_params) -> Callable[..., dict[str, Any]]:
    """Factory for site parameters with sensible defaults.

    * See `make_instrument_params` fixture for details.

    defaults can be overridden by keyword arguments.
    """

    return make_instrument_params
