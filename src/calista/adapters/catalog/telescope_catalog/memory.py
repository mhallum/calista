"""In-memory implementation of the TelescopeCatalog interface."""

import datetime

from calista.adapters.catalog.memory_base import InMemoryVersionedCatalogBase
from calista.interfaces.catalog.telescope_catalog import (
    TelescopeCatalog,
    TelescopeRevision,
    TelescopeSnapshot,
)

# pylint: disable=consider-using-assignment-expr


class InMemoryTelescopeCatalog(
    InMemoryVersionedCatalogBase[TelescopeSnapshot, TelescopeRevision], TelescopeCatalog
):
    """In-memory implementation of the TelescopeCatalog interface."""

    BUCKET_ATTR = "telescopes"

    def _revision_to_snapshot(
        self, revision: TelescopeRevision, version: int
    ) -> TelescopeSnapshot:
        return TelescopeSnapshot(
            telescope_code=revision.telescope_code,
            version=version,
            recorded_at=datetime.datetime.now(datetime.timezone.utc),
            name=revision.name,
            aperture_m=revision.aperture_m,
            source=revision.source,
        )
