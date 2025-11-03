"""SQLAlchemy-backed EventStore adapter for Calista.

This module provides a SQLAlchemy-backed implementation of the EventStore interface,
enabling persistent storage and retrieval of event envelopes in a relational database.
It enforces single-stream, contiguous version appends and ensures events are returned
in the same order as provided. The adapter handles integrity and data errors, mapping
them to domain-specific exceptions.

Usage:
    Instantiate SqlAlchemyEventStore with a SQLAlchemy Connection object to interact
    with the event store table defined in adapters.eventstore.schema.

Classes:
    SqlAlchemyEventStore -- Implements EventStore using SQLAlchemy.

Exceptions:
    Maps SQLAlchemy errors to Calista event store exceptions.
"""

from collections.abc import Iterable, Sequence
from typing import cast

from sqlalchemy import RowMapping, Select, func, insert, select
from sqlalchemy.engine import Connection
from sqlalchemy.exc import (
    DataError,
    DBAPIError,
    IntegrityError,
)

from calista.interfaces.eventstore import (
    DuplicateEventIdError,
    EventEnvelope,
    EventEnvelopeBatch,
    EventStore,
    InvalidEnvelopeError,
    StoreUnavailableError,
    VersionConflictError,
)

from .schema import event_store

# all flags must be present
UNIQUE_EVENT_ID_CONSTRAINT_KEYWORDS = ("event_id", "unique")  # pragma: no mutate

EMPTY_STRING = ""  # pragma: no mutate


class SqlAlchemyEventStore(EventStore):
    """SQLAlchemy-backed EventStore.

    - Uses the canonical `event_store` table (see adapters.eventstore.schema).
    - Enforces single-stream + contiguous version appends.
    - Returns envelopes in the **same order** as provided.
    """

    def __init__(self, connection: Connection):
        self.connection = connection

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

        tip = self._fetch_stream_tip(batch.stream_id)
        expected_first = 1 if tip is None else tip + 1
        if batch.starting_version != expected_first:
            raise VersionConflictError(
                f"expected first version {expected_first}, got {batch.starting_version}"
            )

        try:
            persisted_rows = self._insert_returning(batch)
        except IntegrityError as e:
            self._raise_eventstore_error_from_integrity_error(e)
        except DataError as e:  # value too long, bad JSON, etc.
            raise InvalidEnvelopeError(str(e)) from e
        except (
            DBAPIError
        ) as e:  # any DBAPIErrors (OperationalError, InterfaceError, etc.)
            raise StoreUnavailableError(str(e)) from e

        persisted_events = [EventEnvelope(**row) for row in persisted_rows]
        return persisted_events

    def read_stream(
        self, stream_id: str, from_version: int = 1, to_version: int | None = None
    ) -> Iterable[EventEnvelope]:
        if from_version < 1:
            raise ValueError("from_version must be >= 1")
        if to_version is not None and to_version < from_version:
            raise ValueError("to_version must be >= from_version")

        stmt: Select = (
            select(event_store)
            .where(event_store.c.stream_id == stream_id)
            .where(event_store.c.version >= from_version)
            .order_by(event_store.c.version.asc())
        )

        if to_version is not None:
            stmt = stmt.where(event_store.c.version <= to_version)

        rows = self.connection.execute(stmt).mappings().all()

        for row in rows:
            yield EventEnvelope(**row)

    def read_since(
        self, global_seq: int = 0, limit: int | None = None
    ) -> Iterable[EventEnvelope]:
        if global_seq < 0:
            raise ValueError("global_seq must be >= 0")
        if limit is not None and limit < 1:
            raise ValueError("limit cannot be <= 0")

        stmt: Select = (
            select(event_store)
            .where(event_store.c.global_seq > global_seq)
            .order_by(event_store.c.global_seq.asc())
        )
        if limit is not None:
            stmt = stmt.limit(limit)

        rows = self.connection.execute(stmt).mappings().all()
        for row in rows:
            yield EventEnvelope(**row)

    # --------------------------------------------------------------------- #
    # Internals
    # --------------------------------------------------------------------- #

    def _fetch_stream_tip(self, stream_id: str) -> int | None:
        """Retrieves the latest version (tip) of the event stream for the given stream ID.

        Args:
            stream_id (str): The identifier of the event stream.

        Returns:
            int | None: The maximum version number of the stream if it exists, otherwise None.
        """
        stmt = select(func.max(event_store.c.version)).where(
            event_store.c.stream_id == stream_id
        )
        results = self.connection.execute(stmt).scalar_one_or_none()
        return cast(int | None, results)  # for mypy # pragma: no mutate

    def _insert_returning(self, batch: EventEnvelopeBatch) -> Sequence[RowMapping]:
        """Inserts a batch of event envelopes into the event store and returns the inserted rows.

        Args:
            batch (EventEnvelopeBatch): A batch containing event envelopes to be inserted.

        Returns:
            Sequence[RowMapping]: A sequence of row mappings representing the inserted events.
        """

        # Build rows in input order
        rows = [event.as_insertable_row() for event in batch.events]

        return (
            self.connection.execute(
                insert(event_store).values(rows).returning(event_store)
            )
            .mappings()
            .all()
        )

    @staticmethod
    def _raise_eventstore_error_from_integrity_error(
        integrity_error: IntegrityError,
    ) -> None:
        """Handles SQLAlchemy IntegrityError exceptions by raising appropriate event store errors.

        Args:
            integrity_error (IntegrityError): The SQLAlchemy IntegrityError instance to handle.

        Raises:
            DuplicateEventIdError: If the error message contains keywords indicating a
                duplicate event ID constraint violation.
            InvalidEnvelopeError: For any other integrity errors not related to duplicate event IDs.
        """

        msg = (
            str(integrity_error.orig)
            if integrity_error.orig not in (None, EMPTY_STRING)
            else str(integrity_error)
        )

        if all(kw in msg.lower() for kw in UNIQUE_EVENT_ID_CONSTRAINT_KEYWORDS):
            raise DuplicateEventIdError(msg) from integrity_error

        # Everything I can think of has already been caught by this point,
        # so this is a catch-all fallback for any other integrity errors.
        raise InvalidEnvelopeError(msg) from integrity_error
