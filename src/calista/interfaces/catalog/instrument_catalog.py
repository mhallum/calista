"""Interface for the Instrument Catalog."""

from __future__ import annotations

import abc
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, ClassVar, TypeAlias

from .base import VersionedCatalog
from .errors import InvalidRevisionError, InvalidSnapshotError
from .unsettable import UNSET, Unsettable, resolve

# pylint: disable=too-many-instance-attributes

# -- Read Model ---


@dataclass(frozen=True, slots=True)
class InstrumentSnapshot:
    """Immutable snapshot of an instrument definition at a given catalog version.

    Conventions:
      - `instrument_code` is canonical uppercase (e.g., "DEVENY").
      - `mode` is a short human label (e.g., "imaging", "spectroscopy"), None if unknown.
      - `source` is human-readable provenance (e.g., "LDT wiki", "ops email").
      - `recorded_at` is a UTC tz-aware datetime when this snapshot was recorded.
    """

    instrument_code: str
    version: int
    recorded_at: datetime
    name: str
    source: str | None = None
    mode: str | None = None
    comment: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "instrument_code", self.instrument_code.upper())

        if self.recorded_at.tzinfo is None or self.recorded_at.utcoffset() != timedelta(
            0
        ):
            raise InvalidSnapshotError(
                "instrument",
                self.instrument_code,
                "recorded_at must be timezone-aware UTC",
            )


# -- Write Models ---

Diff: TypeAlias = dict[str, tuple[Any | None, Any | None]]


@dataclass(frozen=True, slots=True)
class InstrumentRevision:
    """Immutable write model for an instrument revision to be published."""

    instrument_code: str  # canonical uppercase code, e.g. 'LMI'
    name: str
    source: str | None = None
    mode: str | None = None
    comment: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "instrument_code", self.instrument_code.upper())

    def get_diff(self, head: InstrumentSnapshot) -> Diff | None:
        """Return changed fields as {name: (old, new)}, or None if no changes."""
        if head.instrument_code != self.instrument_code:
            raise InvalidRevisionError(
                "instrument",
                self.instrument_code,
                f"instrument_code mismatch with head ({head.instrument_code})",
            )
        diffs: dict[str, tuple[object | None, object | None]] = {}
        for field in (
            "name",
            "source",
            "mode",
            "comment",
        ):
            old_value = getattr(head, field)
            new_value = getattr(self, field)
            if old_value != new_value:
                diffs[field] = (old_value, new_value)
        return diffs if diffs else None


@dataclass(frozen=True, slots=True)
class InstrumentPatch:
    """Immutable write model for an instrument patch to be applied to an existing instrument head."""

    name: Unsettable[str] = UNSET
    source: Unsettable[str] = UNSET
    mode: Unsettable[str] = UNSET
    comment: str | None = None

    def apply_to(self, head: InstrumentSnapshot) -> InstrumentRevision:
        """Apply the patch to the given instrument head and return a new InstrumentRevision."""

        def _resolve(field, clearable=True):
            value = getattr(self, field)
            current = getattr(head, field)
            return resolve(
                value,
                current,
                clearable=clearable,
                field=field,
                kind="instrument",
                key=head.instrument_code,
            )

        return InstrumentRevision(
            instrument_code=head.instrument_code,
            name=_resolve("name", clearable=False),
            source=_resolve("source"),
            mode=_resolve("mode"),
            comment=self.comment,
        )


# --- Interface ---


class InstrumentCatalog(
    VersionedCatalog[InstrumentSnapshot, InstrumentRevision], abc.ABC
):
    """Interface for managing the instrument catalog."""

    KIND: ClassVar[str] = "instrument"
    CODE_ATTR: ClassVar[str] = "instrument_code"
    REVISION_CLASS: ClassVar[type[InstrumentRevision]] = InstrumentRevision
    SNAPSHOT_CLASS: ClassVar[type[InstrumentSnapshot]] = InstrumentSnapshot
