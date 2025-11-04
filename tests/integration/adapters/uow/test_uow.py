"""Integration tests for the SQLAlchemy-backed Unit of Work adapter.

Verifies commit and rollback behavior of SqlAlchemyUnitOfWork.
"""

import pytest

from calista.adapters.unit_of_work import SqlAlchemyUnitOfWork
from calista.interfaces.eventstore import EventEnvelope
from calista.interfaces.stream_index import NaturalKey


def test_uow_can_add_event(sqlite_engine_memory, make_event):
    """Unit of Work can add an event to the event store."""
    uow = SqlAlchemyUnitOfWork(sqlite_engine_memory)
    event = EventEnvelope(**make_event())
    with uow:
        persisted_event = uow.eventstore.append([event])[0]
        uow.commit()

    # Verify the event was added
    with uow:
        events = list(uow.eventstore.read_since())

    assert events[0] == persisted_event


def test_uow_rollback_discards_event(sqlite_engine_memory, make_event):
    """Unit of Work rollback discards uncommitted events."""
    uow = SqlAlchemyUnitOfWork(sqlite_engine_memory)
    event = EventEnvelope(**make_event())
    with uow:
        uow.eventstore.append([event])
        # Intentionally not calling commit()

    # Verify the event was not added
    with uow:
        events = list(uow.eventstore.read_since())

    assert len(events) == 0


def test_rolls_back_on_error(sqlite_engine_memory, make_event):
    """Ensure an exception inside the UnitOfWork context triggers a rollback."""

    class MyException(Exception):
        """Custom exception for testing."""

    event = EventEnvelope(**make_event())
    uow = SqlAlchemyUnitOfWork(sqlite_engine_memory)
    with pytest.raises(MyException):
        with uow:
            uow.eventstore.append([event])
            raise MyException()

    # new connection to verify rollback
    with uow:
        events = list(uow.eventstore.read_since())
    assert len(events) == 0


def test_uow_can_use_stream_index(sqlite_engine_memory):
    """Unit of Work can interact with the StreamIndex."""
    stream_id = "test-stream-123"
    stream_type = "TestAggregate"
    natural_key = "test-natural-key"

    uow = SqlAlchemyUnitOfWork(sqlite_engine_memory)

    # Reserve a natural key
    with uow:
        uow.stream_index.reserve(
            NaturalKey(kind=stream_type, key=natural_key),
            stream_id=stream_id,
        )
        uow.commit()

    # Verify the reservation was made
    with uow:
        retreived_entry = uow.stream_index.lookup(
            NaturalKey(kind=stream_type, key=natural_key)
        )
        assert retreived_entry is not None
        assert retreived_entry.stream_id == stream_id
