"""Event store interfaces for CALISTA.

This module defines:
- The canonical `EventEnvelope` DTO (ADR-0006).
- The `EventStore` port (framework-free ABC) for appending and reading events.
- A small, adapter-agnostic exception hierarchy for precise error handling.

Layering & dependency rules:
- Lives under `calista.interfaces`. Do NOT import from adapters, bootstrap, or entrypoints.
- Safe to import from service layer and adapters.

Contract overview
-----------------
Append:
- Atomic write for a **single (stream_type, stream_id)** batch.
- `global_seq` is assigned by the store; `recorded_at` is normalized to **UTC tz-aware**.
- Returns envelopes in the **same order** as provided.
- Strict idempotency policy: duplicate `event_id` -> `DuplicateEventIdError`.
- Errors:
  * `InvalidEnvelopeError` — client-side invariant violations (mixed streams, non-contiguous versions,
    naive timestamps, non-serializable payload/metadata, etc.).
  * `VersionConflictError` — per-stream version uniqueness/contiguity violated
    (e.g., `(stream_id, version)` already exists).
  * `DuplicateEventIdError` — `event_id` not globally unique.
  * `StoreUnavailableError` — transient driver/DB issues; callers may retry.

Reads:
- `read_stream(stream_id, from_version=1, to_version=None)` — ascending by `version` (inclusive bounds).
- `read_since(global_seq=0, limit=None)` — ascending by `global_seq` (global catch-up).
- Empty results yield an empty iterator. Invalid ranges raise `ValueError`.

Invariants & validation:
- `event_id` is a **26-char ULID** (validated here and in the schema).
- `version >= 1`; `global_seq` is None pre-persist.
- If provided, `recorded_at` must be **tz-aware** (UTC).
- `stream_id`, `stream_type`, `event_type` must be non-empty (whitespace rejected).
- Batches enforce single stream, contiguous versions, unique `event_id`s, and `global_seq is None`.

DB mapping notes (adapters):
- Unique on `event_id`; unique on `(stream_id, version)`.
- Check constraints for ULID length and positive version.
- Indexes support global scans and per-stream reads.
- Append-only behavior enforced at the DB (see migrations).

References:
- ADR-0006: Event Envelope
- ADR-0020: EventStore.append Return Semantics
- ADR-0021: Event Store Error Semantics & Read Behavior
"""

import abc
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

# --- Exceptions to standardize adapter behavior ---


class EventStoreError(Exception):
    """Base class for CALISTA event store errors."""


class VersionConflictError(EventStoreError):
    """Stream version precondition failed (optimistic concurrency)."""


class DuplicateEventIdError(EventStoreError):
    """event_id must be globally unique; duplicate detected."""


class InvalidEnvelopeError(EventStoreError):
    """The event envelope is invalid."""


class StoreUnavailableError(EventStoreError):
    """Operational/timeout/connection errors; callers may retry."""


# --- Envelope DTO ---


@dataclass(frozen=True, slots=True)
class EventEnvelope:
    """Canonical persisted event wrapper (see ADR-0006).

    Notes:
      - `global_seq` is None before persistence and assigned by the store.
      - `recorded_at` if set, should be UTC, tz-aware; the store may set/overwrite/confirm it.
    """

    # pylint: disable=too-many-instance-attributes

    stream_id: str  # Prefer ULID or UUID; natural keys allowed (length not enforced).
    stream_type: str
    version: int
    event_id: str  # 26-char ULID
    event_type: str
    payload: dict[str, Any]
    metadata: dict[str, Any] | None = None  # e.g., correlation_id, causation_id, actor
    recorded_at: datetime | None = (
        None  # UTC tz-aware; authoritative on return from store.
    )
    global_seq: int | None = None  # Assigned by the event store

    def __post_init__(self) -> None:
        if len(self.event_id) != 26:
            raise InvalidEnvelopeError("event_id must be a 26-character ULID.")
        if self.version < 1:
            raise InvalidEnvelopeError("version must be >= 1")
        if self.global_seq is not None and self.global_seq < 1:
            raise InvalidEnvelopeError("global_seq must be >= 1 when set")
        if self.recorded_at is not None:
            if self.recorded_at.tzinfo is None or self.recorded_at.utcoffset() is None:
                raise InvalidEnvelopeError("recorded_at must be tz-aware.")
            if self.recorded_at.utcoffset() != timedelta(0):
                raise InvalidEnvelopeError("recorded_at must be UTC.")
        if (
            not self.stream_id.strip()
            or not self.stream_type.strip()
            or not self.event_type.strip()
        ):
            raise InvalidEnvelopeError(
                "stream_id, stream_type, and event_type must be non-empty."
            )


