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
        site_snapshots = self._data.sites.get(site_code.upper())
        if site_snapshots is None:
            return None
        if version is None:
            return site_snapshots[-1]
        for site in site_snapshots:
            if site.version == version:
                return site
        return None

    def get_head_version(self, site_code: str) -> int | None:
        site_snapshots = self._data.sites.get(site_code.upper())
        if site_snapshots is None or len(site_snapshots) == 0:
            return None
        return site_snapshots[-1].version

    def publish(self, revision: SiteRevision, expected_version: int) -> None:
        site_snapshots = self._data.sites.setdefault(revision.site_code, [])
        head_version = site_snapshots[-1].version if site_snapshots else 0

        if expected_version != head_version:
            raise VersionConflictError(
                "site",
                revision.site_code,
                head_version,
                expected_version,
            )

        if site_snapshots and not revision.get_diff(site_snapshots[-1]):
            raise NoChangeError("site", revision.site_code)

        site_snapshots.append(self._revision_to_snapshot(revision, head_version + 1))

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
