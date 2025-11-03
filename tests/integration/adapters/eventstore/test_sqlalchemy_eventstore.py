"""Integration tests for SqlAlchemyEventStore using a real Postgres database.

These tests verify that backend-specific errors are correctly mapped to
EventStoreError types, and that event ordering and integrity constraints
are handled as expected.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from calista.adapters.eventstore.sqlalchemy_adapters.eventstore import (
    SqlAlchemyEventStore,
)
from calista.interfaces.eventstore import (
    DuplicateEventIdError,
    EventEnvelope,
    InvalidEnvelopeError,
    StoreUnavailableError,
)

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

    from calista.interfaces.eventstore import EventStore


# pylint: disable=redefined-outer-name
@pytest.fixture()
def pg_eventstore(postgres_engine: Engine) -> Iterable[EventStore]:
    """Return a fresh SqlAlchemyEventStore instance using the provided Postgres engine."""
    with postgres_engine.connect() as conn:
        yield SqlAlchemyEventStore(conn)
        conn.close()


# needs Postgres; SQLite won't raise DataError on length overflow
@pytest.mark.slow
def test_append_event_type_overflow_maps_to_invalid_envelope_pg(
    pg_eventstore: EventStore, make_event: Callable[..., dict]
):
    """Test that event_type overflow maps to InvalidEnvelopeError in Postgres."""
    event = EventEnvelope(
        **make_event(event_type="A" * 300)
    )  # exceeds typical VARCHAR(255) limit

    # Make the length flexible across environments (optional "(N)"):
    pattern = re.compile(
        r"value too long for type character varying(?:\(\d+\))?",
        re.IGNORECASE,
    )
    with pytest.raises(InvalidEnvelopeError, match=pattern):
        pg_eventstore.append([event])


@pytest.mark.slow
def test_lock_timeout_maps_to_store_unavailable(postgres_engine: Engine, make_event):
    """Test that lock timeout maps to StoreUnavailableError in Postgres."""

    # Two separate connections
    with postgres_engine.connect() as locker, postgres_engine.connect() as runner:
        # 1) LOCKER: take a SHARE lock so SELECTs pass but INSERTs block
        with locker.begin():
            locker.execute(text("LOCK TABLE event_store IN SHARE MODE"))

            # 2) RUNNER: tiny lock_timeout so we fail fast
            runner.execute(text("SET lock_timeout = '50ms'"))

            store = SqlAlchemyEventStore(connection=runner)

            # Seed stream tip so we know SELECT max(version) will run first
            # (Not strictly necessary; SELECT runs anyway.)
            # Nothing to seed here—our lock strategy already allows the SELECT.

            envelope = EventEnvelope(**make_event(stream_id="S1", version=1))

            # INSERT will block on the SHARE lock and then time out -> DBAPIError
            with pytest.raises(
                StoreUnavailableError, match="canceling statement due to lock timeout"
            ):
                store.append([envelope])


@pytest.mark.slow
def test_global_seq_is_set_by_store_when_none(pg_eventstore: EventStore, make_event):
    """Test that global_seq is set by the store when None is provided."""

    # pg, but not sqlite, will error if we try to insert NULL into global_seq
    # we have to make sure to remove it from the insert statement for it to work
    # the same. This test ensures that happens.
    event = EventEnvelope(**make_event(global_seq=None))
    (stored_event,) = pg_eventstore.append([event])
    assert stored_event.global_seq is not None
    assert stored_event.global_seq >= 1


@pytest.mark.slow
def test_read_stream_orders_by_version_even_when_table_out_of_order(
    postgres_engine, make_event
):
    """Test that read_stream orders events by version even when table is physically out of order."""

    # 1) Seed data in a normal transaction
    with postgres_engine.begin() as conn1:
        store = SqlAlchemyEventStore(connection=conn1)
        n = 50
        events = [
            EventEnvelope(**make_event(stream_id="S", version=v))
            for v in range(1, n + 1)
        ]
        store.append(events)

    # 2) Create index & CLUSTER (requires autocommit) and ANALYZE
    with postgres_engine.connect().execution_options(
        isolation_level="AUTOCOMMIT"
    ) as ac:
        ac.execute(
            text("""
            CREATE INDEX IF NOT EXISTS event_store_version_desc_idx
            ON event_store (stream_id, version DESC)
        """)
        )
        ac.execute(text("CLUSTER event_store USING event_store_version_desc_idx"))
        ac.execute(text("ANALYZE event_store"))  # ANALYZE is enough; no VACUUM needed

    # 3) Force a seq scan & call the real adapter method
    with postgres_engine.connect() as conn2:
        conn2.execute(text("SET enable_indexscan = off"))
        conn2.execute(text("SET enable_bitmapscan = off"))
        conn2.execute(text("SET max_parallel_workers_per_gather = 0"))

        # A) read_stream() and verify is correctly ordered by version ASC
        store = SqlAlchemyEventStore(connection=conn2)
        retrieved_events = list(store.read_stream("S"))
        versions = [e.version for e in retrieved_events]

        assert versions == list(range(1, n + 1)), (
            "read_stream must return events ordered by version ASC; "
            "without ORDER BY, a seq scan over CLUSTERed physical order returns out-of-order rows."
        )


@pytest.mark.slow
def test_read_since_orders_by_global_seq_even_when_table_out_of_order(
    postgres_engine, make_event
):
    """Test that read_since orders events by global_seq even when table is physically out of order."""

    # 1) Seed data in a normal transaction
    with postgres_engine.begin() as conn1:
        store = SqlAlchemyEventStore(connection=conn1)
        n = 50
        events = [
            EventEnvelope(**make_event(stream_id="S", version=v))
            for v in range(1, n + 1)
        ]
        store.append(events)

    # 2) Create index & CLUSTER (requires autocommit) and ANALYZE
    with postgres_engine.connect().execution_options(
        isolation_level="AUTOCOMMIT"
    ) as ac:
        ac.execute(
            text("""
            CREATE INDEX IF NOT EXISTS event_store_version_desc_idx
            ON event_store (stream_id, version DESC)
        """)
        )
        ac.execute(text("CLUSTER event_store USING event_store_version_desc_idx"))
        ac.execute(text("ANALYZE event_store"))  # ANALYZE is enough; no VACUUM needed

    # 3) Force a seq scan & call the real adapter method
    with postgres_engine.connect() as conn2:
        conn2.execute(text("SET enable_indexscan = off"))
        conn2.execute(text("SET enable_bitmapscan = off"))
        conn2.execute(text("SET max_parallel_workers_per_gather = 0"))

        # A) read_stream() and verify is correctly ordered by version ASC
        store = SqlAlchemyEventStore(connection=conn2)
        retrieved_events = list(store.read_since())
        global_seq_list = [event.global_seq for event in retrieved_events]

        assert global_seq_list == list(range(1, n + 1)), (
            "read_since must return events ordered by global_seq ASC; "
            "without ORDER BY, a seq scan over CLUSTERed physical order returns out-of-order rows."
        )


@pytest.mark.slow
def test_raise_on_integrity_error_prefers_orig_message(postgres_engine: Engine):
    """Test that _raise_eventstore_error_from_integrity_error prefers the original message."""

    # A fake DBAPI "orig" whose __str__ contains the unique constraint name
    class FakeOrig(Exception):
        """Fake DBAPI error with a useful __str__."""

        def __str__(self) -> str:
            return 'duplicate key value violates unique constraint "uq_event_store_event_id"'

    # A wrapper IntegrityError whose __str__ *hides* the constraint name
    class WeirdIntegrity(IntegrityError):
        """IntegrityError wrapper with generic message."""

        def __init__(self):
            super().__init__("INSERT ...", {}, FakeOrig())

        def __str__(self) -> str:  # wrapper string with no useful clue
            return "generic integrity error"

    with postgres_engine.connect() as conn:
        store = SqlAlchemyEventStore(connection=conn)

        with pytest.raises(DuplicateEventIdError, match="uq_event_store_event_id"):
            store._raise_eventstore_error_from_integrity_error(WeirdIntegrity())  # pylint:disable=protected-access


@pytest.mark.slow
def test_raise_on_integrity_error_uses_wrapper_when_orig_is_none(postgres_engine):
    """Test that _raise_eventstore_error_from_integrity_error uses wrapper message when orig is None."""
    with postgres_engine.connect() as conn:
        store = SqlAlchemyEventStore(connection=conn)

        with pytest.raises(
            DuplicateEventIdError,
            match='duplicate key value violates unique constraint "uq_event_store_event_id"',
        ):
            error = IntegrityError(
                '"duplicate key value violates unique constraint "uq_event_store_event_id"',
                {},
                BaseException(),
            )
            error.orig = None
            store._raise_eventstore_error_from_integrity_error(error)  # pylint:disable=protected-access


@pytest.mark.slow
def test_raise_fallback_on_integrity_error(postgres_engine):
    """Test fallback for _raise_eventstore_error_from_integrity_error.

    If neither the wrapper nor the original IntegrityError message matches a known
    constraint, the method should raise InvalidEnvelopeError with the error message.
    """

    class OtherIntegrity(IntegrityError):  # pylint: disable=too-many-ancestors
        """An IntegrityError whose orig message does not match any known constraint."""

        def __init__(self):
            super().__init__("INSERT ...", {}, Exception("some other integrity error"))

        def __str__(self) -> str:
            return "some other integrity error"

    with postgres_engine.connect() as conn:
        store = SqlAlchemyEventStore(connection=conn)

        with pytest.raises(InvalidEnvelopeError, match="some other integrity error"):
            store._raise_eventstore_error_from_integrity_error(OtherIntegrity())  # pylint:disable=protected-access