@dataclass(frozen=True, slots=True)
class EventEnvelopeBatch:
    """A single-stream, atomic append batch.

    Invariants enforced:
      - All events share the same (stream_id, stream_type).
      - Versions are >= 1 and strictly contiguous within the batch.
      - global_seq is None for all events (pre-persist).
      - event_id is unique within the batch.
      - if recorded_at is present, it must be UTC tz-aware (store may overwrite).
    """

    stream_id: str
    stream_type: str
    events: Sequence[EventEnvelope]

    def __post_init__(self) -> None:
        if not self.events:
            raise InvalidEnvelopeError("Empty batch is not allowed.")

        # Basic shape checks
        for event in self.events:
            if (
                event.stream_id != self.stream_id
                or event.stream_type != self.stream_type
            ):
                raise InvalidEnvelopeError("Mixed streams in a single batch.")

            if event.global_seq is not None:
                raise InvalidEnvelopeError(
                    "global_seq must be None before persistence."
                )

        # Uniqueness within batch
        ids = [event.event_id for event in self.events]
        if len(ids) != len(set(ids)):
            raise InvalidEnvelopeError("Duplicate event_id within batch.")

        # Contiguity within batch (strictly increasing by 1)
        versions = [e.version for e in self.events]
        if versions != list(range(versions[0], versions[0] + len(versions))):
            raise InvalidEnvelopeError(
                "Versions in batch must be contiguous and ordered."
            )

    @property
    def starting_version(self) -> int:
        """The first version in the batch."""
        return self.events[0].version

    @classmethod
    def from_events(cls, events: Sequence[EventEnvelope]) -> "EventEnvelopeBatch":
        """Create a batch from a sequence of events, enforcing invariants.

        Args:
            events: A sequence of EventEnvelope objects.

        Raises:
            InvalidEnvelopeError: If the events list is empty or violates batch invariants.

        Returns:
            An EventEnvelopeBatch instance containing the provided events.
        """

        return cls(
            stream_id=events[0].stream_id,
            stream_type=events[0].stream_type,
            events=events,
        )


# --- Event Store Interface ---


class EventStore(abc.ABC):
    """An abstract base class for an event store."""

    @abc.abstractmethod
    def append(
        self, events: EventEnvelopeBatch | Sequence[EventEnvelope]
    ) -> Sequence[EventEnvelope]:
        """Persist events atomically.

        The store enforces (stream_type, stream_id, version) uniqueness and event_id uniqueness.
        On success, returns envelopes with `global_seq` (and possibly `recorded_at`) populated.

        Raises:
            InvalidEnvelopeError: mixed streams in one batch, non-contiguous versions,
                or other invariant violations.
            VersionConflictError: when the write would violate per-stream
                version monotonicity (e.g., (stream_id, version) already exists
                or versions aren't contiguous for that stream).
            DuplicateEventIdError: when any event_id already exists.
            StoreUnavailableError: for operational/timeout/connection errors;
                callers may retry.

        Returns:
            The persisted events with `global_seq` and `recorded_at` populated,
            in the **same order** as provided.
        """

    @abc.abstractmethod
    def read_stream(
        self, stream_id: str, from_version: int = 1, to_version: int | None = None
    ) -> Iterable[EventEnvelope]:
        """Yield events for a given stream, ordered by version ascending.

        Optionally restrict the range via `from_version` (inclusive) and `to_version` (inclusive).

        Args:
            stream_id: The ID of the stream to read from.
            from_version: The starting version (inclusive), defaults to 1.
            to_version: The ending version (inclusive). If None, reads to the latest.

        Returns:
            An iterable of EventEnvelope objects. Returns empty iterator if the stream has no events.

        Raises:
            ValueError: if from_version < 1 or to_version < from_version.
        """

    @abc.abstractmethod
    def read_since(
        self, global_seq: int = 0, limit: int | None = None
    ) -> Iterable[EventEnvelope]:
        """Yield events with `global_seq` > the given value, ascending.

        Optionally restrict the number returned via `limit`.

        Args:
            global_seq: The global sequence number to read after,
                defaults to 0 (meaning start with the first event).
            limit: Maximum number of events to return. If None, returns all available.

        Returns:
            An iterable of EventEnvelope objects. Returns an empty iterable if no events are found.

        Raises:
            ValueError: if global_seq < 0 or limit is not None and limit < 1.
        """
