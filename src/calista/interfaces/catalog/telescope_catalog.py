"""Interface for the Telescope Catalog."""

from __future__ import annotations

import abc
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, TypeAlias

from .errors import InvalidRevisionError, InvalidSnapshotError
from .unsettable import UNSET, Unsettable, resolve

# pylint: disable=too-many-instance-attributes

# --- Read Model ---


@dataclass(frozen=True, slots=True)
class TelescopeSnapshot:
    """Immutable read model for a telescope definition at a specific catalog version.

    Conventions:
      - `telescope_code` is canonical uppercase (e.g., "LDT-4.3M" or "LDT").
      - `site_code` is the site this telescope belongs to at this version (uppercase).
      - `aperture_m` is in meters (float), None if unknown.
      - `source` is human-readable provenance (e.g., "LDT wiki", "ops email").
      - `recorded_at` is a UTC tz-aware datetime when this snapshot was recorded.
    """

    telescope_code: str  # canonical uppercase code, e.g. 'LDT'
    version: int  # 1..N; head is the max per site_code
    recorded_at: datetime
    name: str
    site_code: str
    source: str | None = None
    aperture_m: float | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "telescope_code", self.telescope_code.upper())
        object.__setattr__(self, "site_code", self.site_code.upper())

        if self.aperture_m is not None and self.aperture_m <= 0:
            raise InvalidSnapshotError(
                "telescope", self.telescope_code, "aperture_m must be positive"
            )
        if self.recorded_at.tzinfo is None or self.recorded_at.utcoffset() != timedelta(
            0
        ):
            raise InvalidSnapshotError(
                "telescope",
                self.telescope_code,
                "recorded_at must be timezone-aware UTC",
            )


# --- Write Models ---

Diff: TypeAlias = dict[str, tuple[Any | None, Any | None]]


@dataclass(frozen=True, slots=True)
class TelescopeRevision:
    """Immutable write model for a telescope revision to be published."""

    telescope_code: str  # canonical uppercase code, e.g. 'LDT'
    name: str
    site_code: str
    source: str | None = None
    aperture_m: float | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "site_code", self.site_code.upper())
        object.__setattr__(self, "telescope_code", self.telescope_code.upper())

        if self.aperture_m is not None and self.aperture_m <= 0:
            raise InvalidRevisionError(
                "telescope", self.telescope_code, "aperture_m must be positive"
            )

    def get_diff(self, head: TelescopeSnapshot) -> Diff | None:
        """Return changed fields as {name: (old, new)}, or None if no changes."""
        if head.telescope_code != self.telescope_code:
            raise InvalidRevisionError(
                "telescope",
                self.telescope_code,
                f"telescope_code mismatch with head ({head.telescope_code})",
            )
        diffs: dict[str, tuple[object | None, object | None]] = {}
        for field in (
            "name",
            "site_code",
            "source",
            "aperture_m",
        ):
            old_value = getattr(head, field)
            new_value = getattr(self, field)
            if old_value != new_value:
                diffs[field] = (old_value, new_value)
        return diffs if diffs else None


@dataclass(frozen=True, slots=True)
class TelescopePatch:
    """Immutable write model for a telescope patch to be applied to an existing telescope head."""

    name: Unsettable[str] = UNSET
    site_code: Unsettable[str] = UNSET
    source: Unsettable[str] = UNSET
    aperture_m: Unsettable[float] = UNSET

    def apply_to(self, head: TelescopeSnapshot) -> TelescopeRevision:
        """Apply the patch to the given telescope head and return a new TelescopeRevision."""

        def _resolve(field, clearable=True):
            value = getattr(self, field)
            current = getattr(head, field)
            return resolve(
                value,
                current,
                clearable=clearable,
                field=field,
                kind="telescope",
                key=head.telescope_code,
            )

        return TelescopeRevision(
            telescope_code=head.telescope_code,
            site_code=_resolve("site_code", clearable=False),
            name=_resolve("name", clearable=False),
            source=_resolve("source"),
            aperture_m=_resolve("aperture_m"),
        )


# --- Interface ---


class TelescopeCatalog(abc.ABC):
    """Interface for managing the telescope catalog."""

    @abc.abstractmethod
    def get(
        self, telescope_code: str, version: int | None = None
    ) -> TelescopeSnapshot | None:
        """Get a telescope by its code.

        Args:
            telescope_code: The unique code of the telescope.
            version: The specific version of the telescope to retrieve.
                If None, retrieves the latest version.

        Returns:
            The telescope snapshot if found, otherwise None.

        Note:
            `telescope_code` lookup is case-insensitive; implementers should uppercase it.
        """

    @abc.abstractmethod
    def get_head_version(self, telescope_code: str) -> int | None:
        """Get the head version of a telescope by its code.

        Args:
            telescope_code: The unique code of the telescope.

        Returns:
            The latest version number if found, otherwise None.
        """

    @abc.abstractmethod
    def publish(
        self,
        revision: TelescopeRevision,
        expected_version: int,
    ) -> None:
        """Append a new revision; enforce optimistic lock if expected_version is set.

        Args:
            revision: The telescope revision to publish.
            expected_version: The expected head version of the telescope for optimistic locking.

        Raises:
            VersionConflictError: If the expected_version does not match the current version.
            NoChangeError: If the revision does not introduce any changes.
            SiteNotFoundError: If the site referenced by the telescope does not exist.
        """
