"""Interface for the Site Catalog."""

from __future__ import annotations

import abc
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, ClassVar, TypeAlias

from .base import VersionedCatalog
from .errors import InvalidRevisionError, InvalidSnapshotError
from .unsettable import UNSET, Unsettable, resolve

# pylint: disable=too-many-instance-attributes

# --- Read Model ---


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
      - `recorded_at` is a UTC tz-aware datetime when this snapshot was recorded.
    """

    site_code: str  # canonical uppercase code, e.g. 'LDT'
    version: int  # 1..N; head is the max per site_code
    name: str
    recorded_at: datetime
    source: str | None = None
    timezone: str | None = None
    lat_deg: float | None = None
    lon_deg: float | None = None
    elevation_m: float | None = None
    mpc_code: str | None = None
    comment: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "site_code", self.site_code.upper())

        if self.lat_deg is not None and not -90.0 <= self.lat_deg <= 90.0:
            raise InvalidSnapshotError(
                "site", self.site_code, "lat_deg must be between -90 and 90 degrees"
            )
        if self.lon_deg is not None and not -180.0 <= self.lon_deg <= 180.0:
            raise InvalidSnapshotError(
                "site", self.site_code, "lon_deg must be between -180 and 180 degrees"
            )
        if self.mpc_code is not None:
            if not self.mpc_code.isalnum() or len(self.mpc_code) != 3:  # pylint: disable=magic-value-comparison
                raise InvalidSnapshotError(
                    "site",
                    self.site_code,
                    "mpc_code must be a 3-character alphanumeric string if set",
                )
        if self.recorded_at.tzinfo is None or self.recorded_at.utcoffset() != timedelta(
            0
        ):
            raise InvalidSnapshotError(
                "site", self.site_code, "recorded_at must be timezone-aware UTC"
            )


# --- Write Models ---

Diff: TypeAlias = dict[str, tuple[Any | None, Any | None]]


@dataclass(frozen=True, slots=True)
class SiteRevision:
    """Immutable write model for a site revision to be published."""

    site_code: str  # canonical uppercase code, e.g. 'LDT'
    name: str
    source: str | None = None
    timezone: str | None = None
    lat_deg: float | None = None
    lon_deg: float | None = None
    elevation_m: float | None = None
    mpc_code: str | None = None
    comment: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "site_code", self.site_code.upper())

        if self.lat_deg is not None and not -90.0 <= self.lat_deg <= 90.0:
            raise InvalidRevisionError(
                "site", self.site_code, "lat_deg must be between -90 and 90 degrees"
            )
        if self.lon_deg is not None and not -180.0 <= self.lon_deg <= 180.0:
            raise InvalidRevisionError(
                "site", self.site_code, "lon_deg must be between -180 and 180 degrees"
            )
        if self.mpc_code is not None:
            if not self.mpc_code.isalnum() or len(self.mpc_code) != 3:  # pylint: disable=magic-value-comparison
                raise InvalidRevisionError(
                    "site",
                    self.site_code,
                    "mpc_code must be a 3-character alphanumeric string if set",
                )

    def get_diff(self, head: SiteSnapshot) -> Diff | None:
        """Return changed fields as {name: (old, new)}, or None if no changes."""
        if head.site_code != self.site_code:
            raise InvalidRevisionError(
                "site",
                self.site_code,
                f"site_code mismatch with head ({head.site_code})",
            )
        diffs: dict[str, tuple[object | None, object | None]] = {}
        for field in (
            "name",
            "source",
            "timezone",
            "lat_deg",
            "lon_deg",
            "elevation_m",
            "mpc_code",
            "comment",
        ):
            old_value = getattr(head, field)
            new_value = getattr(self, field)
            if old_value != new_value:
                diffs[field] = (old_value, new_value)
        return diffs if diffs else None


@dataclass(frozen=True, slots=True)
class SitePatch:
    """Immutable write model for a site patch to be applied to an existing site head."""

    name: Unsettable[str] = UNSET
    source: Unsettable[str] = UNSET
    timezone: Unsettable[str] = UNSET
    lat_deg: Unsettable[float] = UNSET
    lon_deg: Unsettable[float] = UNSET
    elevation_m: Unsettable[float] = UNSET
    mpc_code: Unsettable[str] = UNSET
    comment: str | None = None

    def apply_to(self, head: SiteSnapshot) -> SiteRevision:
        """Apply the patch to the given site head and return a new SiteRevision."""

        def _resolve(field, clearable=True):
            value = getattr(self, field)
            current = getattr(head, field)
            return resolve(
                value,
                current,
                clearable=clearable,
                field=field,
                kind="site",
                key=head.site_code,
            )

        return SiteRevision(
            site_code=head.site_code,
            name=_resolve("name", clearable=False),
            source=_resolve("source"),
            timezone=_resolve("timezone"),
            lat_deg=_resolve("lat_deg"),
            lon_deg=_resolve("lon_deg"),
            elevation_m=_resolve("elevation_m"),
            mpc_code=_resolve("mpc_code"),
            comment=self.comment,
        )


# --- Interface ---


class SiteCatalog(VersionedCatalog[SiteSnapshot, SiteRevision], abc.ABC):
    """Interface for managing the site catalog."""

    KIND: ClassVar[str] = "site"
    CODE_ATTR: ClassVar[str] = "site_code"
    REVISION_CLASS: ClassVar[type[SiteRevision]] = SiteRevision
    SNAPSHOT_CLASS: ClassVar[type[SiteSnapshot]] = SiteSnapshot
