"""In-memory implementation of the TelescopeCatalog interface."""

import datetime

from calista.adapters.catalog.memory_store import InMemoryCatalogData
from calista.interfaces.catalog.errors import (
    NoChangeError,
    VersionConflictError,
)
from calista.interfaces.catalog.instrument_catalog import (
    InstrumentCatalog,
    InstrumentRevision,
    InstrumentSnapshot,
)

# pylint: disable=consider-using-assignment-expr


class InMemoryInstrumentCatalog(InstrumentCatalog):
    """In-memory implementation of the InstrumentCatalog interface."""

    def __init__(self, data: InMemoryCatalogData):
        self._data = data

    def get(
        self, instrument_code: str, version: int | None = None
    ) -> InstrumentSnapshot | None:
        instrument_revs = self._data.instruments.get(instrument_code, None)
        if instrument_revs is None:
            return None
        if version is None:
            return instrument_revs[-1]
        for instrument in instrument_revs:
            if instrument.version == version:
                return instrument
        return None

    def get_head_version(self, instrument_code: str) -> int | None:
        instrument_revs = self._data.instruments.get(instrument_code, None)
        if instrument_revs is None or len(instrument_revs) == 0:
            return None
        return instrument_revs[-1].version

    def publish(self, revision: InstrumentRevision, expected_version: int) -> None:
        instrument_revs = self._data.instruments.setdefault(
            revision.instrument_code, []
        )
        head_version = instrument_revs[-1].version if instrument_revs else 0

        if expected_version != head_version:
            raise VersionConflictError(
                "instrument",
                revision.instrument_code,
                head_version,
                expected_version,
            )

        if instrument_revs and revision == instrument_revs[-1]:
            raise NoChangeError("instrument", revision.instrument_code)

        instrument_revs.append(self._revision_to_snapshot(revision, head_version + 1))

    @staticmethod
    def _revision_to_snapshot(
        revision: InstrumentRevision, version: int
    ) -> InstrumentSnapshot:
        return InstrumentSnapshot(
            instrument_code=revision.instrument_code,
            version=version,
            recorded_at=datetime.datetime.now(datetime.timezone.utc),
            name=revision.name,
            source=revision.source,
            mode=revision.mode,
        )
