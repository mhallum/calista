"""In-memory implementation of the TelescopeCatalog interface."""

import datetime

from calista.adapters.catalog.memory_store import InMemoryCatalogData
from calista.interfaces.catalog.errors import (
    NoChangeError,
    VersionConflictError,
)
from calista.interfaces.catalog.telescope_catalog import (
    TelescopeCatalog,
    TelescopeRevision,
    TelescopeSnapshot,
)

# pylint: disable=consider-using-assignment-expr


class InMemoryTelescopeCatalog(TelescopeCatalog):
    """In-memory implementation of the TelescopeCatalog interface."""

    def __init__(self, data: InMemoryCatalogData):
        self._data = data

    def get(
        self, telescope_code: str, version: int | None = None
    ) -> TelescopeSnapshot | None:
        telescope_revs = self._data.telescopes.get(telescope_code, None)
        if telescope_revs is None:
            return None
        if version is None:
            return telescope_revs[-1]
        for telescope in telescope_revs:
            if telescope.version == version:
                return telescope
        return None

    def get_head_version(self, telescope_code: str) -> int | None:
        telescope_revs = self._data.telescopes.get(telescope_code, None)
        if telescope_revs is None or len(telescope_revs) == 0:
            return None
        return telescope_revs[-1].version

    def publish(self, revision: TelescopeRevision, expected_version: int) -> None:
        telescope_revs = self._data.telescopes.setdefault(revision.telescope_code, [])
        head_version = telescope_revs[-1].version if telescope_revs else 0

        if expected_version != head_version:
            raise VersionConflictError(
                "telescope",
                revision.telescope_code,
                head_version,
                expected_version,
            )

        if telescope_revs and revision == telescope_revs[-1]:
            raise NoChangeError("telescope", revision.telescope_code)

        telescope_revs.append(self._revision_to_snapshot(revision, head_version + 1))

    @staticmethod
    def _revision_to_snapshot(
        revision: TelescopeRevision, version: int
    ) -> TelescopeSnapshot:
        return TelescopeSnapshot(
            telescope_code=revision.telescope_code,
            version=version,
            recorded_at=datetime.datetime.now(datetime.timezone.utc),
            name=revision.name,
            aperture_m=revision.aperture_m,
            source=revision.source,
        )
