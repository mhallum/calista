"""In-memory SiteCatalog implementation for testing purposes."""

import datetime

from calista.adapters.catalog.memory_base import InMemoryVersionedCatalogBase
from calista.interfaces.catalog.site_catalog import (
    SiteCatalog,
    SiteRevision,
    SiteSnapshot,
)

# pylint: disable=consider-using-assignment-expr


class InMemorySiteCatalog(
    InMemoryVersionedCatalogBase[SiteSnapshot, SiteRevision], SiteCatalog
):
    """In-memory implementation of the SiteCatalog interface for testing purposes."""

    KIND = "site"
    CODE_ATTR = "site_code"
    BUCKET_ATTR = "sites"

    def _revision_to_snapshot(
        self, revision: SiteRevision, version: int
    ) -> SiteSnapshot:
        return SiteSnapshot(
            site_code=revision.site_code,
            version=version,
            name=revision.name,
            source=revision.source,
            timezone=revision.timezone,
            lat_deg=revision.lat_deg,
            lon_deg=revision.lon_deg,
            elevation_m=revision.elevation_m,
            mpc_code=revision.mpc_code,
            recorded_at=datetime.datetime.now(datetime.timezone.utc),
        )
