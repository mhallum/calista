"""In memory event store implementation.

All events are stored in memory and lost when the instance is discarded.
Use for unit tests, prototyping, or scenarios where durability is not required.

This implementation passes all contract tests for the EventStore interface.
"""

from collections.abc import Iterable, Sequence
from datetime import datetime, timezone

from calista.interfaces.eventstore import (
    DuplicateEventIdError,
    EventEnvelope,
    EventEnvelopeBatch,
    EventStore,
    VersionConflictError,
)


class InMemoryEventStore(EventStore):
    """In-memory EventStore for testing and non-durable use cases.

    - Non-durable: all data is lost when the instance is discarded.
    - Suitable for testing, prototyping, and ephemeral use cases.
    """

    def __init__(self):
        self._events: list[EventEnvelope] = []
        self._global_seq = 0

    # --------------------------------------------------------------------- #
    # Interface implementation
    # --------------------------------------------------------------------- #

    def append(
        self, events: Sequence[EventEnvelope] | EventEnvelopeBatch
    ) -> Sequence[EventEnvelope]:
        batch = (
            events
            if isinstance(events, EventEnvelopeBatch)
            else EventEnvelopeBatch.from_events(events)
        )

        stream_tip = self._fetch_stream_tip(batch.stream_id)
        expected_version = 1 if stream_tip is None else stream_tip + 1
        if batch.starting_version != expected_version:
            raise VersionConflictError(
                f"expected first version {expected_version}, got {batch.starting_version}"
            )

        appended = []
        for event in batch.events:
            self._global_seq += 1
            row = event.as_insertable_row()
            row["global_seq"] = self._global_seq
            row["recorded_at"] = datetime.now(timezone.utc)
            if row["event_id"] in self._get_event_ids():
                raise DuplicateEventIdError(f"duplicate event_id {row['event_id']}")
            envelope = EventEnvelope(**row)
            appended.append(envelope)

        self._events.extend(appended)
        return appended

    def read_stream(
        self, stream_id: str, from_version: int = 1, to_version: int | None = None
    ) -> Iterable[EventEnvelope]:
        if from_version < 1:
            raise ValueError("from_version must be >= 1")
        if to_version is not None and to_version < from_version:
            raise ValueError("to_version must be >= from_version")

        for event in sorted(
            (e for e in self._events if e.stream_id == stream_id),
            key=lambda e: e.version,
        ):
            if event.version < from_version:
                continue
            if to_version is not None and event.version > to_version:
                break  # pragma: no mutate (replacing with return is equivalent, but less clear)
            yield event

    def read_since(
        self, global_seq: int = 0, limit: int | None = None
    ) -> Iterable[EventEnvelope]:
        if global_seq < 0:
            raise ValueError("global_seq must be >= 0")
        if limit is not None and limit <= 0:
            raise ValueError("limit cannot be <= 0")

        if limit is not None:
            yield from self._events[global_seq : global_seq + limit]
        else:
            yield from self._events[global_seq:]

    # --------------------------------------------------------------------- #
    # Internals
    # --------------------------------------------------------------------- #

    def _fetch_stream_tip(self, stream_id: str) -> int | None:
        """Retrieves the latest version (tip) of the event stream for the given stream ID.

        Args:
            stream_id (str): The identifier of the event stream.

        Returns:
            int | None: The highest version number of the events in the stream,
                or None if the stream has no events.
        """

        if not (stream_events := [e for e in self._events if e.stream_id == stream_id]):
            return None
        return max(e.version for e in stream_events)

    def _get_event_ids(self) -> set[str]:
        """Retrieves a set of unique event IDs from the stored events.

        Returns:
            set[str]: A set containing the event IDs of all events in memory.
        """

        return {e.event_id for e in self._events}
