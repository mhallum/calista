"""Pytest fixtures for FacilityCatalog contract tests.

Provided fixtures
-----------------
- **catalog**: Parametrized factory that returns a **fresh**
  `FacilityCatalog` per test. The catalog backend is seeded with a test site,
  telescope, and instrument. Currently supports `"memory"` (the in-memory
  implementation). To exercise additional implementations later, add
  their keys to the `params` list and branch in the fixture body.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from calista.adapters.catalog.facility_catalog.memory import InMemoryFacilityCatalog
from calista.adapters.catalog.instrument_catalog.memory import InMemoryInstrumentCatalog
from calista.adapters.catalog.memory_store import InMemoryCatalogData
from calista.adapters.catalog.site_catalog.memory import InMemorySiteCatalog
from calista.adapters.catalog.telescope_catalog.memory import InMemoryTelescopeCatalog

if TYPE_CHECKING:
    from calista.interfaces.catalog.facility_catalog import FacilityCatalog


@pytest.fixture(params=["memory"])
def catalog(
    request: pytest.FixtureRequest,
    make_site_params,
    make_telescope_params,
    make_instrument_params,
) -> FacilityCatalog:
    """Return a fresh facility catalog instance for the requested backend.

    Each catalog is pre-seeded with a test site, telescope, and instrument so that
    facilities referencing them can be registered.

    Current params:
      - `"memory"` → `InMemoryFacilityCatalog` (non-durable, in-memory)

    Extend by adding new identifiers to `params` and branching below to
    construct the corresponding implementation. Each invocation yields a brand-new
    catalog instance for isolation.
    """

    match request.param:
        case "memory":
            data = InMemoryCatalogData()

            # seed site
            site_catalog = InMemorySiteCatalog(data=data)
            site_catalog.publish(
                site_catalog.REVISION_CLASS(**make_site_params("SITE", "Test Site")),
                expected_version=0,
            )

            # seed telescope
            telescope_catalog = InMemoryTelescopeCatalog(data=data)
            telescope_catalog.publish(
                telescope_catalog.REVISION_CLASS(
                    **make_telescope_params("TEL", "Test Telescope")
                ),
                expected_version=0,
            )

            # seed instrument
            instrument_catalog = InMemoryInstrumentCatalog(data=data)
            instrument_catalog.publish(
                instrument_catalog.REVISION_CLASS(
                    **make_instrument_params("INST", "Test Instrument")
                ),
                expected_version=0,
            )

            return InMemoryFacilityCatalog(data=data)
        case _:
            raise ValueError(f"unknown catalog type: {request.param}")
