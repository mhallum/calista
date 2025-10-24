"""Interface for the Site Catalog."""

from __future__ import annotations

import abc
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
    """Interface for managing the site catalog."""

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
