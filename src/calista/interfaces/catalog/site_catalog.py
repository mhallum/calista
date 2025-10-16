"""Interface for the Site Catalog."""

from __future__ import annotations

import abc
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

# pylint: disable=too-many-instance-attributes


@dataclass(frozen=True, slots=True)
class SiteSnapshot:
    """Immutable read model for a site definition at a specific catalog version.

    Conventions:
      - `site_code` is canonical uppercase (e.g., "LDT").
      - `lat_deg` is in decimal degrees (float), None if unknown.
      - `lon_deg` is in decimal degrees (float), None if unknown.
      - `elevation_m` is in meters (float), None if unknown.
      - `mpc_code` is the MPC code (e.g., "G37"), None if unknown.
      - `source` is human-readable provenance (e.g., "LDT wiki", "MPC").
    """

    site_code: str  # canonical uppercase code, e.g. 'LDT'
    version: int  # 1..N; head is the max per site_code
    name: str
    source: str | None
    timezone: str
    lat_deg: float | None
    lon_deg: float | None
    elevation_m: float | None
    mpc_code: str | None
    recorded_at: datetime | None = (
        None  # UTC tz-aware; authoritative on return from store.
    )


class SiteCatalog(abc.ABC):
    """Interface for accessing site catalog entries."""

    @abc.abstractmethod
    def get(self, site_code: str, version: int | None = None) -> SiteSnapshot | None:
        """Get a site by its code.

        Args:
            site_code: The unique code of the site.
            version: The specific version of the site to retrieve. If None, retrieves the latest version.

        Returns:
            The site snapshot if found, otherwise None.

        Note:
            `site_code` lookup is case-insensitive; implementers should uppercase it.
        """

    def get_latest_version(self, site_code: str) -> int | None:
        """Get the latest version of a site by its code.

        Args:
            site_code: The unique code of the site.

        Returns:
            The latest version number if found, otherwise None.
        """

    @abc.abstractmethod
    def list(
        self,
        search: str | None = None,
        heads_only: bool = True,
        limit: int | None = 100,
        offset: int = 0,
    ) -> Iterable[SiteSnapshot]:
        """List site snapshots, optionally filtered by a case-insensitive search string
        matching the site code or name.

        Args:
            search: Optional case-insensitive substring to filter site codes or names.
            heads_only: If True, only return the latest version of each site.
            limit: Maximum number of results to return. If None, no limit is applied.
            offset: Number of results to skip before returning the remaining results.

        Returns:
            An iterable of site snapshots matching the criteria.

        Note:
            The results are ordered by `site_code` ascending, then `version` descending.
        """
