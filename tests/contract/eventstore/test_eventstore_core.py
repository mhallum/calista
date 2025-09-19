"""Contract tests for the EventStore port.

This module verifies backend-agnostic behavior:
- append contract (order-preserving, atomic, single-stream invariants)
- error mapping (VersionConflictError, DuplicateEventIdError, InvalidEnvelopeError)
- read semantics (read_stream bounds; read_since global playback; empty reads)
- time normalization (recorded_at tz-aware UTC)
- global_seq monotonicity
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import timedelta

import pytest

from calista.adapters.eventstore.memory import MemoryEventStore
from calista.adapters.eventstore.sqlalchemy import SqlAlchemyEventStore
from calista.interfaces.eventstore import (
    DuplicateEventIdError,
    EventStore,
    InvalidEnvelopeError,
    VersionConflictError,
)


# pylint: disable=redefined-outer-name
@pytest.fixture(params=["memory", "sqlite"])
def eventstore(
    request: pytest.FixtureRequest, sqlite_engine_memory
) -> Iterable[EventStore]:
    """Return a fresh eventstore instance for the requested backend.

    Current params:
      - `"memory"` → `MemoryEventStore` (non-durable, in-memory)
      - `"sqlite"` → `SqlAlchemyEventStore` (SQLite in-memory via SQLAlchemy

    Extend by adding new identifiers to `params` and branching below to
    construct the corresponding backend. Each invocation yields a brand-new
    store instance for isolation.
    """
    # Select backend based on param
    match request.param:
        case "memory":
            yield MemoryEventStore()
        case "sqlite":
            with sqlite_engine_memory.begin() as connection:
                yield SqlAlchemyEventStore(connection)
            connection.close()
        case _:
            raise ValueError(f"unknown store type: {request.param}")


# ===========================================================================
#                         Append: happy path & shapes
# ===========================================================================


def test_append_assigns_seq_and_recorded_at(eventstore: EventStore, make_envelope):
    """Check that appended events get a global_seq and UTC recorded_at timestamp."""

    # Create and append a single event
    event = make_envelope(version=1)
    (stored_event,) = tuple(eventstore.append([event]))

    # Assert global_seq and recorded_at are set correctly
    assert isinstance(stored_event.global_seq, int) and stored_event.global_seq >= 1
    assert stored_event.recorded_at is not None
    assert stored_event.recorded_at.tzinfo is not None
    assert stored_event.recorded_at.utcoffset() == timedelta(0)  # UTC


def test_appended_events_return_in_same_order_as_input(
    eventstore: EventStore, make_envelope
):
    """Check that appended events are returned in the same input order."""

    # Append two events
    event1 = make_envelope(version=1)
    event2 = make_envelope(version=2)
    stored_event1, stored_event2 = eventstore.append([event1, event2])

    # Same order back
    assert (stored_event1.event_id, stored_event2.event_id) == (
        event1.event_id,
        event2.event_id,
    )
    # Monotonic global_seq
    assert stored_event1.global_seq is not None
    assert stored_event2.global_seq is not None
    assert stored_event1.global_seq < stored_event2.global_seq


def test_global_seq_monotonic_across_streams(eventstore: EventStore, make_envelope):
    """Check that global_seq increases across different streams."""

    # Append events to different streams
    event_envelope_a = make_envelope(stream_id="A", version=1)
    (persisted_event_envelope_a,) = eventstore.append([event_envelope_a])

    event_envelope_b = make_envelope(stream_id="B", version=1)
    (persisted_event_envelope_b,) = eventstore.append([event_envelope_b])

    # Confirm monotonicity accross streams
    assert persisted_event_envelope_a.global_seq is not None
    assert persisted_event_envelope_b.global_seq is not None
    assert persisted_event_envelope_a.global_seq < persisted_event_envelope_b.global_seq


# ===========================================================================
#                            Append: errors
# ===========================================================================


def test_append_duplicate_event_id_raises(eventstore: EventStore, make_envelope):
    """Check that appending a duplicate event_id raises DuplicateEventIdError."""

    # Append event with event_id 00000000000000000000000000
    event_id = "0" * 26
    event1 = make_envelope(version=1, event_id=event_id)
    eventstore.append([event1])

    # Try to append another event with same event_id (should fail)
    event2 = make_envelope(stream_id="S2", version=1, event_id=event_id)
    with pytest.raises(DuplicateEventIdError) as exc:
        eventstore.append([event2])
    # ensure a message object was provided (not None)
    assert exc.value.args and exc.value.args[0] is not None
    # and that it’s non-empty when rendered
    assert str(exc.value).strip()  # truthy => not empty string


def test_append_version_conflict_raises_and_is_atomic(
    eventstore: EventStore, make_envelope
):
    """Check VersionConflictError and atomicity on version conflict."""

    # Seed stream "S" with one event at version 1
    (stored_event1,) = eventstore.append([make_envelope(stream_id="S", version=1)])
    assert stored_event1.version == 1

    # Attempt to append a batch where the first item is a conflict (another v1)
    e_conflict = make_envelope(stream_id="S", version=1)
    e_next = make_envelope(stream_id="S", version=2)
    with pytest.raises(VersionConflictError, match="expected first version 2, got 1"):
        eventstore.append([e_conflict, e_next])

    # Atomic: v2 should NOT have been appended
    got = list(eventstore.read_stream("S"))
    assert [e.version for e in got] == [1]


def test_append_version_conflict_raises_on_empty_stream(
    eventstore: EventStore, make_envelope
):
    """Check VersionConflictError when first event version is not 1 on empty stream."""

    # Attempt to append event with version=2 to empty stream (should fail)
    conflicting_event = make_envelope(stream_id="S", version=2)
    with pytest.raises(VersionConflictError, match="expected first version 1, got 2"):
        eventstore.append([conflicting_event])

    # Atomic: nothing should have been appended
    fetched_events = list(eventstore.read_stream("S"))
    assert len(fetched_events) == 0


def test_append_mixed_streams_in_batch_raises(eventstore: EventStore, make_envelope):
    """Check InvalidEnvelopeError for mixed streams in a batch."""

    # Try to append events from different streams in one batch (should fail)
    event1 = make_envelope(stream_id="S1", version=1)
    event2 = make_envelope(stream_id="S2", version=1)
    with pytest.raises(InvalidEnvelopeError):
        eventstore.append([event1, event2])  # single call must be single-stream


def test_append_noncontiguous_batch_versions_raises(
    eventstore: EventStore, make_envelope
):
    """Check InvalidEnvelopeError for noncontiguous batch versions."""

    # Try to append non-contiguous versions in batch (should fail)
    event1 = make_envelope(version=1)
    event3 = make_envelope(version=3)
    with pytest.raises(InvalidEnvelopeError):
        eventstore.append([event1, event3])  # batch must be contiguous


def test_recorded_at_is_set_by_store(eventstore: EventStore, make_envelope):
    """Check that store sets recorded_at to UTC tz-aware value."""

    # recorded_at provided by caller is ignored / overridden by store
    past = make_envelope(version=1, recorded_at=None)
    (persisted_event,) = eventstore.append([past])
    assert persisted_event.recorded_at is not None
    assert persisted_event.recorded_at.tzinfo is not None
    assert persisted_event.recorded_at.utcoffset() == timedelta(0)  # UTC


# ===========================================================================
#                              Reads: behavior
# ===========================================================================


def test_read_stream_bounds_inclusive(eventstore: EventStore, make_envelope):
    """Check read_stream returns events within inclusive bounds."""

    # Append events to stream "S"
    stream_id = "S"
    eventstore.append([make_envelope(stream_id=stream_id, version=1)])
    eventstore.append([make_envelope(stream_id=stream_id, version=2)])
    eventstore.append([make_envelope(stream_id=stream_id, version=3)])
    eventstore.append([make_envelope(stream_id=stream_id, version=4)])

    # Read events with bounds 2 to 3 (inclusive)
    fetched_events = list(
        eventstore.read_stream(stream_id, from_version=2, to_version=3)
    )
    assert [e.version for e in fetched_events] == [2, 3]

    # Read events with bounds 2 to 2 (single event)
    fetched_events = list(
        eventstore.read_stream(stream_id, from_version=2, to_version=2)
    )
    assert [e.version for e in fetched_events] == [2]


def test_read_stream_empty_when_no_events(eventstore: EventStore):
    """Check read_stream returns empty list for missing stream."""

    # Read from non-existent stream
    assert len(list(eventstore.read_stream("nope"))) == 0


def test_read_since_global_cursor_and_limit(eventstore: EventStore, make_envelope):
    """Check read_since returns events after global_seq, with limit."""

    # Append events to two streams
    event1 = eventstore.append([make_envelope(stream_id="A", version=1)])[0]
    eventstore.append([make_envelope(stream_id="A", version=2)])
    eventstore.append([make_envelope(stream_id="B", version=1)])

    assert event1.global_seq is not None  # make sure it persisted
    retrieved_events = list(eventstore.read_since(event1.global_seq, limit=2))

    # make sure we got two events
    expected_number_of_events = 2
    assert len(retrieved_events) == expected_number_of_events

    # make sure events are in ascending global order
    event2, event3 = retrieved_events
    assert event2.global_seq is not None
    assert event3.global_seq is not None
    assert event3.global_seq > event2.global_seq

    # make sure we only got events after event1
    assert event2.global_seq > event1.global_seq


def test_read_since_can_limit_to_one(eventstore: EventStore, make_envelope):
    """Check read_since can limit results to one event."""

    # Append events to two streams
    event1 = eventstore.append([make_envelope(stream_id="A", version=1)])[0]
    eventstore.append([make_envelope(stream_id="A", version=2)])
    eventstore.append([make_envelope(stream_id="B", version=1)])

    assert event1.global_seq is not None  # make sure it persisted
    retrieved_events = list(eventstore.read_since(event1.global_seq, limit=1))

    # make sure we got one event
    expected_number_of_events = 1
    assert len(retrieved_events) == expected_number_of_events

    # make sure we only got events after event1
    event2 = retrieved_events[0]
    assert event2.global_seq is not None
    assert event2.global_seq > event1.global_seq


def test_read_since_empty_for_large_cursor(eventstore: EventStore):
    """Check read_since returns empty for large global_seq."""

    # Use a global_seq much larger than any existing event
    assert len(list(eventstore.read_since(10_000_000))) == 0


def test_read_stream_invalid_ranges_raise(eventstore: EventStore):
    """Check read_stream raises ValueError for invalid ranges."""

    # from_version must be >= 1
    with pytest.raises(ValueError, match=r"^from_version must be >= 1$"):
        list(eventstore.read_stream("S", from_version=0))

    # to_version must be >= from_version
    with pytest.raises(ValueError, match=r"^to_version must be >= from_version$"):
        list(eventstore.read_stream("S", from_version=3, to_version=2))


@pytest.mark.parametrize(
    "global_seq, limit, msg",
    [
        (-1, None, r"^global_seq must be >= 0$"),
        (0, 0, r"^limit cannot be <= 0$"),
    ],
    ids=[
        "negative global_seq",
        "zero limit",
    ],
)
def test_read_since_invalid_args_raise(eventstore: EventStore, global_seq, limit, msg):
    """Check read_since raises ValueError for invalid arguments."""

    # Try invalid global_seq and limit values
    with pytest.raises(ValueError, match=msg):
        list(eventstore.read_since(global_seq=global_seq, limit=limit))


def test_read_since_without_limit_returns_all(eventstore: EventStore, make_envelope):
    """Check read_since returns all events when limit is None."""

    # Append events to two streams
    event1 = eventstore.append([make_envelope(stream_id="A", version=1)])[0]
    event2 = eventstore.append([make_envelope(stream_id="A", version=2)])[0]
    event3 = eventstore.append([make_envelope(stream_id="B", version=1)])[0]

    assert event1.global_seq is not None  # make sure it persisted
    retrieved_events = list(eventstore.read_since())

    # make sure we got all events
    assert retrieved_events == [event1, event2, event3]


def test_read_since_with_limit_larger_than_available_returns_all_available(
    eventstore: EventStore, make_envelope
):
    """Check read_since returns all available events if limit exceeds available."""

    # Append two events
    event1 = eventstore.append([make_envelope(stream_id="A", version=1)])[0]
    event2 = eventstore.append([make_envelope(stream_id="A", version=2)])[0]

    assert event1.global_seq is not None  # make sure it persisted
    retrieved_events = list(eventstore.read_since(event1.global_seq, limit=10))

    # make sure we got all events after event1
    assert retrieved_events == [event2]
