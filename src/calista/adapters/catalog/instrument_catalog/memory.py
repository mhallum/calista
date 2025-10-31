"""In-memory implementation of the TelescopeCatalog interface."""

import datetime

from calista.adapters.catalog.memory_base import InMemoryVersionedCatalogBase
from calista.interfaces.catalog.instrument_catalog import (
    InstrumentCatalog,
    InstrumentRevision,
    InstrumentSnapshot,
)

# pylint: disable=consider-using-assignment-expr


class InMemoryInstrumentCatalog(
    InMemoryVersionedCatalogBase[InstrumentSnapshot, InstrumentRevision],
    InstrumentCatalog,
):
    """In-memory implementation of the InstrumentCatalog interface."""

    BUCKET_ATTR = "instruments"

    def _revision_to_snapshot(
        self, revision: InstrumentRevision, version: int
    ) -> InstrumentSnapshot:
        return InstrumentSnapshot(
            instrument_code=revision.instrument_code,
            version=version,
            recorded_at=datetime.datetime.now(datetime.timezone.utc),
            name=revision.name,
            source=revision.source,
            mode=revision.mode,
        )
