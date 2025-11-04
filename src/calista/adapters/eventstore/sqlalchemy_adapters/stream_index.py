"""Implementation of StreamIndex using SQLAlchemy."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from calista.adapters.db.dialects import DialectName, UnsupportedDialect
from calista.interfaces.stream_index import (
    IndexEntrySnapshot,
    NaturalKey,
    NaturalKeyAlreadyBound,
    StreamIdAlreadyBound,
    StreamIndex,
)

from .schema import stream_index

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection
    from sqlalchemy.sql.dml import Insert


class SqlAlchemyStreamIndex(StreamIndex):
    """StreamIndex implementation that supports both Postgres and SQLite."""

    def __init__(self, connection: Connection):
        self.connection = connection
        self.dialect = connection.engine.dialect.name  # 'postgresql' or 'sqlite'

    # --- lookups ---

    def lookup(self, natural_key: NaturalKey) -> IndexEntrySnapshot | None:
        stm = select(stream_index.c.stream_id, stream_index.c.version).where(
            stream_index.c.kind == natural_key.kind,
            stream_index.c.key == natural_key.key,
        )

        if not (row := self.connection.execute(stm).fetchone()):
            return None
        return IndexEntrySnapshot(natural_key, row.stream_id, int(row.version))

    def _lookup_by_stream(self, stream_id: str) -> IndexEntrySnapshot | None:
        stmt = select(
            stream_index.c.kind, stream_index.c.key, stream_index.c.version
        ).where(stream_index.c.stream_id == stream_id)
        if not (row := self.connection.execute(stmt).fetchone()):
            return None
        return IndexEntrySnapshot(
            NaturalKey(row.kind, row.key), stream_id, int(row.version)
        )

    # --- version updates ---

    def update_version(self, stream_id: str, version: int) -> None:
        self.connection.execute(
            update(stream_index)
            .where(
                stream_index.c.stream_id == stream_id,
                stream_index.c.version < version,  # pragma: no mutate
                # (< and <= has same result)
            )
            .values(version=version)
        )

    # --- reserve: no-throw insert + decide outcome via reads ---

    def reserve(self, natural_key: NaturalKey, stream_id: str) -> None:
        # 1) Build dialect-specific no-throw insert statement
        stmt = self._build_no_throw_insert(natural_key, stream_id)

        # 2) Execute and check how many rows were inserted
        result = self.connection.execute(stmt)
        inserted = result.rowcount == 1  # pragma: no mutate
        # Rationale:
        # - Mutant sets `inserted = None` → falsy → takes the conflict/lookup path.
        # - If the real value was already False, behavior is identical.
        # - If the real value was True (row inserted), the subsequent idempotency check
        #   finds the row and returns early with the same result. No externally visible change.
        # Chasing this mutant would couple tests to internal control flow without increasing safety.

        # 3) If inserted, all is right with the world
        if inserted:  # pylint: disable=consider-using-assignment-expr # (clearer this way)
            return

        # 4) If not inserted, there was a conflict.
        # Decide outcome by reading authoritative rows
        if existing := self.lookup(natural_key):
            if existing.stream_id == stream_id:
                return  # idempotent
            raise NaturalKeyAlreadyBound(
                natural_key=natural_key.key,
                stream_id=existing.stream_id,
                kind=natural_key.kind,
            )

        if by_stream := self._lookup_by_stream(stream_id):
            # same stream_id used under a different natural key
            raise StreamIdAlreadyBound(
                stream_id=stream_id,
                natural_key=by_stream.natural_key.key,
                kind=by_stream.natural_key.kind,
            )

        # If nothing matches, something is very wrong.
        # This should never happen, but is here as a safeguard.
        msg = "reserve(): insert failed but no conflicting rows found"  # pragma: no mutate # pragma: no cover # noqa: E501 # pylint: disable=line-too-long
        raise RuntimeError(msg)  # pragma: no mutate # pragma: no cover

    # --- dialect-specific insert builders ---

    def _build_no_throw_insert(self, key: NaturalKey, stream_id: str) -> Insert:
        dialect_name = DialectName.from_string(self.dialect)
        values = {
            "kind": key.kind,
            "key": key.key,
            "stream_id": stream_id,
            "version": 0,
        }
        if dialect_name is DialectName.POSTGRES:
            return (
                pg_insert(stream_index)
                .values(**values)
                .on_conflict_do_nothing()  # ignore ANY unique conflict
            )
        if dialect_name is DialectName.SQLITE:
            return (
                sqlite_insert(stream_index)
                .values(**values)
                .on_conflict_do_nothing()  # ignore ANY unique conflict
            )

        # Fallback: should not reach here because it should already be raised by
        # DialectName.get_from_string, but some checkers can't infer that.
        # Here just in case.
        msg = f"Unsupported dialect: {self.dialect}"  # pragma: no cover # pragma: no mutate
        raise UnsupportedDialect(msg)  # pragma: no cover # pragma: no mutate
