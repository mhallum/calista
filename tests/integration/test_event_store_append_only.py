"""Append-only contract tests for the event store.

These tests verify that *UPDATE* and *DELETE* are rejected by migration-defined
append-only protections and that inserted rows remain unchanged/present.

Backends:
  - Postgres (`postgres_engine`) — Alembic-migrated, triggers enforced.
  - SQLite file (`sqlite_engine_file`) — Alembic-migrated, triggers enforced.
    (SQLite in-memory is intentionally excluded; `create_all()` has no triggers.)

Notes:
  - Seeding happens in a separate transaction from the failing statement to
    avoid aborting the insert transaction on Postgres.
  - Cleanup relies on TRUNCATE (Postgres) / DELETE (SQLite) in fixture teardown.
  - Error message assertions are intentionally loose to remain backend-agnostic.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import pytest
from sqlalchemy import insert, text
from sqlalchemy.exc import DBAPIError

from calista.adapters.eventstore.schema import event_store

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

# mypy: disable-error-code=no-untyped-def


@pytest.mark.parametrize(
    "engine", ["postgres_engine", "sqlite_engine_file"], indirect=True
)
def test_update_is_blocked(engine: Engine, make_event: Callable[..., dict[str, Any]]):
    """Append-only: UPDATE must be rejected; existing row remains unchanged."""

    # Seed row in its own committed transaction
    with engine.begin() as conn:
        conn.execute(insert(event_store).values(make_event()))

    # Attempt UPDATE in a new transaction
    with engine.begin() as conn, pytest.raises(DBAPIError):
        conn.execute(text("UPDATE event_store SET version = 2"))

    # Verify data unchanged
    with engine.begin() as conn:
        version = conn.execute(text("SELECT version FROM event_store")).scalar_one()
        count = conn.execute(text("SELECT COUNT(*) FROM event_store")).scalar_one()
    assert version == 1
    assert count == 1


@pytest.mark.parametrize(
    "engine", ["postgres_engine", "sqlite_engine_file"], indirect=True
)
def test_delete_is_blocked(engine: Engine, make_event: Callable[..., dict[str, Any]]):
    """Append-only: DELETE must be rejected; row remains present."""
    with engine.begin() as conn:
        conn.execute(insert(event_store).values(make_event()))

    with engine.begin() as conn, pytest.raises(DBAPIError) as e:
        conn.execute(text("DELETE FROM event_store"))

    # pylint: disable=magic-value-comparison
    assert "delete" in str(e.value).lower() or "append" in str(e.value).lower()

    with engine.begin() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM event_store")).scalar_one()
    assert count == 1
