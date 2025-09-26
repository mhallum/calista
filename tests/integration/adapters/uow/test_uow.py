"""Integration tests for the SQLAlchemy-backed Unit of Work adapter.

Verifies commit and rollback behavior of SqlAlchemyUnitOfWork.
"""

import pytest

from calista.adapters.unit_of_work import SqlAlchemyUnitOfWork
from calista.interfaces.eventstore import EventEnvelope


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
