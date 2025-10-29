"""In-memory SiteCatalog implementation for testing purposes."""

import datetime

from calista.adapters.catalog.memory_store import InMemoryCatalogData
from calista.interfaces.catalog.errors import NoChangeError, VersionConflictError
from calista.interfaces.catalog.site_catalog import (
    SiteCatalog,
    SiteRevision,
    SiteSnapshot,
)

# pylint: disable=consider-using-assignment-expr


class InMemorySiteCatalog(SiteCatalog):
    """In-memory implementation of the SiteCatalog interface for testing purposes."""

    def __init__(self, data: InMemoryCatalogData) -> None:
        self._data = data

    def get(self, site_code: str, version: int | None = None) -> SiteSnapshot | None:
        site_revs = self._data.sites.get(site_code, None)
        if site_revs is None:
            return None
        if version is None:
            return site_revs[-1]
        for site in site_revs:
            if site.version == version:
                return site
        return None

    def get_head_version(self, site_code: str) -> int | None:
        site_revs = self._data.sites.get(site_code, None)
        if site_revs is None or len(site_revs) == 0:
            return None
        return site_revs[-1].version

    def publish(self, revision: SiteRevision, expected_version: int) -> None:
        site_revs = self._data.sites.setdefault(revision.site_code, [])
        head_version = site_revs[-1].version if site_revs else 0

        if expected_version != head_version:
            raise VersionConflictError(
                "site",
                revision.site_code,
                head_version,
                expected_version,
            )

        if site_revs and revision == site_revs[-1]:
            raise NoChangeError("site", revision.site_code)

        site_revs.append(self._revision_to_snapshot(revision, head_version + 1))

    @staticmethod
    def _revision_to_snapshot(revision: SiteRevision, version: int) -> SiteSnapshot:
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
