"""In-memory shared data store for catalog adapters."""

from dataclasses import dataclass
from typing import Any

from calista.interfaces.catalog.site_catalog import SiteSnapshot


@dataclass(slots=True)
class InMemoryCatalogData:
    """Shared in-memory backing store for in-memory catalog adapters.

    This class defines a simple data structure used by in-memory catalog
    adapters (e.g. ``InMemorySiteCatalog``, ``InMemoryTelescopeCatalog``)
    to emulate database-backed catalogs in tests. A single shared instance
    should be passed to all such adapters so they can operate on a common
    data source and resolve cross-catalog references consistently.

    Each mapping is keyed by its natural code
    (e.g. ``site_code``, ``instrument_code``) and stores a list of
    the corresponding snapshot objects for that catalog kind. The snapshots
    are stored in ascending version order (i.e. head is the last item in the list).
    """

    sites: dict[str, list[SiteSnapshot]]  # keyed by site_code
    telescopes: dict[str, list[Any]]  # keyed by telescope_code
    instruments: dict[str, list[Any]]  # keyed by instrument_code
    facilities: dict[str, list[Any]]  # keyed by facility_code
